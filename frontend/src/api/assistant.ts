import { apiRequest } from '@/api/client'
import type {
  AssistantChatMessage,
  AssistantChatResponse,
  AssistantStatusResponse,
} from '@/types/api'

export const assistantApi = {
  status: (repositoryId: string) =>
    apiRequest<AssistantStatusResponse>(`/api/v1/repositories/${repositoryId}/assistant/status`),

  chat: (repositoryId: string, message: string, history: AssistantChatMessage[]) =>
    apiRequest<AssistantChatResponse>(`/api/v1/repositories/${repositoryId}/assistant/chat`, {
      method: 'POST',
      body: { message, history },
    }),
}
