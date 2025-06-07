"use client";

import { useRef, useEffect, useState } from 'react';
import { AIModel } from '@/utils/constants';
import { getAvailableModels } from '@/utils/api';

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

type ChatMessagesProps = {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  sessionName?: string;
  isNewChat?: boolean;
  isThinkingDetailsOpenForStreamingMessage?: boolean;
};

const ChatMessages = ({ messages, isLoading, error, sessionName, isNewChat = false, isThinkingDetailsOpenForStreamingMessage }: ChatMessagesProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const thinkingContentRef = useRef<HTMLDivElement>(null);
  const [models, setModels] = useState<AIModel[]>([]);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const availableModels = await getAvailableModels();
        setModels(availableModels);
      } catch (error) {
        console.error('Failed to fetch models:', error);
      }
    };

    fetchModels();
  }, []);

  // モデル名から表示用の名前を取得
  const getModelDisplayName = (modelId?: string): string => {
    if (!modelId) return 'Unknown';
    const model = models.find(m => m.id === modelId);
    return model ? model.name : modelId;
  };

  // 新しいメッセージが追加されたら一番下にスクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 思考内容が更新されたら思考内容の一番下にスクロール
  useEffect(() => {
    if (isThinkingDetailsOpenForStreamingMessage) {
      thinkingContentRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.map(m => m.streamingThinkingContent).join(''), isThinkingDetailsOpenForStreamingMessage]);

  // メッセージの状態に応じたステータスメッセージを返す
  const getStatusMessage = (message: Message): string => {
    if (!message.isStreaming) return '';
    if (!message.content && !message.streamingThinkingContent) {
      return '応答を準備中...';
    }
    return '回答生成中...';
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6">
      <div className="max-w-3xl mx-auto space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg">
            <p>{error}</p>
          </div>
        )}

        {messages.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            {isLoading ? (
              <>
                <p>チャットセッションを準備中...</p>
                <div className="mt-4 flex justify-center">
                  <svg className="animate-spin w-8 h-8 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
              </>
            ) : (
              <>
                <p>{isNewChat ? 'AIとの新しい会話を始めましょう' : 'チャット履歴がありません'}</p>
                <p className="text-sm mt-2">例: 「こんにちは、何か質問があります」</p>
                {sessionName && <p className="text-xs mt-4 text-gray-400">デフォルトモデル: {getModelDisplayName(sessionName)}</p>}
              </>
            )}
          </div>
        ) : (
          messages.map(message => {
            // Determine streaming and final thinking states
            const isStreamingAIMessage = message.role === 'assistant' && message.isStreaming;
            const streamingThinking = message.streamingThinkingContent;
            const finalThinking = !message.isStreaming ? message.thinkingContent : null;
            // Determine if streaming thinking in progress
            const isActivelyStreamingThinking = isStreamingAIMessage && Boolean(streamingThinking);
            // Determine if final thinking exists
            const showFinalThinking = !message.isStreaming && Boolean(finalThinking);
            // Always show answer content after streaming thinking or final thinking
            const showAnswerContent = Boolean(message.content);

            return (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg ${message.role === 'user'
                    ? 'bg-blue-600 text-white rounded-br-none'
                    : 'bg-gray-200 text-gray-800 rounded-bl-none'
                    } p-4`}
                >
                  {message.role === 'assistant' && (
                    <div className="text-xs font-medium mb-2 text-gray-600 bg-gray-100 px-2 py-0.5 rounded inline-block">
                      {getModelDisplayName(message.modelName)}
                    </div>
                  )}

                  {/* ストリーム中の思考表示 */}
                  {isActivelyStreamingThinking && (
                    <div className="mb-4 bg-yellow-50 border border-yellow-400 p-3 rounded text-sm text-yellow-900">
                      <div className="flex items-center mb-2">
                        <svg className="animate-spin h-4 w-4 mr-2 text-yellow-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span className="font-medium">AIが思考中...</span>
                      </div>
                      <pre className="whitespace-pre-wrap bg-yellow-100 p-2 rounded max-h-40 overflow-auto text-xs">
                        {streamingThinking}
                      </pre>
                    </div>
                  )}
                  {/* 完了後の思考表示 */}
                  {showFinalThinking && (
                    <details className="mb-2 cursor-pointer group">
                      <summary className="text-xs text-gray-500 hover:text-gray-700 list-none outline-none">
                        <span className="font-medium">思考過程を表示...</span>
                      </summary>
                      <div className="mt-1 p-2 border-l-2 border-gray-300 bg-gray-100 rounded-r text-xs text-gray-600 whitespace-pre-wrap">
                        {finalThinking}
                      </div>
                    </details>
                  )}

                  {/* 回答内容 */}
                  {showAnswerContent && (
                    <p className="whitespace-pre-wrap">
                      {message.content}
                      {message.isStreaming && (
                        <span className="inline-block w-2 h-4 ml-1 bg-gray-500 animate-pulse" />
                      )}
                    </p>
                  )}
                  <div className={`text-xs mt-1 ${message.role === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                    {message.timestamp.toLocaleTimeString()}
                    {message.isStreaming && ` (${getStatusMessage(message)})`}
                  </div>
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ChatMessages; 
