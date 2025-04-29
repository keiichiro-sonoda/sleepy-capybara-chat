import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio
import typing

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.chat import ChatSession, Message
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSession as ChatSessionSchema,
    MessageCreate,
    Message as MessageSchema,
    ChatResponse,
)
from app.services.chat import ChatService
from app.services.token_usage import TokenUsageService

# ロガーの設定
logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()


@router.post("/sessions", response_model=ChatSessionSchema)
async def create_chat_session(
    session: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSession:
    db_session = ChatSession(user_id=current_user.id, name=session.name)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


@router.get("/sessions", response_model=list[ChatSessionSchema])
async def get_chat_sessions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ChatSession]:
    return db.query(ChatSession).filter(ChatSession.user_id == current_user.id).all()


@router.get("/sessions/{session_id}/messages", response_model=list[MessageSchema])
async def get_chat_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Message]:
    # セッションの存在確認と所有権チェック
    chat_session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
        )

    # セッションのメッセージを取得
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )

    return messages


@router.post("/sessions/{session_id}/messages", response_model=None)
async def create_message(
    session_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse | StreamingResponse:
    # セッションの存在確認
    chat_session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
        )

    # トークン制限チェック
    is_allowed, limit_message = await TokenUsageService.check_token_limit(
        db, current_user.id, message.model_name
    )
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=limit_message,
        )

    # ユーザーメッセージの保存（モデル名を含める）
    user_message = Message(
        session_id=session_id,
        role="user",
        content=message.content,
        model_name=message.model_name,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # セッション内の最初のメッセージの場合、セッション名を生成
    message_count = db.query(Message).filter(Message.session_id == session_id).count()
    if message_count == 1:
        session_name = await ChatService.generate_session_name_from_message(
            message.content
        )
        chat_session.name = session_name
        db.commit()

    # 会話履歴を取得
    chat_history = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )

    formatted_messages = [
        {"role": msg.role, "content": msg.content} for msg in chat_history
    ]

    # ストリーミングモードの場合
    if message.stream:
        return StreamingResponse(
            _stream_chat_response(
                session_id, formatted_messages, message.model_name, db, current_user.id
            ),
            media_type="text/event-stream",
        )

    # 非ストリーミングモードの場合
    try:
        response_data = await ChatService.get_chat_response(
            formatted_messages, message.model_name, stream=False
        )
        ai_response = response_data["content"]

        # トークン使用量のログ出力を追加
        if "token_usage" in response_data:
            token_usage = response_data["token_usage"]
            logger.info(
                f"Token usage (non-streaming) - model: {message.model_name}, "
                f"prompt: {token_usage.get('prompt_tokens', 0)}, "
                f"completion: {token_usage.get('completion_tokens', 0)}, "
                f"total: {token_usage.get('total_tokens', 0)}"
            )
            await TokenUsageService.record_token_usage(
                db,
                current_user.id,
                message.model_name,
                token_usage["prompt_tokens"],
                token_usage["completion_tokens"],
            )
        else:
            logger.warning(
                f"No token usage information in response from {message.model_name}"
            )

        # AIのレスポンスを保存
        ai_message = Message(
            session_id=session_id,
            role="assistant",
            content=ai_response,
            model_name=message.model_name,
        )
        db.add(ai_message)
        db.commit()

        return ChatResponse(response=ai_response, session_id=session_id)
    except Exception as e:
        logger.error(f"Error getting chat response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get AI response: {str(e)}",
        )


