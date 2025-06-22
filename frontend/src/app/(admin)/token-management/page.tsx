'use client';
import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { ColumnDef } from '@tanstack/react-table'; // ColumnDef をインポート

// UI Components (Shadcn/ui)
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "./components/data-table"; // DataTable をインポート
import { columns as baseColumns } from "./components/columns";   // Base columns をインポート (別名で)
import { EditTokenLimitsDialog } from "./components/edit-token-limits-dialog"; // モーダルをインポート
import { UserManagementDialog } from "./components/user-management-dialog"; // ユーザー管理ダイアログをインポート
import { Button } from "@/components/ui/button"; // Button をインポート (アクションカラム用)

// API呼び出し関数
import { fetchCurrentUser } from '@/utils/api';
import { getUsersWithTokenLimitsSummary } from '@/lib/api/admin'; // 作成した関数をインポート
import type { User } from '@/hooks/useAuth';
import type { UserWithTokenLimits } from '@/lib/types'; // 型定義をインポート

export default function TokenManagementPage() {
  const [user, setUser] = useState<User | null>(null);
  const [usersWithLimits, setUsersWithLimits] = useState<UserWithTokenLimits[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false); // モーダル表示状態
  const [selectedUserForEdit, setSelectedUserForEdit] = useState<UserWithTokenLimits | null>(null); // 編集対象ユーザー
  const [isUserManagementDialogOpen, setIsUserManagementDialogOpen] = useState(false); // ユーザー管理ダイアログ表示状態
  const [selectedUserForManagement, setSelectedUserForManagement] = useState<UserWithTokenLimits | null>(null); // ユーザー管理対象ユーザー
  const router = useRouter();

  // データ取得関数
  const fetchData = async () => {
    // setLoading(true); // fetchDataを呼ぶ前に setLoading(true) を行う前提
    setError(null);
    try {
      // ユーザー自身の情報をまず取得 (初回のみ)
      if (!user) {
        const userData = await fetchCurrentUser();
        setUser(userData);
        if (!userData?.is_admin) {
          setLoading(false);
          return; // 管理者でなければここで終了
        }
      } else if (!user.is_admin) {
        setLoading(false);
        return; // 既にユーザー情報があり、管理者でない場合も終了
      }

      // 管理者の場合は全ユーザーのトークン制限を取得
      const limitsData = await getUsersWithTokenLimitsSummary();
      setUsersWithLimits(limitsData);

    } catch (err) {
      console.error("Failed to fetch data:", err);
      let errorMessage = "データの読み込みに失敗しました。";
      if (err instanceof Error) {
        errorMessage = err.message;
      }
      if ((err as { response?: { status?: number }; message?: string })?.response?.status === 401 ||
        (err as { response?: { status?: number }; message?: string })?.message?.includes('認証')) {
        router.push('/auth/login');
        return;
      }
      setError(errorMessage);
    } finally {
      // fetchData内で setLoading(false) を行うと、初回ロード判定がおかしくなる可能性があるため、
      // 呼び出し元で適切に管理する
      // setLoading(false); 
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchData().finally(() => setLoading(false)); // 初回データ取得
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 初回のみ実行

  const handleOpenEditDialog = (userToEdit: UserWithTokenLimits) => {
    setSelectedUserForEdit(userToEdit);
    setIsEditDialogOpen(true);
  };

  const handleOpenUserManagementDialog = (userToManage: UserWithTokenLimits) => {
    setSelectedUserForManagement(userToManage);
    setIsUserManagementDialogOpen(true);
  };

  const handleLimitsUpdate = () => {
    // トークン制限が更新されたらデータを再取得してテーブルを更新
    fetchData(); // 再取得（ローディング状態は管理しない）
  };

  const handleUserUpdate = () => {
    // ユーザー情報が更新されたらデータを再取得してテーブルを更新
    fetchData(); // 再取得（ローディング状態は管理しない）
  };

  // DataTableに渡すカラム定義を動的に生成（編集ハンドラを渡すため）
  const tableColumns = useMemo(() => {
    return baseColumns.map(col => {
      // Columndef<UserWithTokenLimits> にキャストして id を安全に参照
      const columnDef = col as ColumnDef<UserWithTokenLimits>;
      if (columnDef.id === 'actions') {
        return {
          ...columnDef,
          cell: ({ row }: { row: { original: UserWithTokenLimits } }) => (
            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="sm"
                className="text-sm bg-white hover:bg-gray-100 px-3 py-1 rounded transition-colors cursor-pointer border border-gray-300"
                onClick={() => handleOpenEditDialog(row.original)} // ここでハンドラを呼び出す
              >
                Edit Limits
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-sm bg-blue-50 hover:bg-blue-100 px-3 py-1 rounded transition-colors cursor-pointer border border-blue-300 text-blue-700"
                onClick={() => handleOpenUserManagementDialog(row.original)} // ユーザー管理ハンドラを呼び出す
              >
                Manage User
              </Button>
            </div>
          ),
        };
      }
      return col;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseColumns]); // baseColumns は通常変わらないので、依存配列は実質的に空と同じ効果

  if (loading && !user) { // 初回ローディング中
    return <div className="flex justify-center items-center h-screen">読み込み中...</div>;
  }

  // ユーザー情報が取得できていない、または管理ユーザーでない場合はアクセス拒否
  if (!user || !user.is_admin) {
    return (
      <div className="container mx-auto py-8 px-4">
        <Card>
          <CardHeader>
            <CardTitle>アクセス権限がありません</CardTitle>
          </CardHeader>
          <CardContent>
            <p>このページを表示する権限がありません。</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // エラーがあれば表示 (API呼び出しエラーなど)
  if (error) {
    return (
      <div className="container mx-auto py-8 px-4">
        <Card>
          <CardHeader>
            <CardTitle>エラー</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">ユーザー・トークン制限管理</h1>
        <Button
          variant="ghost"
          size="sm"
          className="text-sm bg-white hover:bg-gray-100 px-3 py-1 rounded transition-colors cursor-pointer border border-gray-300"
          onClick={() => router.push('/chat')}
        >
          チャットに戻る
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>ユーザー一覧</CardTitle>
          <p className="text-sm text-gray-600">
            ユーザーの状態管理とトークン制限を設定できます
          </p>
        </CardHeader>
        <CardContent>
          {loading && usersWithLimits.length === 0 ? ( // 再取得中の表示（任意）
            <p>データを読み込み中...</p>
          ) : usersWithLimits.length > 0 ? (
            <DataTable columns={tableColumns} data={usersWithLimits} /> // 修正したカラム定義を使用
          ) : (
            <p className="text-muted-foreground">
              表示できるユーザーデータがありません。
            </p>
          )}
        </CardContent>
      </Card>

      {/* トークン制限編集モーダルダイアログコンポーネント */}
      <EditTokenLimitsDialog
        user={selectedUserForEdit} // 編集対象のユーザーを渡す
        isOpen={isEditDialogOpen}      // 表示状態を渡す
        onOpenChange={setIsEditDialogOpen} // 表示状態の変更関数を渡す
        onLimitsUpdate={handleLimitsUpdate} // 更新後の再取得コールバックを渡す
      />

      {/* ユーザー管理モーダルダイアログコンポーネント */}
      <UserManagementDialog
        user={selectedUserForManagement} // 管理対象のユーザーを渡す
        isOpen={isUserManagementDialogOpen} // 表示状態を渡す
        onOpenChange={setIsUserManagementDialogOpen} // 表示状態の変更関数を渡す
        onUserUpdate={handleUserUpdate} // 更新後の再取得コールバックを渡す
        currentUserId={usersWithLimits.find(u => u.email === user?.email)?.id} // 現在のユーザーIDを渡す
      />
    </div>
  );
} 
