"use client";

import { FormEvent, useState } from 'react';
import { requestPasswordReset } from '@/utils/api';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setMessage('');

    try {
      const res = await requestPasswordReset(email);
      const sentAt = Date.now();
      router.push(`/auth/password-reset-sent?email=${encodeURIComponent(email)}&sentAt=${sentAt}`);
    } catch (err: any) {
      console.error(err);
      let errorMessage = 'パスワードリセット要求に失敗しました。';

      if (err.response?.status === 429) {
        errorMessage = 'しばらく時間をおいてから再度お試しください。';
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      }

      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center text-gray-900">パスワードリセット</h1>

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
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              登録済みメールアドレス
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${isLoading ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
          >
            {isLoading ? '送信中...' : 'リセットリンクを送信'}
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
