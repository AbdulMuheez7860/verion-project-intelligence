import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { AnalyticsTrendPoint } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/states/empty-state'
import { formatRelativeTime } from '@/lib/format-datetime'

interface AnalyticsTrendChartProps {
  title: string
  data: AnalyticsTrendPoint[]
  valueKey?: 'value' | 'total'
  yDomain?: [number, number]
  summary?: string
  emptyMessage?: string
}

export function AnalyticsTrendChart({
  title,
  data,
  valueKey = 'value',
  yDomain = [0, 100],
  summary,
  emptyMessage = 'Trend data appears after multiple completed analyses.',
}: AnalyticsTrendChartProps) {
  const chartData = data
    .filter((point) => point[valueKey] != null)
    .map((point) => ({
      label: new Date(point.capturedAt).toLocaleDateString(),
      value: Number(point[valueKey]),
      capturedAt: point.capturedAt,
      repositoryName: point.repositoryName,
    }))

  return (
    <Card className="min-w-0">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {summary ? <p className="sr-only">{summary}</p> : null}
        {summary ? <p className="text-xs text-muted-foreground" aria-hidden="true">{summary}</p> : null}
      </CardHeader>
      <CardContent className="h-56 sm:h-64">
        {chartData.length === 0 ? (
          <EmptyState title="No trend data" description={emptyMessage} className="min-h-40" />
        ) : chartData.length === 1 ? (
          <div className="flex h-full flex-col justify-center gap-2 px-2">
            <p className="text-sm text-muted-foreground">
              Single snapshot recorded ({formatRelativeTime(chartData[0].capturedAt)}). Run another analysis to
              measure change.
            </p>
            <p className="font-mono text-2xl font-semibold tabular-nums">{Math.round(chartData[0].value)}</p>
          </div>
        ) : (
          <div className="h-full w-full" role="img" aria-label={summary || title}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis domain={yDomain} tick={{ fontSize: 11 }} width={32} />
                <Tooltip
                  formatter={(value: number) => [value, title]}
                  labelFormatter={(_, payload) => {
                    const item = payload?.[0]?.payload as { capturedAt?: string; repositoryName?: string } | undefined
                    if (!item?.capturedAt) return ''
                    const repo = item.repositoryName ? ` · ${item.repositoryName}` : ''
                    return `${new Date(item.capturedAt).toLocaleString()}${repo}`
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#2563eb"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
