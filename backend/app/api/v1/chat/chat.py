import json
import logging
import typing
from datetime import datetime
from typing import Any, AsyncGenerator, cast
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.chat import ChatSession, Message
from app.models.user import User
from app.schemas.chat import ChatResponseWithThinking
from app.schemas.chat import ChatSession as ChatSessionSchema
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionUpdate,
    MessageCreate,
    MessageSchema,
)
from app.schemas.enums import AIModelId
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
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatSession]:
    # セッションと最後のメッセージ情報を効率的に取得
    sessions_query = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.updated_at))
        .limit(limit)
        .offset(offset)
    )

    sessions = sessions_query.all()

    # 各セッションの最後のメッセージ情報を取得
    for session in sessions:
        last_message = (
            db.query(Message)
            .filter(Message.session_id == session.id)
            .order_by(desc(Message.created_at))
            .first()
        )

        # セッションの updated_at を最後のメッセージ時刻に更新（まだ更新されていない場合）
        if last_message and (
            not session.updated_at or session.updated_at < last_message.created_at
        ):
            session.updated_at = last_message.created_at
            db.add(session)

    db.commit()

    return sessions


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
        (
            f"💬 Message request received: model={message.model_id}, "
            f"thinking_mode={message.thinking_mode}, "
            f"content_preview='{message.content[:30]}...'"
        )
    )

    # トークン制限チェック
    is_allowed, reason = await TokenUsageService.check_token_limit(
        db, current_user.id, message.model_id
    )
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=reason
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
    thinking_mode_support = ChatService.get_thinking_mode_support(message.model_id)
    logger.info(
        f"🧠 Model {message.model_id} thinking mode support: {thinking_mode_support}"
    )

    # ユーザーメッセージの保存（モデル名を含める）
    user_content = message.content
    user_message = Message(
        session_id=session_id,
        role="user",
        content=user_content,
        model_id=message.model_id,
    )
    db.add(user_message)

    # セッションのupdated_atを更新
    chat_session.updated_at = datetime.now(ZoneInfo("UTC"))
    db.add(chat_session)

    db.commit()
    db.refresh(user_message)

    # セッション内の最初のメッセージの場合、セッション名を生成
    message_count = db.query(Message).filter(Message.session_id == session_id).count()
    if message_count == 1:
        session_name = await ChatService.generate_session_name_from_message(
            user_content
        )
        # セッション名をデータベースに保存
        chat_session.name = session_name
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
        {"role": msg.role, "content": msg.content} for msg in chat_history
    ]

    # ストリーミングモードの場合
    if message.stream:
        # Cast the generator type explicitly
        chat_response_gen_uncasted = await ChatService.get_chat_response(
            formatted_messages,
            message.model_id,
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
                message.model_id,
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
            message.model_id,
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
                f"Token usage (non-streaming) - model: {message.model_id}, "
                f"prompt: {token_usage.get('prompt_tokens', 0)}, "
                f"completion: {token_usage.get('completion_tokens', 0)}, "
                f"total: {token_usage.get('total_tokens', 0)}"
            )
            await TokenUsageService.record_token_usage(
                db,
                current_user.id,
                message.model_id,
                token_usage["prompt_tokens"],
                token_usage["completion_tokens"],
            )
        else:
            logger.warning(
                f"No token usage information in response from {message.model_id}"
            )

        # AIのレスポンスを保存
        content_length = len(ai_response)
        thinking_length = len(thinking_content) if thinking_content else 0

        logger.info(
            "💾 Saving non-streaming response to DB: "
            f"content_length={content_length}, thinking_length={thinking_length}"
        )
        ai_message = Message(
            session_id=session_id,
            role="assistant",
            content=ai_response,
            model_id=message.model_id,
            thinking_content=thinking_content,
        )
        db.add(ai_message)

        # セッションのupdated_atを更新
        chat_session.updated_at = datetime.now(ZoneInfo("UTC"))
        db.add(chat_session)

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
    model_id: AIModelId,
    db: Session,
    user_id: int,
    thinking_mode: bool = False,
    chat_response_generator: (
        AsyncGenerator[tuple[str, str, bool, dict[Any, Any]], None] | None
    ) = None,
) -> typing.AsyncGenerator[str, None]:
    logger.info(
        (
            f"Starting streaming response for session_id={session_id}, "
            f"model={model_id}, thinking_mode={thinking_mode}"
        )
    )

    complete_response = ""
    complete_thinking = ""
    token_usage_obj = None

    yield "data: " + json.dumps({"event": "start"}) + "\n\n"

    if chat_response_generator is None:
        logger.warning(
            (
                "_stream_chat_response called without pre-fetched generator. "
                "This might indicate an issue."
            )
        )
        return

    try:
        chunk_count = 0
        async for chunk, chunk_type, is_done, usage_data in chat_response_generator:
            chunk_count += 1
            logger.debug(
                (
                    f"Chunk #{chunk_count} received: type={chunk_type}, "
                    f"length={len(chunk)}, is_done={is_done}"
                )
            )

            if (
                usage_data
                and isinstance(usage_data, dict)
                and "thinking_content" in usage_data
            ):
                if usage_data["thinking_content"] is not None:
                    complete_thinking = usage_data["thinking_content"]
                    logger.debug(
                        "Updated complete_thinking from usage: "
                        f"{len(complete_thinking)} chars"
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
                    (
                        f"Processing 'done' event from provider. "
                        f"Final accumulated response length: {len(complete_response)}, "
                        f"thinking length: {len(complete_thinking)}"
                    )
                )
                token_usage_dict_for_json = None
                if usage_data:
                    prompt_tokens = usage_data.get("prompt_tokens", 0)
                    completion_tokens = usage_data.get("completion_tokens", 0)
                    total_tokens = usage_data.get(
                        "total_tokens", prompt_tokens + completion_tokens
                    )
                    logger.info(
                        (
                            f"Token usage (streaming) - model: {model_id}, "
                            f"prompt: {prompt_tokens}, "
                            f"completion: {completion_tokens}, total: {total_tokens}"
                        )
                    )
                    token_usage_obj = await TokenUsageService.record_token_usage(
                        db,
                        user_id,
                        model_id,
                        prompt_tokens,
                        completion_tokens,
                    )
                    token_usage_dict_for_json = {
                        "id": token_usage_obj.id,
                        "user_id": token_usage_obj.user_id,
                        "model_id": token_usage_obj.model_id,
                        "prompt_tokens": token_usage_obj.prompt_tokens,
                        "completion_tokens": token_usage_obj.completion_tokens,
                        "total_tokens": token_usage_obj.total_tokens,
                        "timestamp": (
                            str(token_usage_obj.timestamp)
                            if token_usage_obj.timestamp
                            else None
                        ),
                    }
                else:
                    logger.warning(
                        (
                            "No token usage information in final streaming chunk "
                            f"from {model_id}"
                        )
                    )

                final_answer_content_to_save = complete_response.strip()
                final_thinking_content_to_save = (
                    complete_thinking.strip() if thinking_mode else None
                )

                # ログ用の変数を準備
                content_length = len(final_answer_content_to_save)
                thinking_length = (
                    len(final_thinking_content_to_save)
                    if final_thinking_content_to_save
                    else 0
                )

                logger.info(
                    "💾 Saving streaming response to DB: "
                    f"content_length={content_length}, "
                    f"thinking_length={thinking_length}"
                )

                if not final_answer_content_to_save:
                    logger.warning(
                        (
                            "Empty final answer detected for "
                            f"session_id={session_id}, model={model_id}"
                        )
                    )
                    final_answer_content_to_save = "(応答なし)"

                # データベースに最終メッセージを保存
                db_message = Message(
                    session_id=session_id,
                    role="assistant",
                    content=final_answer_content_to_save,
                    model_id=model_id,
                    thinking_content=final_thinking_content_to_save,
                )
                db.add(db_message)

                # セッションのupdated_atを更新
                chat_session_for_update = (
                    db.query(ChatSession).filter(ChatSession.id == session_id).first()
                )
                if chat_session_for_update:
                    chat_session_for_update.updated_at = datetime.now(ZoneInfo("UTC"))
                    db.add(chat_session_for_update)

                db.commit()
                db.refresh(db_message)
                logger.info(f"AI response saved to DB: message_id={db_message.id}")

                # 最終的なメッセージ情報をクライアントに送信
                # created_at が存在することを確認
                created_at_iso = (
                    db_message.created_at.isoformat() if db_message.created_at else None
                )
                # Ensure model_id is a string for JSON serialization
                model_id_str_for_json = (
                    db_message.model_id.value
                    if hasattr(db_message.model_id, "value")
                    else db_message.model_id
                )
                message_data_for_json = {
                    "id": db_message.id,
                    "session_id": db_message.session_id,
                    "role": db_message.role,
                    "content": db_message.content,
                    "model_id": model_id_str_for_json,
                    "created_at": created_at_iso,
                    "thinking_content": db_message.thinking_content,
                    "token_usage": token_usage_dict_for_json,
                }
                # Send the final message data with type: "message"
                # This event might be used by the frontend to update
                # the final message content
                # before the stream is considered fully 'done'.
                yield "data: " + json.dumps(
                    {
                        "type": "message",
                        "data": message_data_for_json,
                    }
                ) + "\n\n"

                # Send the 'event: done' that the frontend expects for completion
                done_event_data = {
                    "event": "done",  # Frontend expects this event type
                    "content": message_data_for_json.get("content"),
                    "model_name": message_data_for_json.get(
                        "model_id"
                    ),  # Frontend expects model_name
                    "thinking_content": message_data_for_json.get("thinking_content"),
                    "token_usage": message_data_for_json.get("token_usage"),
                }
                yield "data: " + json.dumps(done_event_data) + "\n\n"

                logger.info(f"Sent 'event: done' for session_id={session_id}")
                logger.info(f"Streaming response completed for session_id={session_id}")
                break
            else:
                logger.warning(f"Unknown chunk type received: {chunk_type}")

    except Exception as e:
        logger.error(f"Error in streaming response: {e}", exc_info=True)
        yield "data: " + json.dumps({"event": "error", "message": str(e)}) + "\n\n"


@router.put("/sessions/{session_id}", response_model=ChatSessionSchema)
async def update_chat_session(
    session_id: int,
    session_update: ChatSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSession:
    """チャットセッションの名前を更新する"""
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

    # セッション名を更新
    chat_session.name = session_update.name
    chat_session.updated_at = datetime.now(ZoneInfo("UTC"))
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    logger.info(f"Updated chat session name: {session_id} -> '{session_update.name}'")
    return chat_session


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
