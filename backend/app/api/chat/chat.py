import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import httpx
import json
import asyncio

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


@router.post("/sessions/{session_id}/messages")
async def create_message(
    session_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    # 会話履歴を取得（現在のセッションの全メッセージ）
    chat_history = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )

    # Ollamaの /api/chat エンドポイント用にメッセージを整形
    formatted_messages = [
        {"role": msg.role, "content": msg.content} for msg in chat_history
    ]

    # リクエストの内容をログ出力
    request_data = {
        "model": chat_session.model_name,
        "messages": formatted_messages,
        "stream": message.stream,  # ストリーミングモードの設定をクライアントから受け取る
    }
    logger.info(f"Sending request to Ollama API: {request_data}")

    # ストリーミングモードの場合
    if message.stream:
        return StreamingResponse(
            _stream_chat_response(
                session_id, request_data, settings.OLLAMA_API_BASE_URL, db
            ),
            media_type="text/event-stream",
        )

    # 非ストリーミングモードの場合（従来のコード）
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_API_BASE_URL}/api/chat",
            json=request_data,
        )
        if response.status_code != 200:
            logger.error(f"Ollama API error: {response.status_code} {response.text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get response from Ollama: {response.status_code} {response.text}",
            )

        response_data = response.json()
        logger.info(f"Received response from Ollama API: {response_data}")
        ai_response = response_data["message"]["content"]

    # AIのレスポンスを保存
    ai_message = Message(session_id=session_id, role="assistant", content=ai_response)
    db.add(ai_message)
    db.commit()

    return ChatResponse(response=ai_response, session_id=session_id)


# ストリーミングレスポンスを処理する非同期ジェネレータ
async def _stream_chat_response(session_id, request_data, ollama_api_base_url, db):
    # 最終的な完全なAI応答を保持する変数
    complete_response = ""

    # SSE (Server-Sent Events)形式のヘッダーを送信
    yield "data: " + json.dumps({"event": "start"}) + "\n\n"

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST", f"{ollama_api_base_url}/api/chat", json=request_data, timeout=300.0
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"Ollama API error: {response.status_code} {error_text}")
                yield "data: " + json.dumps(
                    {
                        "event": "error",
                        "message": f"Error from Ollama API: {response.status_code}",
                    }
                ) + "\n\n"
                return

            # Ollamaからのストリーミングレスポンスを処理
            async for line in response.aiter_lines():
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    # 応答テキストを取得
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        complete_response += chunk
                        # クライアントにチャンクを送信
                        yield "data: " + json.dumps(
                            {"event": "chunk", "content": chunk}
                        ) + "\n\n"

                    # 応答が完了したら、完了イベントを送信
                    if data.get("done", False):
                        # 完全な応答をDBに保存
                        ai_message = Message(
                            session_id=session_id,
                            role="assistant",
                            content=complete_response,
                        )
                        db.add(ai_message)
                        db.commit()

                        # クライアントに完了イベントを送信
                        yield "data: " + json.dumps(
                            {
                                "event": "done",
                                "content": complete_response,
                                "session_id": session_id,
                            }
                        ) + "\n\n"
                        break

                    # 少し待機して、クライアントに処理時間を与える
                    await asyncio.sleep(0.01)

                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e} for line: {line}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing stream: {e}")
                    yield "data: " + json.dumps(
                        {"event": "error", "message": str(e)}
                    ) + "\n\n"
                    break


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
