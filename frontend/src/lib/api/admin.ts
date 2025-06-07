import { authGet, authPost, authPut, authDelete } from "@/utils/api";
import type { UserWithTokenLimits, TokenLimit } from "@/lib/types";

/**
 * 全ユーザーとそのトークン制限の概要を取得します。
 * 管理者権限が必要です。
 */
export const getUsersWithTokenLimitsSummary = async (): Promise<UserWithTokenLimits[]> => {
  return await authGet<UserWithTokenLimits[]>('/v1/admin/users/token-limits-summary');
};

/**
 * 新しいトークン制限を作成します。
 */
export const createTokenLimit = async (limitData: Omit<TokenLimit, 'id'>): Promise<TokenLimit> => {
  // model_nameはバックエンドに送信しない（表示用のみ）
  const { model_name, ...apiData } = limitData;
  return await authPost<TokenLimit>('/v1/admin/token-limits', apiData);
};

/**
 * 既存のトークン制限を更新します。
 * user_id は変更不可とする想定。
 */
export const updateTokenLimit = async (
  limitId: number,
  updateData: Partial<Omit<TokenLimit, 'id' | 'user_id'>>
): Promise<TokenLimit> => {
  // model_nameはバックエンドに送信しない（表示用のみ）
  const { model_name, ...apiData } = updateData;
  return await authPut<TokenLimit>(`/v1/admin/token-limits/${limitId}`, apiData);
};

/**
 * トークン制限を削除します。
 */
export const deleteTokenLimit = async (limitId: number): Promise<void> => {
  await authDelete(`/v1/admin/token-limits/${limitId}`);
};

/**
 * ユーザーの有効・無効状態を切り替えます。
 */
export const setUserActive = async (userId: number, isActive: boolean): Promise<{ message: string }> => {
  return await authPost<{ message: string }>(`/v1/auth/users/${userId}/active`, { is_active: isActive });
};

// 今後、トークン制限の作成、更新、削除などの管理者用API関数をここに追加していく
// export const createTokenLimitForUser = async (userId: number, limitData: any) => { ... }
// export const updateTokenLimit = async (limitId: number, updateData: any) => { ... }
// export const deleteTokenLimit = async (limitId: number) => { ... } 
