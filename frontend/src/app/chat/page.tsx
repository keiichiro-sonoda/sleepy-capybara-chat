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
  ChatSession,
  getAvailableModels
} from '@/utils/api';
import { AIModel } from '@/utils/constants';

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
  streamingThinkingContent?: string;
  thinkingContent?: string | null;
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
  const [isNewChat, setIsNewChat] = useState(true);
  const [useStreaming, setUseStreaming] = useState(true);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [loadingModel, setLoadingModel] = useState(true);
  const [availableModels, setAvailableModels] = useState<AIModel[]>([]);
  const [isThinkingModeEnabled, setIsThinkingModeEnabled] = useState(false);
  const [isThinkingDetailsOpen, setIsThinkingDetailsOpen] = useState(false);
  const [hasMoreSessions, setHasMoreSessions] = useState(true);
  const [loadingMoreSessions, setLoadingMoreSessions] = useState(false);

  useEffect(() => {
    const initApp = async () => {
      try {
        setLoadingModel(true);
        const [defaultModel, fetchedModels] = await Promise.all([
          getDefaultModel(),
          getAvailableModels()
        ]);
        setSelectedModel(defaultModel);
        setAvailableModels(fetchedModels);

        const defaultModelInfo = fetchedModels.find(m => m.id === defaultModel);
        if (defaultModelInfo) {
          if (defaultModelInfo.thinking_mode === 'forced') {
            setIsThinkingModeEnabled(true);
          } else if (defaultModelInfo.thinking_mode === 'optional') {
            setIsThinkingModeEnabled(false);
          } else {
            setIsThinkingModeEnabled(false);
          }
        }

      } catch (err) {
        console.error('Failed to initialize app:', err);
        setError("アプリの初期化に失敗しました。")
        setSelectedModel("qwen3");
        setAvailableModels([{ id: "qwen3", name: "Qwen3 Fallback", provider: "ollama", thinking_mode: "optional" }]);
      } finally {
        setLoadingModel(false);
      }

      fetchSessions();
    };

    initApp();
  }, []);

  const fetchSessions = async (offset: number = 0, append: boolean = false) => {
    try {
      if (!append) {
        setLoadingSessions(true);
      } else {
        setLoadingMoreSessions(true);
      }

      const chatSessions = await getChatSessions(20, offset);

      // updated_atを使って並べ替え（APIから既にソートされているが、フロントエンドでも確実にソート）
      const sortedSessions = chatSessions
        .map(session => ({
          ...session,
          lastMessageAt: new Date(session.updated_at || session.created_at)
        }))
        .sort((a, b) => b.lastMessageAt.getTime() - a.lastMessageAt.getTime());

      if (append) {
        // 既存のセッションIDを取得
        const existingIds = new Set(sessions.map(session => session.id));
        // 新しいセッションから既存IDを除外
        const newSessions = sortedSessions.filter(session => !existingIds.has(session.id));
        setSessions(prev => [...prev, ...newSessions]);
      } else {
        setSessions(sortedSessions);
      }

      // 取得したセッション数が20未満の場合、これ以上のセッションはない
      setHasMoreSessions(chatSessions.length === 20);
    } catch (err) {
      console.error('Failed to fetch chat sessions:', err);
      setError('チャットセッションの取得に失敗しました');
    } finally {
      setLoadingSessions(false);
      setLoadingMoreSessions(false);
    }
  };

  const loadMoreSessions = () => {
    if (!loadingMoreSessions && hasMoreSessions) {
      fetchSessions(sessions.length, true);
    }
  };

  const prepareNewChat = () => {
    setMessages([]);
    setCurrentSession(null);
    setIsNewChat(true);
    setError(null);
  };

  const createNewSession = async (modelName?: string): Promise<ChatSession> => {
    try {
      setIsLoading(true);
      const newSession = await createChatSession(modelName);
      setCurrentSession(newSession);

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

  const loadChatHistory = async (sessionId: number) => {
    try {
      setIsLoading(true);
      const history = await getChatMessages(sessionId);

      const formattedMessages: Message[] = history.map(msg => ({
        id: msg.id.toString(),
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: new Date(msg.created_at),
        modelName: msg.model_name,
        thinkingContent: msg.thinking_content
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

  const handleSessionSelect = async (sessionId: number) => {
    if (currentSession?.id === sessionId) return;

    const selectedSession = sessions.find(s => s.id === sessionId);
    if (selectedSession) {
      setCurrentSession(selectedSession);
      setIsNewChat(false);
      await loadChatHistory(sessionId);
    }
  };

  const handleDeleteSession = async (sessionId: number) => {
    try {
      setIsLoading(true);
      await deleteChatSession(sessionId);

      if (currentSession?.id === sessionId) {
        prepareNewChat();
      }

      await fetchSessions();

      setError(null);
    } catch (err) {
      console.error('Failed to delete chat session:', err);
      setError('チャットセッションの削除に失敗しました。もう一度お試しください。');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (message: string) => {
    if (loadingModel) return;

    setIsLoading(true);
    setError(null);
    try {
      const isNewChat = !currentSession;
      let sessionId = currentSession?.id;

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

      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        content: message,
        role: 'user',
        timestamp: new Date(),
        modelName: selectedModel
      };
      const newMessages = [...messages, userMessage];
      setMessages(newMessages);

      const aiMessageId = `temp-${Date.now() + 1}`;
      const aiMessage: Message = {
        id: aiMessageId,
        content: '',
        streamingThinkingContent: '',
        thinkingContent: null,
        role: 'assistant',
        timestamp: new Date(),
        isStreaming: true,
        modelName: selectedModel
      };

      setIsThinkingDetailsOpen(true);
      let firstAnswerChunkReceived = false;

      if (useStreaming) {
        setMessages([...newMessages, aiMessage]);

        try {
          await sendChatMessageStreaming(
            sessionId!,
            message,
            (chunk: string, type: 'thinking' | 'answer') => {
              setMessages(prev => prev.map(msg => {
                if (msg.id === aiMessageId) {
                  let updatedMsg = { ...msg };
                  if (type === 'thinking') {
                    updatedMsg.streamingThinkingContent = (updatedMsg.streamingThinkingContent || '') + chunk;
                  } else {
                    updatedMsg.content = msg.content + chunk;
                    if (!firstAnswerChunkReceived) {
                      setIsThinkingDetailsOpen(false);
                      firstAnswerChunkReceived = true;
                    }
                  }
                  return updatedMsg;
                } else {
                  return msg;
                }
              }));
            },
            async (fullResponse: string, responseModelName?: string, finalThinkingContent?: string | null) => {
              console.log('Streaming onComplete triggered. Full response length:', fullResponse.length, 'Model:', responseModelName, 'Thinking content length:', finalThinkingContent?.length);
              setIsThinkingDetailsOpen(false);
              setMessages(prev => prev.map(msg =>
                msg.id === aiMessageId
                  ? {
                    ...msg,
                    content: fullResponse,
                    isStreaming: false,
                    modelName: responseModelName || selectedModel,
                    thinkingContent: finalThinkingContent,
                    streamingThinkingContent: undefined
                  }
                  : msg
              ));
              await fetchSessions();
            },
            (errorMsg: string) => {
              setIsThinkingDetailsOpen(false);
              setError(`AIからの応答の取得に失敗しました: ${errorMsg}`);
              setMessages(prev => prev.map(msg =>
                msg.id === aiMessageId
                  ? { ...msg, content: 'エラーが発生しました', isStreaming: false }
                  : msg
              ));
            },
            selectedModel,
            isThinkingModeEnabled
          );
        } catch (error) {
          setIsThinkingDetailsOpen(false);
          console.error('Streaming error:', error);
          setError('ストリーミング中にエラーが発生しました');
        }
      } else {
        setIsThinkingDetailsOpen(false);
        const waitingMessage: Message = {
          ...aiMessage,
          content: '応答を待っています...',
          isStreaming: true
        };
        setMessages([...newMessages, waitingMessage]);

        try {
          const response = await sendChatMessage(
            sessionId!,
            message,
            selectedModel,
            isThinkingModeEnabled
          );
          const completedMessage: Message = {
            id: aiMessageId,
            content: response.response,
            role: 'assistant',
            timestamp: new Date(),
            modelName: selectedModel,
            isStreaming: false,
            thinkingContent: response.thinking_content ?? null
          };
          setMessages(prev => prev.map(msg => msg.id === aiMessageId ? completedMessage : msg));
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

  const toggleStreamingMode = () => {
    setUseStreaming(prev => !prev);
  };

  const toggleThinkingMode = () => {
    const modelInfo = availableModels.find(m => m.id === selectedModel);
    if (modelInfo?.thinking_mode === 'forced') return;

    setIsThinkingModeEnabled(prev => !prev);
  };

  const handleModelChange = (modelId: string) => {
    setSelectedModel(modelId);
    const modelInfo = availableModels.find(m => m.id === modelId);
    if (modelInfo) {
      if (modelInfo.thinking_mode === 'forced') {
        setIsThinkingModeEnabled(true);
      } else if (modelInfo.thinking_mode === 'optional') {
        setIsThinkingModeEnabled(false);
      } else {
        setIsThinkingModeEnabled(false);
      }
    }
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
        availableModels={availableModels}
        isThinkingModeEnabled={isThinkingModeEnabled}
        onToggleThinkingMode={toggleThinkingMode}
      />

      <div className="flex flex-1 overflow-hidden">
        <ChatSidebar
          sessions={sessions}
          currentSessionId={currentSession?.id || null}
          onSessionSelect={handleSessionSelect}
          onDeleteSession={handleDeleteSession}
          onNewChat={prepareNewChat}
          isLoading={loadingSessions || isLoading}
          hasMoreSessions={hasMoreSessions}
          loadingMoreSessions={loadingMoreSessions}
          onLoadMoreSessions={loadMoreSessions}
        />

        <div className="flex flex-col flex-1 overflow-hidden">
          <ChatMessages
            messages={messages}
            isLoading={isLoading || loadingModel}
            error={error}
            sessionName={currentSession?.model_name}
            isNewChat={isNewChat}
            isThinkingDetailsOpenForStreamingMessage={isThinkingDetailsOpen}
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

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <ChatContent />
    </ProtectedRoute>
  );
} 
