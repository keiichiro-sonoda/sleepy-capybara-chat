'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { loginWithCredentials } from '@/utils/api';
import { useAuth } from '@/hooks/useAuth';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const { access_token } = await loginWithCredentials(email, password);

      // 認証状態を更新し、トークンを保存
      login(access_token);

      // チャットページにリダイレクト
      router.push('/chat');
    } catch (error: unknown) {
      console.error('Login error:', error);
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response: { data: { detail: unknown } } };
        // APIからのエラーメッセージを抽出
        const errorDetail = axiosError.response.data.detail;

        // 配列形式のエラーメッセージをわかりやすく表示
        if (Array.isArray(errorDetail)) {
          setError('入力内容に問題があります。もう一度確認してください。');
        } else if (typeof errorDetail === 'object' && errorDetail !== null) {
          setError('ログインに失敗しました。もう一度お試しください。');
        } else if (errorDetail === 'Email not verified') {
          setError('メールアドレスが確認されていません。メールの確認リンクをクリックしてください。');
        } else if (errorDetail === 'Incorrect email or password') {
          setError('メールアドレスまたはパスワードが正しくありません。');
        } else {
          setError(String(errorDetail) || 'ログインに失敗しました。');
        }
      } else {
        setError('ログイン中にエラーが発生しました。');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center text-gray-900">ログイン</h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded relative" role="alert">
            <p className="text-sm">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              メールアドレス
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

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              パスワード
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${isLoading ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'
              } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
          >
            {isLoading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                ログイン中...
              </>
            ) : (
              'ログイン'
            )}
          </button>
        </form>

        <div className="text-sm text-center">
          <Link href="/auth/register" className="text-blue-600 hover:text-blue-500">
            アカウントをお持ちでない方はこちら
          </Link>
        </div>

        <div className="text-sm text-center mt-2">
          <Link href="/auth/forgot-password" className="text-blue-600 hover:text-blue-500">
            パスワードをお忘れですか？
          </Link>
        </div>
      </div>
    </div>
  );
} 
