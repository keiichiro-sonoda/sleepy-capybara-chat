"use client";

import { useAuth } from '@/hooks/useAuth';
import { AIModel } from '@/utils/constants';
import { getAvailableModels } from '@/utils/api';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

type ChatHeaderProps = {
  user: ReturnType<typeof useAuth>['user'];
  onLogout: () => void;
  onHome: () => void;
  currentModel?: string;
  useStreaming: boolean;
  onToggleStreaming: () => void;
  onModelChange?: (model: string) => void;
  isLoading?: boolean;
};

const ChatHeader = ({
  user,
  onLogout,
  onHome,
  currentModel,
  useStreaming,
  onToggleStreaming,
  onModelChange,
  isLoading: externalLoading
}: ChatHeaderProps) => {
  const router = useRouter();
  const [models, setModels] = useState<AIModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const availableModels = await getAvailableModels();
        setModels(availableModels);
      } catch (error) {
        console.error('Failed to fetch models:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchModels();
  }, []);

  // 内部ローディング状態または外部から渡されたローディング状態を使用
  const isModelLoading = isLoading || externalLoading;

  return (
    <header className="bg-gray-800 text-white p-4 shadow-md">
      <div className="container mx-auto flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <button
            onClick={onHome}
            className="text-xl font-bold flex items-center hover:text-blue-300 transition-colors"
          >
            <span>🦥</span>
            <span className="ml-2">Sleepy Capybara Chat</span>
          </button>

          {/* モデル選択ドロップダウン */}
          <div className="ml-4">
            <select
              className="bg-gray-700 text-white rounded-md px-3 py-1 text-sm"
              value={currentModel || (models.length > 0 ? models[0].id : '')}
              onChange={e => onModelChange && onModelChange(e.target.value)}
              disabled={!onModelChange || isModelLoading || models.length === 0}
            >
              {isModelLoading ? (
                <option>読み込み中...</option>
              ) : (
                models.map((model: AIModel) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))
              )}
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* ストリーミングモード切り替えスイッチ */}
          <div className="flex items-center space-x-2">
            <span className="text-sm">ストリーミング:</span>
            <button
              onClick={onToggleStreaming}
              className={`relative inline-flex h-6 w-11 items-center rounded-full ${useStreaming ? 'bg-blue-600' : 'bg-gray-500'
                }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${useStreaming ? 'translate-x-6' : 'translate-x-1'
                  }`}
              />
            </button>
          </div>

          {user && (
            <div className="flex items-center space-x-2">
              <span className="mr-2 text-sm hidden md:inline">{user.email}</span>
              <button
                onClick={() => router.push('/profile')}
                className="text-sm bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded transition-colors"
              >
                プロフィール
              </button>
              <button
                onClick={onLogout}
                className="text-sm bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded transition-colors"
              >
                ログアウト
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default ChatHeader;
