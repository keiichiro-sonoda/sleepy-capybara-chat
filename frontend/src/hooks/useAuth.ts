import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { fetchCurrentUser, getApiUrl } from '@/utils/api';

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

type RegisterParams = {
  email: string;
  password: string;
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

  // ユーザー登録処理
  const register = async ({ email, password }: RegisterParams) => {
    try {
      const response = await axios.post(`${getApiUrl()}/v1/auth/register`, {
        email,
        password,
      });

      if (response.data.error) {
        throw new Error(response.data.error);
      }

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        const message = error.response.data.detail || error.response.data.message;
        throw new Error(Array.isArray(message) ? message[0] : message);
      }
      throw new Error('ユーザー登録に失敗しました');
    }
  };

  return {
    ...authState,
    login,
    logout,
    register,
  };
}; 
