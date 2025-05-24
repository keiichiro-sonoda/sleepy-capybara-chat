"use client";

import { useAuth } from '@/hooks/useAuth';
import { AIModel } from '@/utils/constants';
import { getAvailableModels } from '@/utils/api';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import Link from 'next/link';
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
  onToggleThinkingMode
}: ChatHeaderProps) => {
  const router = useRouter();

  const selectedModelInfo = availableModels.find(m => m.id === currentModel);
  const thinkingModeSupport = selectedModelInfo?.thinking_mode ?? "none";

  const isModelLoading = externalLoading;

  const isThinkingModeSwitchDisabled = thinkingModeSupport === "forced";
  const showThinkingModeSwitch = thinkingModeSupport !== "none";

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
              <span className="mr-2 text-sm hidden md:inline">{user.email}</span>
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
    </header>
  );
};

export default ChatHeader;
