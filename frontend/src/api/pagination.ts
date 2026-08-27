import { apiRequest } from '@/api/client'
import type { PaginatedResponse } from '@/types/api'

export async function fetchAllPages<T>(path: string, pageSize = 200): Promise<T[]> {
  const first = await apiRequest<PaginatedResponse<T>>(`${path}?page=1&pageSize=${pageSize}`)
  if (!first.hasNext) {
    return first.items
  }

  const items = [...first.items]
  let page = 2
  while (page * pageSize < first.total + pageSize) {
    const next = await apiRequest<PaginatedResponse<T>>(`${path}?page=${page}&pageSize=${pageSize}`)
    items.push(...next.items)
    if (!next.hasNext) {
      break
    }
    page += 1
  }
  return items
}
