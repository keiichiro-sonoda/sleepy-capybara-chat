'use client';

import Link from 'next/link';
import Image from "next/image";
import { useAuth } from '@/hooks/useAuth';

export default function Home() {
  const { user, isLoading, logout } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20 font-[family-name:var(--font-geist-sans)]">
      <main className="flex flex-col gap-[32px] row-start-2 items-center sm:items-start">
        <div className="w-full max-w-4xl bg-white p-8 rounded-lg shadow-md">
          {user ? (
            <div className="space-y-6">
              <div className="bg-blue-50 p-6 rounded-lg">
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                  ようこそ、{user.email}さん！
                </h1>
                <p className="text-gray-600 mb-4">
                  AIチャットアプリでの会話を始めましょう
                </p>
                <Link
                  href="/chat"
                  className="inline-block bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors"
                >
                  チャットを始める
                </Link>
              </div>

              <div className="flex justify-end">
                <button
                  onClick={logout}
                  className="text-sm text-gray-600 hover:text-gray-800 underline"
                >
                  ログアウト
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center space-y-6">
              <h1 className="text-2xl font-bold text-gray-900">
                AIチャットアプリへようこそ
              </h1>
              <p className="text-gray-600">
                AIとの会話を始めるには、ログインしてください
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/auth/login"
                  className="inline-block bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors"
                >
                  ログイン
                </Link>
                <Link
                  href="/auth/register"
                  className="inline-block bg-white border border-blue-600 text-blue-600 px-6 py-3 rounded-md hover:bg-blue-50 transition-colors"
                >
                  新規登録
                </Link>
              </div>
            </div>
          )}
        </div>
      </main>
      <footer className="row-start-3 flex gap-[24px] flex-wrap items-center justify-center">
        <a
          className="flex items-center gap-2 hover:underline hover:underline-offset-4"
          href="https://nextjs.org/learn?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Image
            aria-hidden
            src="/file.svg"
            alt="File icon"
            width={16}
            height={16}
          />
          Learn
        </a>
        <a
          className="flex items-center gap-2 hover:underline hover:underline-offset-4"
          href="https://vercel.com/templates?framework=next.js&utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Image
            aria-hidden
            src="/window.svg"
            alt="Window icon"
            width={16}
            height={16}
          />
          Examples
        </a>
        <a
          className="flex items-center gap-2 hover:underline hover:underline-offset-4"
          href="https://nextjs.org?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Image
            aria-hidden
            src="/globe.svg"
            alt="Globe icon"
            width={16}
            height={16}
          />
          Go to nextjs.org →
        </a>
      </footer>
    </div>
  );
}
