import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetchCurrentUser } from '@/utils/api';

export type User = {
  email: string;
  is_verified: boolean;
};

export type AuthState = {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
};

// 認証状態を管理するフック
export const useAuth = () => {
  const router = useRouter();
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
    error: null,
  });

  useEffect(() => {
    // ユーザー情報の取得
    const loadUser = async () => {
      const token = localStorage.getItem('token');

      if (!token) {
        setAuthState({
          user: null,
          isLoading: false,
          isAuthenticated: false,
          error: null,
        });
        return;
      }

      try {
        const userData = await fetchCurrentUser() as User;
        setAuthState({
          user: userData,
          isLoading: false,
          isAuthenticated: true,
          error: null,
        });
      } catch (error) {
        console.error('Failed to fetch user data:', error);
        localStorage.removeItem('token');
        setAuthState({
          user: null,
          isLoading: false,
          isAuthenticated: false,
          error: 'セッションが無効です。再度ログインしてください。',
        });
      }
    };

    loadUser();
  }, []);

  // ログイン処理
  const login = (token: string) => {
    localStorage.setItem('token', token);
    setAuthState((prev) => ({
      ...prev,
      isAuthenticated: true,
    }));
  };

  // ログアウト処理
  const logout = () => {
    localStorage.removeItem('token');
    setAuthState({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      error: null,
    });
    router.push('/auth/login');
  };

  return {
    ...authState,
    login,
    logout,
  };
}; 
