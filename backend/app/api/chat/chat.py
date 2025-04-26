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
    db_session = ChatSession(user_id=current_user.id, model_name=session.model_name)
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

    # ユーザーメッセージの保存
    user_message = Message(session_id=session_id, role="user", content=message.content)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # セッション内の最初のメッセージの場合、セッション名を生成
    message_count = db.query(Message).filter(Message.session_id == session_id).count()
    if message_count == 1:  # 最初のメッセージ
        session_name = await ChatService.generate_session_name_from_message(
            message.content
        )
        chat_session.name = session_name
        db.commit()

    # 会話履歴を取得（現在のセッションの全メッセージ）
    chat_history = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )

    # メッセージを整形
    formatted_messages = [
        {"role": msg.role, "content": msg.content} for msg in chat_history
    ]

    # ストリーミングモードの場合
    if message.stream:
        return StreamingResponse(
            _stream_chat_response(
                session_id, formatted_messages, chat_session.model_name, db
            ),
            media_type="text/event-stream",
        )

    # 非ストリーミングモードの場合
    try:
        response_data = await ChatService.get_chat_response(
            formatted_messages, chat_session.model_name, stream=False
        )
        ai_response = response_data["message"]["content"]

        # AIのレスポンスを保存
        ai_message = Message(
            session_id=session_id, role="assistant", content=ai_response
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


# ストリーミングレスポンスを処理する非同期ジェネレータ
async def _stream_chat_response(
    session_id: int, messages: list, model_name: str, db: Session
) -> typing.AsyncGenerator[str, None]:
    # 開始ログ
    logger.info(
        f"Starting streaming response for session_id={session_id}, model={model_name}"
    )

    # 最終的な完全なAI応答を保持する変数
    complete_response = ""

    # SSE (Server-Sent Events)形式のヘッダーを送信
    yield "data: " + json.dumps({"event": "start"}) + "\n\n"

    try:
        # ジェネレータを使用して結果を取得
        chat_response_gen = await ChatService.get_chat_response(
            messages, model_name, stream=True
        )

        chunk_count = 0
        # チャンク処理
        async for chunk, is_done in chat_response_gen:
            chunk_count += 1
            logger.debug(
                f"Chunk #{chunk_count} received: length={len(chunk) if chunk else 0}, is_done={is_done}"
            )

            if chunk:
                complete_response += chunk
                # クライアントにチャンクを送信
                yield "data: " + json.dumps(
                    {"event": "chunk", "content": chunk}
                ) + "\n\n"

            if is_done:
                # ログ追加：保存前の状態確認
                logger.info(
                    f"Saving AI response to DB: session_id={session_id}, content_length={len(complete_response)}, chunks_processed={chunk_count}"
                )

                # 空の応答をチェック
                if not complete_response:
                    logger.warning(
                        f"Empty response detected for session_id={session_id}"
                    )
                    # 空の場合でもエラーにせず保存
                    complete_response = "応答を生成できませんでした。"

                # 完全な応答をDBに保存
                ai_message = Message(
                    session_id=session_id,
                    role="assistant",
                    content=complete_response,
                )
                db.add(ai_message)
                db.commit()
                db.refresh(ai_message)  # IDを取得するためにリフレッシュ

                # ログ追加：保存後の確認
                logger.info(f"AI response saved to DB: message_id={ai_message.id}")

                # クライアントに完了イベントを送信
                yield "data: " + json.dumps(
                    {
                        "event": "done",
                        "content": complete_response,
                        "session_id": session_id,
                    }
                ) + "\n\n"

                # 保存処理とクライアント通知が完了
                logger.info(f"Streaming response completed for session_id={session_id}")
                break

            # 少し待機して、クライアントに処理時間を与える
            await asyncio.sleep(0.01)

        # 全てのチャンクを処理したが、is_doneを受け取らなかった場合
        if not is_done:
            logger.warning(
                f"Stream completed without is_done signal for session_id={session_id}"
            )

            # それでも応答があれば保存する
            if complete_response:
                logger.info(
                    f"Saving AI response anyway: session_id={session_id}, content_length={len(complete_response)}"
                )

                ai_message = Message(
                    session_id=session_id,
                    role="assistant",
                    content=complete_response,
                )
                db.add(ai_message)
                db.commit()
                db.refresh(ai_message)

                logger.info(f"AI response saved to DB: message_id={ai_message.id}")

                # クライアントに完了イベントを送信
                yield "data: " + json.dumps(
                    {
                        "event": "done",
                        "content": complete_response,
                        "session_id": session_id,
                    }
                ) + "\n\n"

    except Exception as e:
        logger.error(
            f"Error in streaming response: {e}", exc_info=True
        )  # スタックトレースも出力
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
