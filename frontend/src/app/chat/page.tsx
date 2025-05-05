'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { useAuth } from '@/hooks/useAuth';
import {
  createChatSession,
  sendChatMessage,
  sendChatMessageStreaming,
  getChatSessions,
  getChatMessages,
  deleteChatSession,
  getDefaultModel,
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
  isStreaming?: boolean;
  modelName?: string;
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
  const [useStreaming, setUseStreaming] = useState(true); // ストリーミングモードを使用するかどうか
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [loadingModel, setLoadingModel] = useState(true);

  // デフォルトモデルとセッション一覧を初期化時に取得
  useEffect(() => {
    const initApp = async () => {
      try {
        setLoadingModel(true);
        const defaultModel = await getDefaultModel();
        setSelectedModel(defaultModel);
      } catch (err) {
        console.error('Failed to fetch default model:', err);
        // フォールバックとして一時的なデフォルトモデルを使用
        setSelectedModel("qwen3");
      } finally {
        setLoadingModel(false);
      }

      fetchSessions();
    };

    initApp();
  }, []);

  // セッション一覧を取得
  const fetchSessions = async () => {
    try {
      setLoadingSessions(true);
      const chatSessions = await getChatSessions();

      // 最新のメッセージ日時情報を取得するため、各セッションのメッセージを取得
      const sessionsWithLastMessageAt = await Promise.all(
        chatSessions.map(async (session) => {
          try {
            const messages = await getChatMessages(session.id);
            // メッセージがある場合は最後のメッセージの日時、ない場合はセッション作成日時
            const lastMessageAt = messages.length > 0
              ? new Date(messages[messages.length - 1].created_at)
              : new Date(session.created_at);

            return {
              ...session,
              lastMessageAt
            };
          } catch (err) {
            console.error(`Failed to fetch messages for session ${session.id}:`, err);
            return {
              ...session,
              lastMessageAt: new Date(session.created_at)
            };
          }
        })
      );

      // 最後のメッセージ日時の降順でソート（新しい順）
      const sortedSessions = sessionsWithLastMessageAt.sort((a, b) =>
        b.lastMessageAt.getTime() - a.lastMessageAt.getTime()
      );

      setSessions(sortedSessions);
    } catch (err) {
      console.error('Failed to fetch chat sessions:', err);
      setError('チャットセッションの取得に失敗しました');
    } finally {
      setLoadingSessions(false);
    }
  };

  // 新しいチャットの準備をする（セッションはまだ作成しない）
  const prepareNewChat = () => {
    setMessages([]);
    setCurrentSession(null);
    setIsNewChat(true);
    setError(null);
  };

  // 新しいチャットセッションを作成
  const createNewSession = async (modelName?: string): Promise<ChatSession> => {
    try {
      setIsLoading(true);
      const newSession = await createChatSession(modelName);
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
        timestamp: new Date(msg.created_at),
        modelName: msg.model_name
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

  // セッションを削除
  const handleDeleteSession = async (sessionId: number) => {
    try {
      setIsLoading(true);
      await deleteChatSession(sessionId);

      // 現在表示中のセッションが削除された場合は新規チャットモードに
      if (currentSession?.id === sessionId) {
        prepareNewChat();
      }

      // セッション一覧を更新
      await fetchSessions();

      setError(null);
    } catch (err) {
      console.error('Failed to delete chat session:', err);
      setError('チャットセッションの削除に失敗しました。もう一度お試しください。');
    } finally {
      setIsLoading(false);
    }
  };

  // メッセージ送信処理
  const handleSendMessage = async (message: string) => {
    if (loadingModel) return; // モデルロード中は送信できないようにする

    setIsLoading(true);
    setError(null);
    try {
      const isNewChat = !currentSession;
      let sessionId = currentSession?.id;

      // 新規チャットの場合はセッションを作成
      if (isNewChat) {
        try {
          const newSession = await createNewSession(selectedModel);
          sessionId = newSession.id;
          setIsNewChat(false);
        } catch (err) {
          console.error('Failed to create chat session:', err);
          setError('チャットセッションの作成に失敗しました');
          setIsLoading(false);
          return;
        }
      }

      // ユーザーメッセージを追加
      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        content: message,
        role: 'user',
        timestamp: new Date(),
        modelName: selectedModel
      };

      const newMessages = [...messages, userMessage];
      setMessages(newMessages);

      // AIメッセージの一時プレースホルダー
      const aiMessageId = `temp-${Date.now() + 1}`;
      const aiMessage: Message = {
        id: aiMessageId,
        content: '',
        role: 'assistant',
        timestamp: new Date(),
        isStreaming: true,
        modelName: selectedModel
      };

      if (useStreaming) {
        // ストリーミングモードでメッセージを送信
        setMessages([...newMessages, aiMessage]);

        try {
          await sendChatMessageStreaming(
            sessionId!,
            message,
            // チャンク受信時のコールバック
            (chunk: string) => {
              setMessages(prev => prev.map(msg =>
                msg.id === aiMessageId
                  ? { ...msg, content: msg.content + chunk }
                  : msg
              ));
            },
            // 完了時のコールバック
            async (fullResponse: string, responseModelName?: string) => {
              setMessages(prev => prev.map(msg =>
                msg.id === aiMessageId
                  ? {
                    ...msg,
                    content: fullResponse,
                    isStreaming: false,
                    modelName: responseModelName || selectedModel
                  }
                  : msg
              ));
              // 最新のセッション一覧を取得
              await fetchSessions();
            },
            // エラー時のコールバック
            (errorMsg: string) => {
              setError(`AIからの応答の取得に失敗しました: ${errorMsg}`);
              setMessages(prev => prev.map(msg =>
                msg.id === aiMessageId
                  ? { ...msg, content: 'エラーが発生しました', isStreaming: false }
                  : msg
              ));
            },
            // 使用するモデル
            selectedModel
          );
        } catch (error) {
          console.error('Streaming error:', error);
          setError('ストリーミング中にエラーが発生しました');
        }
      } else {
        // 非ストリーミングモードでメッセージを送信
        const waitingMessage: Message = {
          ...aiMessage,
          content: '応答を待っています...',
          isStreaming: true  // isStreamingフラグは維持（ローディングインジケータのため）
        };
        setMessages([...newMessages, waitingMessage]);

        try {
          const response = await sendChatMessage(sessionId!, message, selectedModel);

          const completedMessage: Message = {
            id: aiMessageId,
            content: response.response,
            role: 'assistant',
            timestamp: new Date(),
            modelName: selectedModel,
            isStreaming: false  // 明示的にfalseに設定
          };

          setMessages(prev =>
            prev.map(msg => msg.id === aiMessageId ? completedMessage : msg)
          );

          // 最新のセッション一覧を取得
          await fetchSessions();
        } catch (error) {
          console.error('Chat message error:', error);
          setError('メッセージの送信に失敗しました');
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setError('メッセージの送信中にエラーが発生しました');
    } finally {
      setIsLoading(false);
    }
  };

  // ストリーミングモードの切り替え
  const toggleStreamingMode = () => {
    setUseStreaming(prev => !prev);
  };

  // モデル選択の変更ハンドラ
  const handleModelChange = (model: string) => {
    setSelectedModel(model);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      <ChatHeader
        user={user}
        onLogout={logout}
        onHome={() => router.push('/')}
        currentModel={selectedModel}
        useStreaming={useStreaming}
        onToggleStreaming={toggleStreamingMode}
        onModelChange={handleModelChange}
        isLoading={loadingModel}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* サイドバー */}
        <ChatSidebar
          sessions={sessions}
          currentSessionId={currentSession?.id || null}
          onSessionSelect={handleSessionSelect}
          onDeleteSession={handleDeleteSession}
          onNewChat={prepareNewChat}
          isLoading={loadingSessions || isLoading}
        />

        {/* メインチャットエリア */}
        <div className="flex flex-col flex-1 overflow-hidden">
          <ChatMessages
            messages={messages}
            isLoading={isLoading || loadingModel}
            error={error}
            sessionName={currentSession?.model_name}
            isNewChat={isNewChat}
          />

          <ChatInput
            onSendMessage={handleSendMessage}
            isLoading={isLoading || loadingModel}
            disabled={(!currentSession && messages.length > 0) || loadingModel}
            isStreaming={useStreaming}
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
