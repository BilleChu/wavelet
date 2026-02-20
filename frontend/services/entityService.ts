import apiClient from './apiConfig'

export interface Entity {
  entity_id: string
  entity_type: string
  name: string
  aliases: string[]
  description: string | null
  code: string | null
  industry: string | null
  market: string | null
  market_cap: number | null
  properties: Record<string, unknown>
  source: string | null
  confidence: number
}

export interface EntityListResponse {
  entities: Entity[]
  total: number
  page: number
  page_size: number
}

export interface EntityType {
  type: string
  count: number
}

export interface Industry {
  industry: string
  count: number
}

export const entityService = {
  async searchEntities(params: {
    keyword?: string
    entity_type?: string
    industry?: string
    page?: number
    page_size?: number
  }): Promise<EntityListResponse> {
    const response = await apiClient.get<EntityListResponse>('/api/entities', { params })
    return response.data
  },

  async getEntity(entityId: string): Promise<Entity> {
    const response = await apiClient.get<Entity>(`/api/entities/${entityId}`)
    return response.data
  },

  async getEntityTypes(): Promise<{ types: EntityType[] }> {
    const response = await apiClient.get<{ types: EntityType[] }>('/api/entities/types/list')
    return response.data
  },

  async getIndustries(): Promise<{ industries: Industry[] }> {
    const response = await apiClient.get<{ industries: Industry[] }>('/api/entities/industries/list')
    return response.data
  },

  async createEntity(data: {
    entity_type: string
    name: string
    aliases?: string[]
    description?: string
    code?: string
    industry?: string
    market?: string
    market_cap?: number
    properties?: Record<string, unknown>
  }): Promise<Entity> {
    const response = await apiClient.post<Entity>('/api/entities', data)
    return response.data
  },
}
