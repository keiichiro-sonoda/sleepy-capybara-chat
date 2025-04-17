import axios, { AxiosRequestConfig } from 'axios';
import { User } from '@/hooks/useAuth';

// APIのベースURL
export const getApiUrl = (): string => {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
};

// 認証付きのAPIクライアントを作成
export const createAuthClient = (token?: string | null) => {
  const apiClient = axios.create({
    baseURL: getApiUrl(),
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // トークンがある場合は、リクエストヘッダーに追加
  if (token) {
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  return apiClient;
};

// 認証が必要なGETリクエスト
export const authGet = async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  const token = localStorage.getItem('token');

  if (!token) {
    throw new Error('認証が必要です');
  }

  const client = createAuthClient(token);
  const response = await client.get<T>(url, config);
  return response.data;
};

// 認証が必要なPOSTリクエスト
export const authPost = async <T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
  const token = localStorage.getItem('token');

  if (!token) {
    throw new Error('認証が必要です');
  }

  const client = createAuthClient(token);
  const response = await client.post<T>(url, data, config);
  return response.data;
};

// 認証が必要なDELETEリクエスト
export const authDelete = async <T>(url: string, config?: AxiosRequestConfig): Promise<T | void> => {
  const token = localStorage.getItem('token');

  if (!token) {
    throw new Error('認証が必要です');
  }

  const client = createAuthClient(token);
  const response = await client.delete<T>(url, config);
  return response.data;
};

// フォームデータ形式でログインリクエストを送信
export const loginWithCredentials = async (email: string, password: string) => {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);

  const response = await axios.post(`${getApiUrl()}/v1/auth/login`, formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  return response.data;
};

// ユーザー情報を取得
export const fetchCurrentUser = async (): Promise<User> => {
  return await authGet<User>('/v1/auth/me');
};

// チャットセッション関連の型定義
export type ChatSession = {
  id: number;
  model_name: string;
  name: string | null;
  created_at: string;
  updated_at: string;
};

export type ChatResponse = {
  response: string;
  session_id: number;
};

export type ChatMessage = {
  id: number;
  session_id: number;
  role: string;
  content: string;
  created_at: string;
};

// 新しいチャットセッションを作成
export const createChatSession = async (modelName: string = 'llama3'): Promise<ChatSession> => {
  return await authPost<ChatSession>('/v1/chat/sessions', {
    model_name: modelName
  });
};

// 全てのチャットセッションを取得
export const getChatSessions = async (): Promise<ChatSession[]> => {
  return await authGet<ChatSession[]>('/v1/chat/sessions');
};

// セッションのメッセージ履歴を取得
export const getChatMessages = async (sessionId: number): Promise<ChatMessage[]> => {
  return await authGet<ChatMessage[]>(`/v1/chat/sessions/${sessionId}/messages`);
};

// メッセージを送信して応答を取得（非ストリーム）
export const sendChatMessage = async (sessionId: number, content: string): Promise<ChatResponse> => {
  return await authPost<ChatResponse>(`/v1/chat/sessions/${sessionId}/messages`, {
    content,
    role: "user",
    stream: false
  });
};

// メッセージを送信して応答をストリーミングで取得
export const sendChatMessageStreaming = async (
  sessionId: number,
  content: string,
  onChunk: (chunk: string) => void,
  onComplete: (fullResponse: string) => void,
  onError: (error: string) => void
): Promise<void> => {
  const token = localStorage.getItem('token');
  if (!token) {
    throw new Error('認証が必要です');
  }

  try {
    const apiUrl = `${getApiUrl()}/v1/chat/sessions/${sessionId}/messages`;
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        content,
        role: "user",
        stream: true
      })
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    // EventSourceの代わりにfetchのストリーミングを使用
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is null');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    // ストリームの読み取り
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // 新しいテキストをバッファに追加
      buffer += decoder.decode(value, { stream: true });

      // バッファを行に分割して処理
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || ''; // 最後の不完全な行をバッファに戻す

      for (const line of lines) {
        if (!line.trim() || !line.startsWith('data: ')) continue;

        try {
          const eventData = JSON.parse(line.substring(6)); // 'data: ' を取り除く

          if (eventData.event === 'chunk' && eventData.content) {
            onChunk(eventData.content);
          } else if (eventData.event === 'done') {
            onComplete(eventData.content);
            return;
          } else if (eventData.event === 'error') {
            onError(eventData.message || 'Unknown error');
            return;
          }
        } catch (e) {
          console.error('Error parsing event data:', e, line);
        }
      }
    }
  } catch (error) {
    console.error('Error in streaming request:', error);
    onError(error instanceof Error ? error.message : String(error));
  }
};

// チャットセッションを削除
export const deleteChatSession = async (sessionId: number): Promise<void> => {
  await authDelete(`/v1/chat/sessions/${sessionId}`);
};
