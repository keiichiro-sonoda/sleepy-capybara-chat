// import { MetricType as BackendMetricType, PeriodUnit as BackendPeriodUnit } from '@/utils/api'; // この行は削除

// MetricType と PeriodUnit をバックエンドに合わせて定義
export enum MetricType {
  TOKENS = "tokens",
}

export enum PeriodUnit {
  MINUTE = "minute",
  HOUR = "hour",
  DAY = "day",
  MONTH = "month",
}

export interface TokenLimit {
  id: number;
  model_id: string;  // バックエンドAPIに合わせてmodel_idを使用
  user_id: number;
  metric_type: MetricType;
  limit_value: number;
  period_unit: PeriodUnit;
  period_value: number;
  model_name: string; // バックエンドから提供される表示用モデル名
}

export interface User {
  id: number;
  email: string;
  is_verified: boolean;
  is_admin: boolean;
  is_active: boolean;
}

export interface UserWithTokenLimits extends User {
  token_limits: TokenLimit[];
} 
