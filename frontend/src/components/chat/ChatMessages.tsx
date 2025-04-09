import { useRef, useEffect } from 'react';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
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

  // 新しいメッセージが追加されたら一番下にスクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
                {sessionName && <p className="text-xs mt-4 text-gray-400">モデル: {sessionName}</p>}
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
                <p className="whitespace-pre-wrap">{message.content}</p>
                <div className={`text-xs mt-1 ${message.role === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                  {message.timestamp.toLocaleTimeString()}
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
