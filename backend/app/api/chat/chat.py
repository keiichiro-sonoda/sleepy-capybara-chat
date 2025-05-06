import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import typing
from typing import cast, AsyncGenerator, Any

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.chat import ChatSession, Message
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSession as ChatSessionSchema,
    MessageCreate,
    MessageSchema,
    ChatResponseWithThinking,
)
from app.services.chat import ChatService
from app.services.token_usage import TokenUsageService

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
) -> ChatResponseWithThinking | StreamingResponse:
    # thinking_modeパラメータをログ出力（レベルをINFOに上げる）
    logger.info(
        f"💬 Message request received: model={message.model_name}, thinking_mode={message.thinking_mode}, content_preview='{message.content[:30]}...'"
    )

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

    # ChatServiceから思考モードのサポート状況を確認
    thinking_mode_support = ChatService.get_thinking_mode_support(message.model_name)
    logger.info(
        f"🧠 Model {message.model_name} thinking mode support: {thinking_mode_support}"
    )

    # ユーザーメッセージの保存（モデル名を含める）
    user_content = message.content
    user_message = Message(
        session_id=session_id,
        role="user",
        content=user_content,
        model_name=message.model_name,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # セッション内の最初のメッセージの場合、セッション名を生成
    message_count = db.query(Message).filter(Message.session_id == session_id).count()
    if message_count == 1:
        session_name = await ChatService.generate_session_name_from_message(
            user_content
        )
        # If the assignment error on chat_session.name persists, uncomment the next line
        # chat_session.name = session_name # type: ignore[assignment]
        db.commit()

    # 会話履歴を取得
    chat_history: list[Message] = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )

    # Cast the values within the list comprehension to str
    formatted_messages: list[dict[str, str]] = [
        {"role": cast(str, msg.role), "content": cast(str, msg.content)}
        for msg in chat_history
    ]

    # ストリーミングモードの場合
    if message.stream:
        # Cast the generator type explicitly
        chat_response_gen_uncasted = await ChatService.get_chat_response(
            formatted_messages,
            message.model_name,
            stream=True,
            thinking_mode=message.thinking_mode,
        )
        # Cast directly without intermediate variable
        chat_response_gen = cast(
            AsyncGenerator[tuple[str, str, bool, dict[Any, Any]], None],
            chat_response_gen_uncasted,
        )

        return StreamingResponse(
            _stream_chat_response(
                session_id,
                message.model_name,
                db,
                current_user.id,
                message.thinking_mode,
                chat_response_gen,
            ),
            media_type="text/event-stream",
        )

    # 非ストリーミングモードの場合
    try:
        response_data_uncasted = await ChatService.get_chat_response(
            formatted_messages,
            message.model_name,
            stream=False,
            thinking_mode=message.thinking_mode,
        )
        # Cast the response data to dict
        response_data = cast(dict[str, Any], response_data_uncasted)

        ai_response = response_data["content"]
        thinking_content = response_data.get("thinking_content")

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
        logger.info(
            f"💾 Saving non-streaming response to DB: content_length={len(ai_response)}, thinking_length={len(thinking_content) if thinking_content else 0}"
        )
        logger.debug(f"💾 Content preview: {ai_response[:100]}...")
        logger.debug(
            f"💾 Thinking preview: {thinking_content[:100] if thinking_content else 'None'}..."
        )
        ai_message = Message(
            session_id=session_id,
            role="assistant",
            content=ai_response,
            model_name=message.model_name,
            thinking_content=thinking_content,
        )
        db.add(ai_message)
        db.commit()

        return ChatResponseWithThinking(
            response=ai_response,
            session_id=session_id,
            thinking_content=thinking_content,
        )
    except Exception as e:
        logger.error(f"Error getting chat response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get AI response: {str(e)}",
        )


# ストリーミングレスポンスを処理する非同期ジェネレータを更新
async def _stream_chat_response(
    session_id: int,
    model_name: str,
    db: Session,
    user_id: int,
    thinking_mode: bool = False,
    chat_response_generator: (
        AsyncGenerator[tuple[str, str, bool, dict[Any, Any]], None] | None
    ) = None,
) -> typing.AsyncGenerator[str, None]:
    logger.info(
        f"Starting streaming response for session_id={session_id}, model={model_name}, thinking_mode={thinking_mode}"
    )

    complete_response = ""
    complete_thinking = ""
    token_usage = None

    yield "data: " + json.dumps({"event": "start"}) + "\n\n"

    if chat_response_generator is None:
        logger.warning(
            "_stream_chat_response called without pre-fetched generator. This might indicate an issue."
        )
        return

    try:
        chunk_count = 0
        async for chunk, chunk_type, is_done, usage in chat_response_generator:
            chunk_count += 1
            logger.debug(
                f"Chunk #{chunk_count} received: type={chunk_type}, length={len(chunk)}, is_done={is_done}"
            )

            if usage and isinstance(usage, dict) and "thinking_content" in usage:
                if usage["thinking_content"] is not None:
                    complete_thinking = usage["thinking_content"]
                    logger.debug(
                        f"Updated complete_thinking from usage: {len(complete_thinking)} chars"
                    )
                else:
                    logger.debug("Received None for thinking_content in usage.")

            if chunk_type == "thinking":
                yield "data: " + json.dumps(
                    {"event": "chunk", "type": "thinking", "content": chunk}
                ) + "\n\n"
            elif chunk_type == "answer":
                if chunk:
                    complete_response += chunk
                    yield "data: " + json.dumps(
                        {"event": "chunk", "type": "answer", "content": chunk}
                    ) + "\n\n"
            elif chunk_type == "done":
                logger.info(
                    f"Processing 'done' event from provider. Final accumulated response length: {len(complete_response)}, thinking length: {len(complete_thinking)}"
                )
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
                else:
                    logger.warning(
                        f"No token usage information in final streaming chunk from {model_name}"
                    )
                    token_usage_dict = None

                final_answer_content_to_save = complete_response.strip()
                final_thinking_content_to_save = (
                    complete_thinking.strip() if thinking_mode else None
                )

                logger.info(
                    f"💾 Saving streaming response to DB: content_length={len(final_answer_content_to_save)}, thinking_length={len(final_thinking_content_to_save) if final_thinking_content_to_save else 0}"
                )
                logger.debug(
                    f"💾 Content preview: {final_answer_content_to_save[:100]}..."
                )
                logger.debug(
                    f"💾 Thinking preview: {final_thinking_content_to_save[:100] if final_thinking_content_to_save else 'None'}..."
                )

                if not final_answer_content_to_save:
                    logger.warning(
                        f"Empty final answer detected for session_id={session_id}, model={model_name}"
                    )
                    final_answer_content_to_save = "(応答なし)"

                ai_message = Message(
                    session_id=session_id,
                    role="assistant",
                    content=final_answer_content_to_save,
                    model_name=model_name,
                    thinking_content=final_thinking_content_to_save,
                )
                db.add(ai_message)
                db.commit()
                logger.info(f"AI response saved to DB: message_id={ai_message.id}")

                yield "data: " + json.dumps(
                    {
                        "event": "done",
                        "content": final_answer_content_to_save,
                        "session_id": session_id,
                        "model_name": model_name,
                        "token_usage": token_usage_dict,
                        "thinking_content": final_thinking_content_to_save,
                    }
                ) + "\n\n"

                logger.info(f"Streaming response completed for session_id={session_id}")
                break
            else:
                logger.warning(f"Unknown chunk type received: {chunk_type}")

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