# ストリーミングレスポンスを処理する非同期ジェネレータを更新
async def _stream_chat_response(
    session_id: int,
    messages: list,
    model_name: str,
    db: Session,
    user_id: int,
) -> typing.AsyncGenerator[str, None]:
    logger.info(
        f"Starting streaming response for session_id={session_id}, model={model_name}"
    )

    complete_response = ""
    token_usage = None

    yield "data: " + json.dumps({"event": "start"}) + "\n\n"

    try:
        chat_response_gen = await ChatService.get_chat_response(
            messages, model_name, stream=True
        )

        chunk_count = 0
        async for chunk_data in chat_response_gen:
            # 必要な値を抽出（chunk, is_done, usageの3つの値）
            if len(chunk_data) == 3:
                chunk, is_done, usage = chunk_data
                # トークン使用量情報があれば詳細をログに出力
                if usage and isinstance(usage, dict) and usage:
                    logger.debug(f"Token usage info from chunk {chunk_count}: {usage}")
            else:
                # 後方互換性のために2つの値の場合も対応
                chunk, is_done = chunk_data
                usage = {}
                logger.debug(f"No usage info in chunk {chunk_count}")

            chunk_count += 1
            logger.debug(
                f"Chunk #{chunk_count} received: length={len(chunk) if chunk else 0}, is_done={is_done}"
            )

            if chunk:
                complete_response += chunk
                yield "data: " + json.dumps(
                    {"event": "chunk", "content": chunk}
                ) + "\n\n"

            if is_done:
                logger.info(
                    f"Saving AI response to DB: session_id={session_id}, content_length={len(complete_response)}, chunks_processed={chunk_count}"
                )

                if not complete_response:
                    logger.warning(
                        f"Empty response detected for session_id={session_id}"
                    )
                    complete_response = "応答を生成できませんでした。"

                # トークン使用量を記録
                if usage:
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get(
                        "total_tokens", prompt_tokens + completion_tokens
                    )

                    logger.info(
                        f"Token usage (streaming) - model: {model_name}, "
                        f"prompt: {prompt_tokens}, completion: {completion_tokens}, total: {total_tokens}"
                    )

                    token_usage = await TokenUsageService.record_token_usage(
                        db,
                        user_id,
                        model_name,
                        prompt_tokens,
                        completion_tokens,
                    )
                else:
                    logger.warning(
                        f"No token usage information in final streaming chunk from {model_name}"
                    )

                ai_message = Message(
                    session_id=session_id,
                    role="assistant",
                    content=complete_response,
                    model_name=model_name,
                )
                db.add(ai_message)
                db.commit()
                db.refresh(ai_message)

                logger.info(f"AI response saved to DB: message_id={ai_message.id}")

                # SQLAlchemyオブジェクトを辞書に変換
                token_usage_dict = None
                if token_usage:
                    token_usage_dict = {
                        "id": token_usage.id,
                        "user_id": token_usage.user_id,
                        "model_name": token_usage.model_name,
                        "prompt_tokens": token_usage.prompt_tokens,
                        "completion_tokens": token_usage.completion_tokens,
                        "total_tokens": token_usage.total_tokens,
                        "timestamp": (
                            str(token_usage.timestamp)
                            if token_usage.timestamp
                            else None
                        ),
                    }

                yield "data: " + json.dumps(
                    {
                        "event": "done",
                        "content": complete_response,
                        "session_id": session_id,
                        "model_name": model_name,
                        "token_usage": token_usage_dict,
                    }
                ) + "\n\n"

                logger.info(f"Streaming response completed for session_id={session_id}")
                break

            await asyncio.sleep(0.01)

        if not is_done:
            logger.warning(
                f"Stream completed without is_done signal for session_id={session_id}"
            )

            if complete_response:
                logger.info(
                    f"Saving AI response anyway: session_id={session_id}, content_length={len(complete_response)}"
                )

                ai_message = Message(
                    session_id=session_id,
                    role="assistant",
                    content=complete_response,
                    model_name=model_name,
                )
                db.add(ai_message)
                db.commit()
                db.refresh(ai_message)

                logger.info(f"AI response saved to DB: message_id={ai_message.id}")

                # SQLAlchemyオブジェクトを辞書に変換
                token_usage_dict = None
                if token_usage:
                    token_usage_dict = {
                        "id": token_usage.id,
                        "user_id": token_usage.user_id,
                        "model_name": token_usage.model_name,
                        "prompt_tokens": token_usage.prompt_tokens,
                        "completion_tokens": token_usage.completion_tokens,
                        "total_tokens": token_usage.total_tokens,
                        "timestamp": (
                            str(token_usage.timestamp)
                            if token_usage.timestamp
                            else None
                        ),
                    }

                yield "data: " + json.dumps(
                    {
                        "event": "done",
                        "content": complete_response,
                        "session_id": session_id,
                        "model_name": model_name,
                        "token_usage": token_usage_dict,
                    }
                ) + "\n\n"

    except Exception as e:
        logger.error(f"Error in streaming response: {e}", exc_info=True)
        yield "data: " + json.dumps({"event": "error", "message": str(e)}) + "\n\n"


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """チャットセッションとそれに関連するすべてのメッセージを削除する"""
    # セッションの存在確認と所有権チェック
    chat_session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
        )

    # 関連するメッセージを削除
    db.query(Message).filter(Message.session_id == session_id).delete()

    # セッションを削除
    db.delete(chat_session)
    db.commit()

    logger.info(f"Deleted chat session: {session_id}")
    return None
