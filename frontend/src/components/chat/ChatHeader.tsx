import { User } from '@/hooks/useAuth';

type ChatHeaderProps = {
  user: User | null;
  onLogout: () => void;
  onHome: () => void;
  currentModel?: string;
  useStreaming?: boolean;
  onToggleStreaming?: () => void;
};

const ChatHeader = ({
  user,
  onLogout,
  onHome,
  currentModel,
  useStreaming = true,
  onToggleStreaming
}: ChatHeaderProps) => {
  return (
    <header className="bg-white shadow p-4">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        <div className="flex items-center">
          <h1 className="text-xl font-semibold text-gray-800">AIチャット</h1>
          {currentModel && (
            <span className="ml-2 px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
              {currentModel}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          {onToggleStreaming && (
            <button
              onClick={onToggleStreaming}
              className={`px-3 py-1 rounded text-sm ${useStreaming
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-700'
                }`}
              title={useStreaming ? 'ストリーミングモード: ON' : 'ストリーミングモード: OFF'}
            >
              {useStreaming ? 'ストリーム' : '一括'}
            </button>
          )}
          <span className="text-sm text-gray-600">{user?.email}</span>
          <button
            onClick={onHome}
            className="text-gray-600 hover:text-gray-800"
          >
            ホームに戻る
          </button>
          <button
            onClick={onLogout}
            className="text-red-600 hover:text-red-800"
          >
            ログアウト
          </button>
        </div>
      </div>
    </header>
  );
};

export default ChatHeader; 
