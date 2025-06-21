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
  }, [isThinkingDetailsOpenForStreamingMessage, messages]);

  // メッセージの状態に応じたステータスメッセージを返す
  const getStatusMessage = (message: Message): string => {
    if (!message.isStreaming) return '';
    if (!message.content && !message.streamingThinkingContent) {
      return '応答を準備中...';
    }
    return '回答生成中...';
  };

  return (
    <div className="flex-1 overflow-y-auto bg-white px-2 sm:px-4 py-4">
      <div className="max-w-4xl mx-auto">
        {error && (
          <div className="mb-4 p-3 sm:p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm">
            <strong>エラー:</strong> {error}
          </div>
        )}

        {isNewChat && messages.length === 0 && !isLoading && (
          <div className="text-center py-8 sm:py-12">
            <h2 className="text-xl sm:text-2xl font-bold text-gray-600 mb-2">
              🦥 Sleepy Capybara Chatへようこそ！
            </h2>
            <p className="text-sm sm:text-base text-gray-500">
              新しい会話を始めましょう。下のフォームからメッセージを送信してください。
            </p>
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
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} mb-4 px-2 sm:px-4`}
              >
                <div
                  className={`max-w-[85%] sm:max-w-[70%] p-3 sm:p-4 rounded-lg ${message.role === 'user'
                    ? 'bg-blue-600 text-white ml-auto'
                    : 'bg-gray-200 text-gray-800'
                    }`}
                >
                  {/* User messages */}
                  {message.role === 'user' && (
                    <div className="text-sm sm:text-base">{message.content}</div>
                  )}

                  {/* Assistant messages */}
                  {message.role === 'assistant' && (
                    <>
                      {/* Model name for assistant */}
                      <div className="text-xs text-gray-500 mb-2 font-medium">
                        {getModelDisplayName(message.modelName)}
                      </div>

                      {/* Streaming thinking content */}
                      {isActivelyStreamingThinking && (
                        <details
                          open={isThinkingDetailsOpenForStreamingMessage}
                          className="mb-3 bg-gray-50 rounded p-2 sm:p-3 border"
                        >
                          <summary className="cursor-pointer text-sm font-medium text-gray-700">
                            🤔 思考中...
                          </summary>
                          <div
                            ref={thinkingContentRef}
                            className="mt-2 text-xs sm:text-sm text-gray-600 whitespace-pre-wrap bg-gray-100 p-2 rounded border-l-4 border-blue-400"
                          >
                            {streamingThinking}
                          </div>
                        </details>
                      )}

                      {/* Final thinking content */}
                      {showFinalThinking && (
                        <details className="mb-3 bg-gray-50 rounded p-2 sm:p-3 border">
                          <summary className="cursor-pointer text-sm font-medium text-gray-700">
                            🤔 思考過程を表示
                          </summary>
                          <div className="mt-2 text-xs sm:text-sm text-gray-600 whitespace-pre-wrap bg-gray-100 p-2 rounded border-l-4 border-blue-400">
                            {finalThinking}
                          </div>
                        </details>
                      )}

                      {/* Answer content */}
                      {showAnswerContent && (
                        <div className="text-sm sm:text-base whitespace-pre-wrap">
                          {message.content}
                          {message.isStreaming && getStatusMessage(message) && (
                            <div className="text-xs text-gray-500 mt-2 italic">
                              {getStatusMessage(message)}
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}

                  <div className="text-xs text-gray-400 mt-2 opacity-70">
                    {message.timestamp.toLocaleTimeString('ja-JP', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
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
