'use client';

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { setUserActive } from '@/lib/api/admin';
import type { UserWithTokenLimits } from '@/lib/types';

interface UserManagementDialogProps {
  user: UserWithTokenLimits | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onUserUpdate: () => void;
  currentUserId?: number; // 現在のユーザーIDを渡して自分自身の無効化を防ぐ
}

export function UserManagementDialog({
  user: initialUser,
  isOpen,
  onOpenChange,
  onUserUpdate,
  currentUserId
}: UserManagementDialogProps) {
  const [user, setUser] = useState<UserWithTokenLimits | null>(initialUser);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // propsのuserが変更されたらローカルstateも更新
  useEffect(() => {
    setUser(initialUser);
  }, [initialUser]);

  if (!user) return null;

  const isSelf = currentUserId === user.id;

  const handleToggleActive = async (newActiveState: boolean) => {
    if (isSelf && !newActiveState) {
      setError('自分自身を無効化することはできません');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      await setUserActive(user.id, newActiveState);

      // APIが成功したらローカルのuser状態を即座に更新
      setUser(prevUser => prevUser ? { ...prevUser, is_active: newActiveState } : null);

      // 親コンポーネントにも通知（テーブルの更新など）
      onUserUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ユーザー状態の更新に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>ユーザー管理: {user.email}</DialogTitle>
          <DialogDescription>
            ユーザーの有効・無効状態を管理します。
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="p-3 rounded-md border border-red-200 bg-red-50 text-red-800 text-sm">
            {error}
          </div>
        )}

        <div className="space-y-6">
          {/* 基本情報 */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium">基本情報</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <label className="text-gray-500">ID</label>
                <p>{user.id}</p>
              </div>
              <div>
                <label className="text-gray-500">管理者権限</label>
                <div className="mt-1">
                  <Badge
                    style={{
                      backgroundColor: user.is_admin ? '#f3e8ff' : '#f3f4f6',
                      color: user.is_admin ? '#7c3aed' : '#374151',
                      border: `1px solid ${user.is_admin ? '#e9d5ff' : '#d1d5db'}`
                    }}
                  >
                    {user.is_admin ? "管理者" : "一般ユーザー"}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="text-gray-500">メール確認</label>
                <div className="mt-1">
                  <Badge
                    style={{
                      backgroundColor: user.is_verified ? '#dbeafe' : '#f3f4f6',
                      color: user.is_verified ? '#1e40af' : '#374151',
                      border: `1px solid ${user.is_verified ? '#bfdbfe' : '#d1d5db'}`
                    }}
                  >
                    {user.is_verified ? "確認済み" : "未確認"}
                  </Badge>
                </div>
              </div>
            </div>
            {isSelf && (
              <div className="p-2 rounded-md bg-blue-50 border border-blue-200 text-blue-800 text-xs">
                これはあなた自身のアカウントです
              </div>
            )}
          </div>

          {/* ユーザー状態管理 */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium">状態管理</h4>

            {/* アクティブ状態 */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="space-y-1 flex-1">
                <Label htmlFor="active-toggle" className="text-sm font-medium">
                  アクティブ状態
                </Label>
                <p className="text-xs text-gray-500">
                  無効化されたユーザーはログインできません
                </p>
                {isSelf && user.is_active && (
                  <p className="text-xs text-orange-600">
                    自分自身を無効化することはできません
                  </p>
                )}
              </div>
              <div className="flex items-center space-x-2">
                <Badge
                  style={{
                    backgroundColor: user.is_active ? '#dcfce7' : '#fee2e2',
                    color: user.is_active ? '#166534' : '#991b1b',
                    border: `1px solid ${user.is_active ? '#bbf7d0' : '#fecaca'}`
                  }}
                >
                  {user.is_active ? "有効" : "無効"}
                </Badge>
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    width: '32px',
                    height: '18px',
                    borderRadius: '9999px',
                    border: '1px solid #d1d5db',
                    backgroundColor: user.is_active ? '#10b981' : '#e5e7eb',
                    cursor: (isLoading || (isSelf && user.is_active)) ? 'not-allowed' : 'pointer',
                    opacity: (isLoading || (isSelf && user.is_active)) ? 0.5 : 1,
                    transition: 'all 0.2s',
                    position: 'relative'
                  }}
                  onClick={() => {
                    if (!isLoading && !(isSelf && user.is_active)) {
                      handleToggleActive(!user.is_active);
                    }
                  }}
                >
                  <div
                    style={{
                      width: '14px',
                      height: '14px',
                      borderRadius: '50%',
                      backgroundColor: '#ffffff',
                      position: 'absolute',
                      left: '2px',
                      transform: user.is_active ? 'translateX(14px)' : 'translateX(0px)',
                      transition: 'transform 0.2s',
                      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* トークン制限情報 */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium">トークン制限</h4>
            {user.token_limits && user.token_limits.length > 0 ? (
              <div className="space-y-2">
                {user.token_limits.map((limit) => (
                  <div key={limit.id} className="text-xs p-2 bg-gray-50 rounded">
                    <div className="font-medium">{limit.model_name}</div>
                    <div className="text-gray-600">
                      {limit.limit_value} トークン / {limit.period_value} {limit.period_unit}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-500">設定されたトークン制限はありません</p>
            )}
          </div>
        </div>

        <div className="flex justify-end space-x-2 pt-4">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            閉じる
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
} 
