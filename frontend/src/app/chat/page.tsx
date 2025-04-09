'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { useAuth } from '@/hooks/useAuth';
import {
  createChatSession,
  sendChatMessage,
  getChatSessions,
  getChatMessages,
  ChatSession
} from '@/utils/api';

import ChatSidebar from '@/components/chat/ChatSidebar';
import ChatMessages from '@/components/chat/ChatMessages';
import ChatInput from '@/components/chat/ChatInput';
import ChatHeader from '@/components/chat/ChatHeader';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
};

function ChatContent() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isNewChat, setIsNewChat] = useState(true); // 新規チャットモードかどうか

  // セッション一覧を取得
  const fetchSessions = async () => {
    try {
      setLoadingSessions(true);
      const chatSessions = await getChatSessions();
      setSessions(chatSessions);
    } catch (err) {
      console.error('Failed to fetch chat sessions:', err);
      setError('チャットセッションの取得に失敗しました');
    } finally {
      setLoadingSessions(false);
    }
  };

  // 初期化時にチャットセッション一覧を取得
  useEffect(() => {
    fetchSessions();
  }, []);

  // 新しいチャットの準備をする（セッションはまだ作成しない）
  const prepareNewChat = () => {
    setMessages([]);
    setCurrentSession(null);
    setIsNewChat(true);
    setError(null);
  };

  // 新しいチャットセッションを作成
  const createNewSession = async (): Promise<ChatSession> => {
    try {
      setIsLoading(true);
      const newSession = await createChatSession();
      setCurrentSession(newSession);

      // セッション一覧を更新
      await fetchSessions();

      setError(null);
      return newSession;
    } catch (err) {
      console.error('Failed to create chat session:', err);
      setError('チャットセッションの作成に失敗しました。もう一度お試しください。');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // チャット履歴を取得する関数
  const loadChatHistory = async (sessionId: number) => {
    try {
      setIsLoading(true);
      const history = await getChatMessages(sessionId);

      // APIから取得したメッセージを画面表示用の形式に変換
      const formattedMessages: Message[] = history.map(msg => ({
        id: msg.id.toString(),
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: new Date(msg.created_at)
      }));

      setMessages(formattedMessages);
      setError(null);
    } catch (err) {
      console.error('Failed to load chat history:', err);
      setError('チャット履歴の読み込みに失敗しました。');
    } finally {
      setIsLoading(false);
    }
  };

  // セッションを選択
  const handleSessionSelect = async (sessionId: number) => {
    if (currentSession?.id === sessionId) return;

    const selectedSession = sessions.find(s => s.id === sessionId);
    if (selectedSession) {
      setCurrentSession(selectedSession);
      setIsNewChat(false);
      await loadChatHistory(sessionId);
    }
  };

  // メッセージ送信処理
  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: content,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      let sessionId = currentSession?.id;

      // 新規チャットモードで、まだセッションがない場合は作成する
      if (isNewChat && !currentSession) {
        const newSession = await createChatSession();
        setCurrentSession(newSession);
        sessionId = newSession.id;
        setIsNewChat(false);
        await fetchSessions();
      }

      // メッセージを送信
      const response = await sendChatMessage(sessionId!, content);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to get AI response:', error);
      setError('AIからの応答の取得に失敗しました。もう一度お試しください。');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      <ChatHeader
        user={user}
        onLogout={logout}
        onHome={() => router.push('/')}
        currentModel={currentSession?.model_name}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* サイドバー */}
        <ChatSidebar
          sessions={sessions}
          currentSessionId={currentSession?.id || null}
          onSessionSelect={handleSessionSelect}
          onNewChat={prepareNewChat}
          isLoading={loadingSessions || isLoading}
        />

        {/* メインチャットエリア */}
        <div className="flex flex-col flex-1 overflow-hidden">
          <ChatMessages
            messages={messages}
            isLoading={isLoading}
            error={error}
            sessionName={currentSession?.model_name}
            isNewChat={isNewChat}
          />

          <ChatInput
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            disabled={false} // 常に入力可能に設定
          />
        </div>
      </div>
    </div>
  );
}

// ProtectedRouteでラップして認証を要求
export default function ChatPage() {
  return (
    <ProtectedRoute>
      <ChatContent />
    </ProtectedRoute>
  );
} 
