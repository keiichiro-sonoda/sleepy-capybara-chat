import { ChatSession, updateChatSessionName } from '@/utils/api';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';
import { useEffect, useRef, useState } from 'react';

// ChatSessionを拡張した型を定義
interface ExtendedChatSession extends ChatSession {
  lastMessageAt?: Date;
}

type ChatSidebarProps = {
  sessions: ExtendedChatSession[];
  currentSessionId: number | null;
  onSessionSelect: (sessionId: number) => void;
  onDeleteSession: (sessionId: number) => void;
  onNewChat: () => void;
  isLoading: boolean;
  hasMoreSessions?: boolean;
  loadingMoreSessions?: boolean;
  onLoadMoreSessions?: () => void;
  onSessionUpdate?: () => void;
};

const ChatSidebar = ({
  sessions,
  currentSessionId,
  onSessionSelect,
  onDeleteSession,
  onNewChat,
  isLoading,
  hasMoreSessions = false,
  loadingMoreSessions = false,
  onLoadMoreSessions,
  onSessionUpdate,
}: ChatSidebarProps) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [editingSessionId, setEditingSessionId] = useState<number | null>(null);
  const [newName, setNewName] = useState('');

  // 日付をフォーマットする関数
  const formatDate = (date?: Date) => {
    if (!date) return '';
    return formatDistanceToNow(date, { addSuffix: true, locale: ja });
  };

  // スクロールイベントハンドラ
  useEffect(() => {
    const scrollContainer = scrollContainerRef.current;
    if (!scrollContainer || !onLoadMoreSessions) return;

    let isScrollHandling = false;

    const handleScroll = () => {
      if (isScrollHandling) return;

      const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
      const remaining = scrollHeight - scrollTop - clientHeight;

      // スクロールが下から50px以内に来たら追加読み込み
      if (remaining < 50 && hasMoreSessions && !loadingMoreSessions) {
        isScrollHandling = true;
        onLoadMoreSessions();

        // 500ms後にフラグをリセット
        setTimeout(() => {
          isScrollHandling = false;
        }, 500);
      }
    };

    scrollContainer.addEventListener('scroll', handleScroll);
    return () => scrollContainer.removeEventListener('scroll', handleScroll);
  }, [hasMoreSessions, loadingMoreSessions, onLoadMoreSessions]);

  const handleEditSession = (sessionId: number) => {
    setEditingSessionId(sessionId);
    setNewName(sessions.find(s => s.id === sessionId)?.name || '');
  };

  const handleSaveSession = async () => {
    if (editingSessionId !== null && newName.trim()) {
      try {
        await updateChatSessionName(editingSessionId, newName.trim());
        // セッション一覧を更新するため、再読み込み処理が必要
        setEditingSessionId(null);
        setNewName('');
        if (onSessionUpdate) {
          onSessionUpdate();
        }
      } catch (error) {
        console.error('Failed to update session name:', error);
      }
    }
  };

  const handleCancelEdit = () => {
    setEditingSessionId(null);
    setNewName('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveSession();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  return (
    <div className="w-64 bg-gray-800 text-white h-full flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <button
          onClick={onNewChat}
          disabled={isLoading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span>新しいチャット</span>
        </button>
      </div>

      <div className="flex-1 overflow-hidden">
        <div className="p-2 h-full flex flex-col">
          <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-2">チャット履歴</h3>
          {sessions.length === 0 ? (
            <div className="text-center py-4 text-gray-400 text-sm">
              {isLoading ? '読み込み中...' : '履歴がありません'}
            </div>
          ) : (
            <div ref={scrollContainerRef} className="flex-1 overflow-y-auto space-y-1">
              {sessions.map((session) => (
                <div key={session.id} className="flex items-center min-w-0">
                  <button
                    onClick={() => onSessionSelect(session.id)}
                    className={`flex-1 min-w-0 text-left px-3 py-2 rounded-lg transition-colors ${currentSessionId === session.id
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-300 hover:bg-gray-700'
                      }`}
                  >
                    <div className="flex items-center min-w-0">
                      <div className="min-w-0 flex-1">
                        {editingSessionId === session.id ? (
                          <input
                            type="text"
                            value={newName}
                            onChange={(e) => setNewName(e.target.value)}
                            onBlur={handleCancelEdit}
                            onKeyDown={handleKeyPress}
                            className="bg-gray-700 text-white px-2 py-1 rounded-lg"
                            autoFocus
                            onFocus={(e) => e.target.select()}
                            style={{ width: '100%', minWidth: '120px' }}
                          />
                        ) : (
                          <>
                            <p className="truncate text-sm">
                              {session.name || new Date(session.created_at).toLocaleDateString()}
                            </p>
                            <div className="text-xs flex items-center min-w-0">
                              <span className="text-gray-400 flex-shrink-0">{session.model_name}</span>
                              {session.lastMessageAt && (
                                <span className="text-gray-500 ml-2 truncate">
                                  {formatDate(session.lastMessageAt)}
                                </span>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  </button>
                  <div className="flex items-center flex-shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditSession(session.id);
                      }}
                      className="p-2 text-gray-400 hover:text-blue-400 flex-shrink-0"
                      title="名前を編集"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                        />
                      </svg>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm('このチャット履歴を削除してもよろしいですか？')) {
                          onDeleteSession(session.id);
                        }
                      }}
                      className="p-2 text-gray-400 hover:text-red-400 flex-shrink-0"
                      title="削除"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}

              {/* 追加読み込み用のローディング表示 */}
              {loadingMoreSessions && (
                <div className="text-center py-2 text-gray-400 text-sm">
                  <div className="flex justify-center items-center">
                    <svg className="animate-spin w-4 h-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    追加読み込み中...
                  </div>
                </div>
              )}

              {/* すべて読み込み完了の表示 */}
              {!hasMoreSessions && sessions.length > 0 && (
                <div className="text-center py-2 text-gray-500 text-xs">すべてのセッションを表示しました</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatSidebar; 
