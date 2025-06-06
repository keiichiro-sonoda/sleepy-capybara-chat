import axios, { AxiosRequestConfig } from 'axios';
import { User } from '@/hooks/useAuth';
import { AIModel } from './constants';

// APIのベースURL
export const getApiUrl = (): string => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
  // console.log('DEBUG: getApiUrl() returning:', apiUrl);
  // console.log('DEBUG: process.env.NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL);
  return apiUrl;
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

// 認証が必要なPUTリクエスト
export const authPut = async <T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
  const token = localStorage.getItem('token');

  if (!token) {
    throw new Error('認証が必要です');
  }

  const client = createAuthClient(token);
  const response = await client.put<T>(url, data, config);
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

// トークン使用量の型定義
export type TokenUsageStats = {
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
};

export type TokenUsageByModel = {
  model_name: string;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
};

// モデルごとのトークン使用量を取得
export const fetchTokenUsageByModel = async (days: number = 30): Promise<TokenUsageByModel[]> => {
  return await authGet<TokenUsageByModel[]>(`/v1/users/me/token-usage/by-model?days=${days}`);
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
  thinking_content?: string | null;
};

export type ChatMessage = {
  id: number;
  session_id: number;
  role: string;
  content: string;
  created_at: string;
  model_name?: string;
  thinking_content?: string | null;
};

// 利用可能なAIモデル一覧を取得
export const getAvailableModels = async (): Promise<AIModel[]> => {
  const baseUrl = getApiUrl();
  const fullUrl = `${baseUrl}/v1/models/`;
  // console.log(`DEBUG: getAvailableModels - baseUrl: ${baseUrl}`);
  // console.log(`DEBUG: getAvailableModels - fullUrl: ${fullUrl}`);
  const response = await axios.get<AIModel[]>(fullUrl);
  return response.data;
};

// デフォルトモデルを取得
export const getDefaultModel = async (): Promise<string> => {
  const response = await axios.get<string>(`${getApiUrl()}/v1/models/default`);
  return response.data;
};

// APIからモデル情報を取得する前の一時的なデフォルトモデルID
// これはAPIリクエスト中のフォールバックとしてのみ使用
const TEMP_DEFAULT_MODEL_ID = "qwen3";

// 新しいチャットセッションを作成
export const createChatSession = async (modelId?: string): Promise<ChatSession> => {
  const modelToUse = modelId || TEMP_DEFAULT_MODEL_ID;
  return await authPost<ChatSession>('/v1/chat/sessions', {
    model_id: modelToUse
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
export const sendChatMessage = async (
  sessionId: number,
  content: string,
  modelId?: string,
  thinking_mode?: boolean
): Promise<ChatResponse> => {
  return await authPost<ChatResponse>(`/v1/chat/sessions/${sessionId}/messages`, {
    content,
    role: "user",
    stream: false,
    model_id: modelId,
    thinking_mode: thinking_mode ?? false
  });
};

// メッセージを送信して応答をストリーミングで取得
export const sendChatMessageStreaming = async (
  sessionId: number,
  content: string,
  onChunk: (chunk: string, type: 'thinking' | 'answer') => void,
  onComplete: (fullResponse: string, modelId?: string, thinkingContent?: string | null) => void,
  onError: (error: string) => void,
  modelId?: string,
  thinking_mode?: boolean
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
        stream: true,
        model_id: modelId,
        thinking_mode: thinking_mode ?? false
      })
    });

    if (!response.ok) {
      let errorBody = `API error: ${response.status}`;
      try {
        const errorJson = await response.json();
        if (errorJson && errorJson.detail) {
          errorBody += ` - ${errorJson.detail}`;
        }
      } catch (e) {
        // JSONパース失敗時は何もしない
      }
      throw new Error(errorBody);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is null');
    }

    const decoder = new TextDecoder();
    let buffer = '';
    let completedResponse = "";
    let completedThinkingContent: string | null = null;
    let responseModelId: string | undefined = undefined;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim() || !line.startsWith('data: ')) continue;

        try {
          const eventData = JSON.parse(line.substring(6));

          if (eventData.event === 'chunk' && eventData.content) {
            const chunkType = eventData.type === 'thinking' ? 'thinking' : 'answer';
            onChunk(eventData.content, chunkType);
          } else if (eventData.event === 'done') {
            completedResponse = eventData.content ?? "";
            completedThinkingContent = eventData.thinking_content ?? null;
            responseModelId = eventData.model_name ?? modelId;
            onComplete(completedResponse, responseModelId, completedThinkingContent);
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
