"use client";

import { useAuth } from '@/hooks/useAuth';
import { AIModel } from '@/utils/constants';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';

type ChatHeaderProps = {
  user: ReturnType<typeof useAuth>['user'];
  onLogout: () => void;
  onHome: () => void;
  currentModel?: string;
  useStreaming: boolean;
  onToggleStreaming: () => void;
  onModelChange?: (model: string) => void;
  isLoading?: boolean;
  availableModels: AIModel[];
  isThinkingModeEnabled?: boolean;
  onToggleThinkingMode?: () => void;
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
};

const ChatHeader = ({
  user,
  onLogout,
  onHome,
  currentModel,
  useStreaming,
  onToggleStreaming,
  onModelChange,
  isLoading: externalLoading,
  availableModels,
  isThinkingModeEnabled,
  onToggleThinkingMode,
  onToggleSidebar,
  isSidebarOpen
}: ChatHeaderProps) => {
  const router = useRouter();

  const selectedModelInfo = availableModels.find(m => m.id === currentModel);
  const thinkingModeSupport = selectedModelInfo?.thinking_mode ?? "none";

  const isModelLoading = externalLoading;

  const isThinkingModeSwitchDisabled = thinkingModeSupport === "forced";
  const showThinkingModeSwitch = thinkingModeSupport !== "none";

  return (
    <header className="bg-gray-800 text-white shadow-md">
      <div className="container mx-auto px-4 py-3">
        {/* Mobile Header Layout */}
        <div className="flex lg:hidden justify-between items-center">
          <div className="flex items-center space-x-3">
            {onToggleSidebar && (
              <button
                onClick={onToggleSidebar}
                className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
                aria-label="サイドバーを開く"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            )}
            <button
              onClick={onHome}
              className="text-lg font-bold flex items-center hover:text-blue-300 transition-colors"
            >
              <span>🦥</span>
              <span className="ml-1 hidden sm:inline">Sleepy Capybara</span>
            </button>
          </div>
        </div>

        {/* Mobile Settings Row */}
        <div className="lg:hidden mt-3 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-300 mb-1">モデル</label>
              <select
                className="w-full bg-gray-700 text-white rounded-md px-2 py-1 text-sm"
                value={currentModel || (availableModels.length > 0 ? availableModels[0].id : '')}
                onChange={e => onModelChange && onModelChange(e.target.value)}
                disabled={!onModelChange || isModelLoading || availableModels.length === 0}
              >
                {isModelLoading ? (
                  <option>読み込み中...</option>
                ) : (
                  availableModels.map((model: AIModel) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))
                )}
              </select>
            </div>

            <div className="flex flex-col space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-300">ストリーミング</span>
                <button
                  onClick={onToggleStreaming}
                  className={`relative inline-flex h-5 w-9 items-center rounded-full ${useStreaming ? 'bg-blue-600' : 'bg-gray-500'}`}
                >
                  <span
                    className={`inline-block h-3 w-3 transform rounded-full bg-white transition ${useStreaming ? 'translate-x-5' : 'translate-x-1'}`}
                  />
                </button>
              </div>

              {showThinkingModeSwitch && onToggleThinkingMode && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-300">思考モード</span>
                  <button
                    onClick={onToggleThinkingMode}
                    disabled={isThinkingModeSwitchDisabled}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${isThinkingModeEnabled ? 'bg-green-600' : 'bg-gray-500'} ${isThinkingModeSwitchDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <span
                      className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${isThinkingModeEnabled ? 'translate-x-5' : 'translate-x-1'}`}
                    />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Mobile Action Buttons Row */}
          {user && (
            <div className="flex items-center justify-center space-x-2 pt-2 border-t border-gray-700">
              <Button
                variant="ghost"
                size="sm"
                className="text-xs bg-gray-700 hover:bg-gray-600 px-3 py-2 rounded transition-colors flex-1 max-w-24"
                onClick={() => router.push('/profile')}
              >
                プロフィール
              </Button>
              {user.is_admin && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs bg-gray-700 hover:bg-gray-600 px-3 py-2 rounded transition-colors flex-1 max-w-20"
                  onClick={() => router.push('/token-management')}
                >
                  管理
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="text-xs bg-red-600 hover:bg-red-700 px-3 py-2 rounded transition-colors flex-1 max-w-24"
                onClick={onLogout}
              >
                ログアウト
              </Button>
            </div>
          )}
        </div>

        {/* Desktop Header Layout */}
        <div className="hidden lg:flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <button
              onClick={onHome}
              className="text-xl font-bold flex items-center hover:text-blue-300 transition-colors"
            >
              <span>🦥</span>
              <span className="ml-2">Sleepy Capybara Chat</span>
            </button>

            <div className="ml-4">
              <select
                className="bg-gray-700 text-white rounded-md px-3 py-1 text-sm"
                value={currentModel || (availableModels.length > 0 ? availableModels[0].id : '')}
                onChange={e => onModelChange && onModelChange(e.target.value)}
                disabled={!onModelChange || isModelLoading || availableModels.length === 0}
              >
                {isModelLoading ? (
                  <option>読み込み中...</option>
                ) : (
                  availableModels.map((model: AIModel) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))
                )}
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {showThinkingModeSwitch && onToggleThinkingMode && (
              <div className="flex items-center space-x-2">
                <span className="text-sm">思考モード:</span>
                <button
                  onClick={onToggleThinkingMode}
                  disabled={isThinkingModeSwitchDisabled}
                  title={thinkingModeSupport === 'forced' ? "このモデルは常に思考モードが有効です" : (isThinkingModeEnabled ? "思考モード: ON" : "思考モード: OFF")}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isThinkingModeEnabled ? 'bg-green-600' : 'bg-gray-500'} ${isThinkingModeSwitchDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isThinkingModeEnabled ? 'translate-x-6' : 'translate-x-1'}`}
                  />
                </button>
              </div>
            )}

            <div className="flex items-center space-x-2">
              <span className="text-sm">ストリーミング:</span>
              <button
                onClick={onToggleStreaming}
                className={`relative inline-flex h-6 w-11 items-center rounded-full ${useStreaming ? 'bg-blue-600' : 'bg-gray-500'}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${useStreaming ? 'translate-x-6' : 'translate-x-1'}`}
                />
              </button>
            </div>

            {user && (
              <div className="flex items-center space-x-2">
                <span className="mr-2 text-sm hidden xl:inline">{user.email}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-sm bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded transition-colors cursor-pointer"
                  onClick={() => router.push('/profile')}
                >
                  プロフィール
                </Button>
                {user.is_admin && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-sm bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded transition-colors cursor-pointer"
                    onClick={() => router.push('/token-management')}
                  >
                    トークン管理
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-sm bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded transition-colors cursor-pointer"
                  onClick={onLogout}
                >
                  ログアウト
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default ChatHeader;
