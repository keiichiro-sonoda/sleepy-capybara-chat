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
};

type ChatMessagesProps = {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  sessionName?: string;
  isNewChat?: boolean;
};

const ChatMessages = ({ messages, isLoading, error, sessionName, isNewChat = false }: ChatMessagesProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
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

  // メッセージの状態に応じたステータスメッセージを返す
  const getStatusMessage = (message: Message): string => {
    if (!message.isStreaming) return '';

    // コンテンツが空の場合は生成開始前
    if (!message.content || message.content === '') {
      return '応答を準備中...';
    }

    // コンテンツがある場合は生成中
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
          messages.map(message => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-4 ${message.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-gray-200 text-gray-800 rounded-bl-none'
                  }`}
              >
                {message.role === 'assistant' && message.modelName && !message.isStreaming && (
                  <div className="text-xs font-medium mb-2 text-gray-600 bg-gray-100 px-2 py-1 rounded inline-block">
                    {getModelDisplayName(message.modelName)}
                  </div>
                )}
                <p className="whitespace-pre-wrap">
                  {message.content}
                  {message.isStreaming && (
                    <span className="inline-block w-2 h-4 ml-1 bg-gray-500 animate-pulse" />
                  )}
                </p>
                <div className={`text-xs mt-1 ${message.role === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                  {message.timestamp.toLocaleTimeString()}
                  {message.isStreaming ? ` (${getStatusMessage(message)})` : ''}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ChatMessages; 
