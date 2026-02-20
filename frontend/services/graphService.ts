/**
 * Graph Service for Knowledge Graph API.
 */

import { apiClient } from './apiConfig'

export interface GraphNode {
  id: string
  name: string
  type: string
  properties: Record<string, unknown>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: string
  weight: number
  properties: Record<string, unknown>
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  total_nodes: number
  total_edges: number
}

export interface Entity {
  id: string
  name: string
  type: string
  code?: string
  industry?: string
  description?: string
  aliases: string[]
  properties: Record<string, unknown>
  confidence: number
  source?: string
  created_at?: string
  updated_at?: string
  relations?: {
    outgoing: Relation[]
    incoming: Relation[]
    total: number
  }
}

export interface Relation {
  id: string
  type: string
  weight: number
  confidence: number
  evidence?: string
  source?: { id: string; name: string; type: string }
  target?: { id: string; name: string; type: string }
}

export interface EntityType {
  type: string
  display_name: string
  count?: number
}

export interface RelationType {
  type: string
  display_name: string
}

export interface Industry {
  name: string
  count?: number
}

export interface EntityNews {
  id: string
  title: string
  summary: string
  source: string
  published_at: string
  sentiment: string
}

export interface EntitySource {
  type: string
  name?: string
  confidence?: number
  reason?: string
  version?: number
  timestamp?: string
}

export interface DataQualityReport {
  total_entities: number
  total_relations: number
  entity_type_distribution: Record<string, number>
  relation_type_distribution: Record<string, number>
  isolated_entities: number
  entities_without_industry: number
  entities_without_code: number
  stock_entities_without_basic: number
  dangling_relations: number
  consistency_score: number
  issues: Array<{
    type: string
    severity: 'info' | 'warning' | 'error'
    message: string
    count: number
  }>
}

export const graphService = {
  async getDefaultGraph(limit: number = 50): Promise<GraphData> {
    const response = await apiClient.get('/api/graph/default', { params: { limit } })
    return response.data
  },

  async getEntityGraph(entityId: string, depth: number = 1): Promise<GraphData> {
    const response = await apiClient.get(`/api/graph/entity/${entityId}`, {
      params: { depth },
    })
    return response.data
  },

  async searchGraph(keyword: string, limit: number = 20): Promise<GraphData> {
    const response = await apiClient.get('/api/graph/search', {
      params: { keyword, limit },
    })
    return response.data
  },

  async findPath(startId: string, endId: string, maxDepth: number = 3): Promise<{
    found: boolean
    path: Array<{ id: string; name: string; type: string }>
    length: number
    message?: string
  }> {
    const response = await apiClient.get('/api/graph/path', {
      params: { start_id: startId, end_id: endId, max_depth: maxDepth },
    })
    return response.data
  },

  async getStats(): Promise<{
    total_entities: number
    total_relations: number
    entity_types: Record<string, number>
    relation_types: Record<string, number>
  }> {
    const response = await apiClient.get('/api/stats')
    return response.data
  },

  async getQuality(): Promise<DataQualityReport> {
    const response = await apiClient.get('/api/quality')
    return response.data
  },
}

export const entityService = {
  async listEntities(params: {
    entity_type?: string
    keyword?: string
    industry?: string
    limit?: number
    offset?: number
  }): Promise<{
    entities: Entity[]
    total: number
    page: number
    page_size: number
    has_more: boolean
  }> {
    const response = await apiClient.get('/api/entities', { params })
    return response.data
  },

  async getEntity(entityId: string): Promise<Entity> {
    const response = await apiClient.get(`/api/entities/${entityId}`)
    return response.data
  },

  async createEntity(data: {
    entity_type: string
    name: string
    code?: string
    aliases?: string[]
    description?: string
    industry?: string
    properties?: Record<string, unknown>
    confidence?: number
  }): Promise<{ id: string; name: string; type: string; created: boolean }> {
    const response = await apiClient.post('/api/entities', data)
    return response.data
  },

  async updateEntity(entityId: string, data: {
    name?: string
    aliases?: string[]
    description?: string
    industry?: string
    properties?: Record<string, unknown>
    reason?: string
  }): Promise<{ id: string; name: string; updated: boolean }> {
    const response = await apiClient.put(`/api/entities/${entityId}`, data)
    return response.data
  },

  async deleteEntity(entityId: string): Promise<{ id: string; deleted: boolean }> {
    const response = await apiClient.delete(`/api/entities/${entityId}`)
    return response.data
  },

  async createRelation(data: {
    source_entity_id: string
    target_entity_id: string
    relation_type: string
    weight?: number
    confidence?: number
    evidence?: string
    properties?: Record<string, unknown>
  }): Promise<{ id: string; type: string; created: boolean }> {
    const response = await apiClient.post('/api/relations', data)
    return response.data
  },

  async getEntityTypes(): Promise<{ types: EntityType[] }> {
    const response = await apiClient.get('/api/entities/types/list')
    return response.data
  },

  async getRelationTypes(): Promise<{ types: RelationType[] }> {
    const response = await apiClient.get('/api/relation-types/list')
    return response.data
  },

  async getIndustries(): Promise<{ industries: Industry[] }> {
    const response = await apiClient.get('/api/entities/industries/list')
    return response.data
  },

  async getEntityNews(entityId: string, limit: number = 10): Promise<{
    entity_id: string
    entity_name: string
    news: EntityNews[]
    total: number
  }> {
    const response = await apiClient.get(`/api/entity/${entityId}/news`, {
      params: { limit },
    })
    return response.data
  },

  async getEntitySources(entityId: string): Promise<{
    entity_id: string
    entity_name: string
    sources: EntitySource[]
  }> {
    const response = await apiClient.get(`/api/entity/${entityId}/sources`)
    return response.data
  },
}

export default graphService
