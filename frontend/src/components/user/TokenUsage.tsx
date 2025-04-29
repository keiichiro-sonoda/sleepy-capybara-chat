'use client'

import { useState, useEffect } from 'react'
import { fetchTokenUsageByModel, TokenUsageByModel } from '@/utils/api'

type TimeRange = '7' | '30' | '90'

export default function TokenUsage() {
  const [tokenUsage, setTokenUsage] = useState<TokenUsageByModel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState<TimeRange>('30')

  useEffect(() => {
    const loadTokenUsage = async () => {
      try {
        setLoading(true)
        const days = parseInt(timeRange)
        const data = await fetchTokenUsageByModel(days)
        setTokenUsage(data)
        setError(null)
      } catch (err) {
        console.error('トークン使用量の取得に失敗しました', err)
        setError('トークン使用量の取得に失敗しました')
      } finally {
        setLoading(false)
      }
    }

    loadTokenUsage()
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

  return (
    <div className="w-full border rounded-lg shadow-sm p-6">
      <div className="mb-4 pb-4 border-b flex items-center justify-between">
        <h2 className="text-xl font-semibold">トークン使用量</h2>
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
      <div>
        {loading ? (
          <div className="flex justify-center items-center h-40">
            <div className="text-gray-500">読み込み中...</div>
          </div>
        ) : error ? (
          <div className="text-red-500 text-center">{error}</div>
        ) : tokenUsage.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            この期間のトークン使用記録はありません
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-100 p-4 rounded-lg">
                <div className="text-gray-500 text-sm">総トークン数</div>
                <div className="text-2xl font-bold mt-1">{formatNumber(totalUsage.total_tokens)}</div>
              </div>
              <div className="bg-gray-100 p-4 rounded-lg">
                <div className="text-gray-500 text-sm">プロンプトトークン</div>
                <div className="text-2xl font-bold mt-1">{formatNumber(totalUsage.total_prompt_tokens)}</div>
              </div>
              <div className="bg-gray-100 p-4 rounded-lg">
                <div className="text-gray-500 text-sm">レスポンストークン</div>
                <div className="text-2xl font-bold mt-1">{formatNumber(totalUsage.total_completion_tokens)}</div>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-medium">モデル別使用量</h3>
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
      </div>
    </div>
  )
} 
