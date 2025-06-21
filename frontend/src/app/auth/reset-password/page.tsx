"use client";

import { FormEvent, useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { confirmPasswordReset, verifyPasswordResetToken } from '@/utils/api';
import Link from 'next/link';

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token') || '';
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTokenValid, setIsTokenValid] = useState<boolean | null>(null);
  const [userEmail, setUserEmail] = useState('');

  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setIsTokenValid(false);
        setError('トークンが見つかりません。メールのリンクを再確認してください。');
        return;
      }

      try {
        const result = await verifyPasswordResetToken(token);
        setIsTokenValid(true);
        setUserEmail(result.email);
      } catch (err: unknown) {
        setIsTokenValid(false);
        if (err && typeof err === 'object' && 'response' in err) {
          const axiosError = err as { response: { status?: number } };
          if (axiosError.response?.status === 400) {
            setError('このリンクは無効または期限切れです。新しいパスワードリセット要求を行ってください。');
          } else {
            setError('トークンの検証に失敗しました。');
          }
        } else {
          setError('トークンの検証に失敗しました。');
        }
      }
    };

    validateToken();
  }, [token]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (newPassword !== confirmPassword) {
      setError('パスワードが一致しません。');
      return;
    }

    setIsLoading(true);
    try {
      const res = await confirmPasswordReset(token, newPassword);
      setMessage(res.message);
      setTimeout(() => router.push('/auth/login'), 2000);
    } catch (err: unknown) {
      console.error(err);
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response: { status?: number } };
        if (axiosError.response?.status === 400) {
          setError('このリンクは無効または期限切れです。新しいパスワードリセット要求を行ってください。');
        } else {
          setError('パスワードリセットに失敗しました。');
        }
      } else {
        setError('パスワードリセットに失敗しました。');
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (isTokenValid === null) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100">
        <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md">
          <h1 className="text-2xl font-bold text-center text-gray-900">リンクを確認中...</h1>
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    );
  }

  if (isTokenValid === false) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100">
        <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md">
          <h1 className="text-2xl font-bold text-center text-gray-900">リンクが無効です</h1>

          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded" role="alert">
            <p className="text-sm">{error}</p>
          </div>

          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              以下の理由が考えられます：
            </p>
            <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1">
              <li>リンクの有効期限（1時間）が切れている</li>
              <li>新しいパスワードリセット要求により、このリンクが無効化された</li>
              <li>既にこのリンクを使用してパスワードを変更済み</li>
            </ul>
          </div>

          <div className="text-sm text-center space-y-2">
            <p>
              <Link href="/auth/forgot-password" className="text-blue-600 hover:text-blue-500">
                新しいパスワードリセット要求を行う
              </Link>
            </p>
            <p>
              <Link href="/auth/login" className="text-blue-600 hover:text-blue-500">
                ログインページに戻る
              </Link>
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md">
        <div>
          <h1 className="text-2xl font-bold text-center text-gray-900">新しいパスワード設定</h1>
          {userEmail && (
            <p className="text-sm text-center text-gray-600 mt-2">
              アカウント: {userEmail}
            </p>
          )}
        </div>

        {message && (
          <div className="bg-green-50 border border-green-200 text-green-600 px-4 py-3 rounded" role="alert">
            <p className="text-sm">{message}</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded" role="alert">
            <p className="text-sm">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              新しいパスワード
            </label>
            <input
              type="password"
              id="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
              パスワード確認
            </label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${isLoading ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
          >
            {isLoading ? '送信中...' : 'パスワードをリセット'}
          </button>
        </form>

        <div className="text-sm text-center">
          <Link href="/auth/login" className="text-blue-600 hover:text-blue-500">
            ログイン画面に戻る
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center">読み込み中...</div>}>
      <ResetPasswordContent />
    </Suspense>
  );
} 
