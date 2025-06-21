'use client'

import { useState, useEffect } from 'react'
import { fetchTokenUsageByModel, TokenUsageByModel, fetchMyTokenLimitsSummary, TokenLimitSummary } from '@/utils/api'

// Shadcn UI components
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Clock, Info } from "lucide-react";

type TimeRange = '7' | '30' | '90'

// シンプルなプログレスバーコンポーネント
const Progress = ({ value, className }: { value: number; className?: string }) => (
  <div className={`w-full bg-gray-200 rounded-full h-2 ${className || ''}`}>
    <div
      className="h-2 rounded-full transition-all duration-300 ease-in-out"
      style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
    />
  </div>
)

// シンプルなアラートコンポーネント
const Alert = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={`p-3 rounded-md border ${className || 'border-gray-200 bg-gray-50'}`}>
    {children}
  </div>
)

const AlertDescription = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={`text-sm ${className || ''}`}>
    {children}
  </div>
)

// CSS-onlyツールチップコンポーネント
const InfoTooltip = ({ content }: { content: string }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        className="cursor-help focus:outline-none"
        aria-label="詳細情報"
      >
        <Info className="h-4 w-4 text-gray-400 hover:text-gray-600 ml-1" />
      </button>

      {/* デスクトップ用: 中央配置 */}
      <div className={`hidden sm:block absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-4 py-3 bg-gray-900 text-white text-sm rounded-lg transition-all duration-200 z-50 w-80 max-w-md ${isOpen ? 'opacity-100 visible' : 'opacity-0 invisible'}`}>
        <div className="text-left leading-relaxed">{content}</div>
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
      </div>

      {/* モバイル用: 画面中央に固定表示 */}
      {isOpen && (
        <div className="sm:hidden fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 pointer-events-auto w-[90vw] max-w-sm">
          <div className="bg-gray-900/95 text-white text-sm rounded-lg px-4 py-3 shadow-lg max-h-[80vh] overflow-y-auto">
            <div className="text-left leading-relaxed">{content}</div>
            <button
              onClick={() => setIsOpen(false)}
              className="mt-3 w-full bg-gray-700 hover:bg-gray-600 text-white text-xs py-2 px-3 rounded transition-colors"
            >
              閉じる
            </button>
          </div>
        </div>
      )}

      {/* モバイル用オーバーレイ（タップして閉じる） */}
      {isOpen && (
        <div
          className="sm:hidden fixed inset-0 z-40 bg-black bg-opacity-20"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};

export default function TokenUsage() {
  const [tokenUsage, setTokenUsage] = useState<TokenUsageByModel[]>([])
  const [tokenLimits, setTokenLimits] = useState<TokenLimitSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState<TimeRange>('30')

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        const days = parseInt(timeRange)

        // 使用量と制限情報を並行取得
        const [usageData, limitsData] = await Promise.all([
          fetchTokenUsageByModel(days),
          fetchMyTokenLimitsSummary()
        ])

        setTokenUsage(usageData)
        setTokenLimits(limitsData.limits)
        setError(null)
      } catch (err) {
        console.error('データの取得に失敗しました', err)
        setError('データの取得に失敗しました')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [timeRange])

  // 合計トークン数を計算
  const totalUsage = tokenUsage.reduce(
    (acc, model) => {
      return {
        total_prompt_tokens: acc.total_prompt_tokens + model.total_prompt_tokens,
        total_completion_tokens: acc.total_completion_tokens + model.total_completion_tokens,
        total_tokens: acc.total_tokens + model.total_tokens,
      }
    },
    { total_prompt_tokens: 0, total_completion_tokens: 0, total_tokens: 0 }
  )

  // トークン数にカンマを入れて表示
  const formatNumber = (num: number) => num.toLocaleString()

  // 制限に基づいて優先度を決定（使用率の高い順、または期間の短い順）
  const getImportantLimits = (limits: TokenLimitSummary[]): TokenLimitSummary[] => {
    return limits
      .filter(limit => limit.usage_percentage > 0 || limit.current_usage > 0) // 使用量があるもののみ
      .sort((a, b) => {
        // 使用率90%以上を最優先
        if (a.usage_percentage >= 90 && b.usage_percentage < 90) return -1
        if (b.usage_percentage >= 90 && a.usage_percentage < 90) return 1

        // 使用率順（高い順）
        if (a.usage_percentage !== b.usage_percentage) {
          return b.usage_percentage - a.usage_percentage
        }

        // 使用率が同じ場合は期間の短い順（より制限的なもの）
        const periodOrder = { 'hour': 1, 'day': 2, 'week': 3, 'month': 4 }
        const aPeriod = periodOrder[a.period_unit as keyof typeof periodOrder] || 5
        const bPeriod = periodOrder[b.period_unit as keyof typeof periodOrder] || 5
        return aPeriod - bPeriod
      })
      .slice(0, 5) // 最大5個まで表示
  }

  const importantLimits = getImportantLimits(tokenLimits)

  // 警告レベルを決定
  const getWarningLevel = (percentage: number) => {
    if (percentage >= 95) return 'critical'
    if (percentage >= 80) return 'warning'
    if (percentage >= 60) return 'caution'
    return 'normal'
  }

  // プログレスバーの色クラスを取得
  const getProgressColorClass = (warningLevel: string) => {
    switch (warningLevel) {
      case 'critical': return 'bg-red-500'
      case 'warning': return 'bg-orange-500'
      case 'caution': return 'bg-yellow-500'
      default: return 'bg-green-500'
    }
  }

  return (
    <div className="space-y-6">
      {/* トークン制限の状態 */}
      {importantLimits.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              トークン制限の状況
              <InfoTooltip content="制限計算では、レスポンストークンがプロンプトトークンよりも重み付けされて計算される場合があります。モデルによって異なる比率で実質トークン数が算出されます。" />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {importantLimits.map((limit) => {
              const warningLevel = getWarningLevel(limit.usage_percentage)

              return (
                <div key={`${limit.model_id}-${limit.period_description}`} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{limit.model_name}</span>
                      <Badge variant={limit.is_custom_limit ? "default" : "secondary"}>
                        {limit.is_custom_limit ? "カスタム制限" : "デフォルト制限"}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {limit.period_description}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="flex items-center">
                        {formatNumber(limit.current_usage)} / {formatNumber(limit.limit_value)} トークン
                        <InfoTooltip content="この数値は制限計算用の実質トークン数です。レスポンストークンの重み付けが含まれている場合があります。" />
                      </span>
                      <span className={`font-medium ${warningLevel === 'critical' ? 'text-red-600' :
                        warningLevel === 'warning' ? 'text-orange-600' :
                          warningLevel === 'caution' ? 'text-yellow-600' :
                            'text-green-600'
                        }`}>
                        {limit.usage_percentage}%
                      </span>
                    </div>
                    <Progress
                      value={Math.min(limit.usage_percentage, 100)}
                      className={`[&>div]:${getProgressColorClass(warningLevel)}`}
                    />
                    {limit.remaining > 0 ? (
                      <div className="text-xs text-muted-foreground">
                        残り {formatNumber(limit.remaining)} トークン使用可能
                      </div>
                    ) : (
                      <div className="text-xs text-red-600 font-medium">
                        制限に達しました
                      </div>
                    )}
                  </div>

                  {warningLevel === 'critical' && (
                    <Alert className="border-red-200 bg-red-50 flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                      <AlertDescription className="text-red-800">
                        制限にほぼ達しています。使用量にご注意ください。
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              )
            })}
          </CardContent>
        </Card>
      )}

      {/* 既存のトークン使用量表示 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center">
              トークン使用量
              <InfoTooltip content="ここに表示される数値は実際に送受信されたトークンの生の数値です。制限計算で使用される実質トークン数とは異なる場合があります。" />
            </CardTitle>
            <div className="flex space-x-2 border rounded-md overflow-hidden">
              <button
                className={`px-3 py-1 text-sm ${timeRange === '7' ? 'bg-blue-500 text-white' : 'bg-gray-100'}`}
                onClick={() => setTimeRange('7')}
              >
                7日間
              </button>
              <button
                className={`px-3 py-1 text-sm ${timeRange === '30' ? 'bg-blue-500 text-white' : 'bg-gray-100'}`}
                onClick={() => setTimeRange('30')}
              >
                30日間
              </button>
              <button
                className={`px-3 py-1 text-sm ${timeRange === '90' ? 'bg-blue-500 text-white' : 'bg-gray-100'}`}
                onClick={() => setTimeRange('90')}
              >
                90日間
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center items-center h-40">
              <div className="text-gray-500">読み込み中...</div>
            </div>
          ) : error ? (
            <Alert className="border-red-200 bg-red-50 flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
              <AlertDescription className="text-red-800">{error}</AlertDescription>
            </Alert>
          ) : tokenUsage.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              この期間のトークン使用記録はありません
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-100 p-4 rounded-lg">
                  <div className="text-gray-500 text-sm flex items-center">
                    総トークン数
                    <InfoTooltip content="プロンプトトークンとレスポンストークンの合計です。制限計算で使用される実質トークン数とは異なる場合があります。" />
                  </div>
                  <div className="text-2xl font-bold mt-1">{formatNumber(totalUsage.total_tokens)}</div>
                </div>
                <div className="bg-gray-100 p-4 rounded-lg">
                  <div className="text-gray-500 text-sm flex items-center">
                    プロンプトトークン
                    <InfoTooltip content="あなたが送信したメッセージで使用されたトークン数です。" />
                  </div>
                  <div className="text-2xl font-bold mt-1">{formatNumber(totalUsage.total_prompt_tokens)}</div>
                </div>
                <div className="bg-gray-100 p-4 rounded-lg">
                  <div className="text-gray-500 text-sm flex items-center">
                    レスポンストークン
                    <InfoTooltip content="AIが生成した返答で使用されたトークン数です。制限計算では、このトークンがより重く計算される場合があります。" />
                  </div>
                  <div className="text-2xl font-bold mt-1">{formatNumber(totalUsage.total_completion_tokens)}</div>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-medium flex items-center">
                  モデル別使用量
                  <InfoTooltip content="各AIモデルでの実際のトークン使用量です。制限計算では、モデルごとに異なる重み付け比率が適用される場合があります。" />
                </h3>
                <div className="space-y-3">
                  {tokenUsage.map((model) => (
                    <div key={model.model_name} className="border rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <div className="font-medium flex items-center">
                          <span>{model.model_name}</span>
                          <span className="ml-2 text-xs bg-gray-200 text-gray-800 px-2 py-0.5 rounded-full">
                            {Math.round((model.total_tokens / totalUsage.total_tokens) * 100)}%
                          </span>
                        </div>
                        <div className="text-xl font-semibold">{formatNumber(model.total_tokens)}</div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm text-gray-500">
                        <div>プロンプト: {formatNumber(model.total_prompt_tokens)}</div>
                        <div>レスポンス: {formatNumber(model.total_completion_tokens)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
} 
