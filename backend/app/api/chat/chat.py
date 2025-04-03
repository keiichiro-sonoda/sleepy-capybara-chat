from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.chat import ChatSession, Message
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSession as ChatSessionSchema,
    MessageCreate,
    ChatResponse
)

router = APIRouter()
settings = get_settings()

@router.post("/sessions", response_model=ChatSessionSchema)
async def create_chat_session(
    session: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_session = ChatSession(
        user_id=current_user.id,
        model_name=session.model_name
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@router.get("/sessions", response_model=list[ChatSessionSchema])
async def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(ChatSession).filter(ChatSession.user_id == current_user.id).all()

@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def create_message(
    session_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # セッションの存在確認
    chat_session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    # ユーザーメッセージの保存
    user_message = Message(
        session_id=session_id,
        role="user",
        content=message.content
    )
    db.add(user_message)
    db.commit()
    
    # Ollama APIへのリクエスト
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.OLLAMA_API_BASE_URL}/api/generate",
            json={
                "model": chat_session.model_name,
                "prompt": message.content,
                "stream": False
            }
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get response from Ollama"
            )
        
        ai_response = response.json()["response"]
    
    # AIのレスポンスを保存
    ai_message = Message(
        session_id=session_id,
        role="assistant",
        content=ai_response
    )
    db.add(ai_message)
    db.commit()
    
    return ChatResponse(
        response=ai_response,
        session_id=session_id
    ) 
