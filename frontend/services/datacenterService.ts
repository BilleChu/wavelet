import apiClient from './apiConfig'

export interface TaskDefinition {
  task_id: string
  name: string
  task_type: string
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused'
  priority: 'CRITICAL' | 'HIGH' | 'NORMAL' | 'LOW' | 'BACKGROUND'
  progress: number
  progress_message: string
  data_source: string | null
  data_type: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  error: string | null
  include_in_global_start: boolean
}

export interface TriggerDefinition {
  trigger_id: string
  name: string
  trigger_type: 'interval' | 'cron' | 'once' | 'condition' | 'manual'
  status: 'enabled' | 'disabled' | 'triggered' | 'error'
  last_triggered: string | null
  next_trigger: string | null
  trigger_count: number
  error_count: number
}

export interface DataSourceInfo {
  source_id: string
  name: string
  category: string
  is_available: boolean
  description: string
}

export interface QueueStats {
  total_tasks: number
  queued: number
  running: number
  completed: number
  failed: number
  paused: number
  cancelled: number
  max_concurrent: number
  is_running: boolean
}

export interface OverviewData {
  is_running: boolean
  queue: QueueStats
  triggers: {
    total_triggers: number
    enabled: number
    disabled: number
  }
  success_rate: number
  recent_tasks: TaskDefinition[]
}

export interface CreateTaskRequest {
  name: string
  task_type: string
  data_source?: string
  data_type?: string
  params: Record<string, unknown>
  priority?: string
  include_in_global_start?: boolean
  max_retries?: number
  timeout_seconds?: number
}

export interface CreateTriggerRequest {
  name: string
  trigger_type: string
  task_name: string
  task_type: string
  task_params: Record<string, unknown>
  interval_seconds?: number
  cron_expression?: string
  condition_type?: string
  condition_value?: string | string[]
}

export const datacenterService = {
  async getOverview(): Promise<OverviewData> {
    const response = await apiClient.get<OverviewData>('/api/datacenter/overview')
    return response.data
  },

  async getDataSources(): Promise<{ sources: DataSourceInfo[]; total: number }> {
    const response = await apiClient.get<{ sources: DataSourceInfo[]; total: number }>('/api/datacenter/sources')
    return response.data
  },

  async getDataTypes(): Promise<{ data_types: Array<{ type_id: string; name: string; category: string }>; total: number }> {
    const response = await apiClient.get('/api/datacenter/data-types')
    return response.data
  },

  async getTasks(params?: { status?: string; task_type?: string }): Promise<{ tasks: TaskDefinition[]; total: number }> {
    const response = await apiClient.get('/api/datacenter/tasks', { params })
    return response.data
  },

  async getTask(taskId: string): Promise<TaskDefinition> {
    const response = await apiClient.get<TaskDefinition>(`/api/datacenter/tasks/${taskId}`)
    return response.data
  },

  async createTask(request: CreateTaskRequest): Promise<{ success: boolean; task_id: string; message: string }> {
    const response = await apiClient.post('/api/datacenter/tasks', request)
    return response.data
  },

  async startTask(taskId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.put(`/api/datacenter/tasks/${taskId}/start`)
    return response.data
  },

  async pauseTask(taskId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.put(`/api/datacenter/tasks/${taskId}/pause`)
    return response.data
  },

  async cancelTask(taskId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.put(`/api/datacenter/tasks/${taskId}/cancel`)
    return response.data
  },

  async retryTask(taskId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.put(`/api/datacenter/tasks/${taskId}/retry`)
    return response.data
  },

  async startAllTasks(): Promise<{ success: boolean; started: string[]; skipped: string[]; message: string }> {
    const response = await apiClient.post('/api/datacenter/tasks/start-all')
    return response.data
  },

  async pauseAllTasks(): Promise<{ success: boolean; paused: string[]; skipped: string[]; message: string }> {
    const response = await apiClient.post('/api/datacenter/tasks/pause-all')
    return response.data
  },

  async getQueueStatus(): Promise<{ queue_size: number; running_count: number; stats: QueueStats }> {
    const response = await apiClient.get('/api/datacenter/queue')
    return response.data
  },

  async getExecutions(params?: { task_id?: string; limit?: number }): Promise<{
    executions: Array<{
      execution_id: string
      task_id: string
      status: string
      started_at: string
      completed_at: string | null
      duration_ms: number | null
      records_processed: number
      records_failed: number
      error: string | null
    }>
    total: number
  }> {
    const response = await apiClient.get('/api/datacenter/executions', { params })
    return response.data
  },

  async getTriggers(params?: { trigger_type?: string }): Promise<{ triggers: TriggerDefinition[]; total: number }> {
    const response = await apiClient.get('/api/datacenter/triggers', { params })
    return response.data
  },

  async createTrigger(request: CreateTriggerRequest): Promise<{ success: boolean; trigger_id: string; message: string }> {
    const response = await apiClient.post('/api/datacenter/triggers', request)
    return response.data
  },

  async enableTrigger(triggerId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.put(`/api/datacenter/triggers/${triggerId}/enable`)
    return response.data
  },

  async disableTrigger(triggerId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.put(`/api/datacenter/triggers/${triggerId}/disable`)
    return response.data
  },

  async executeTrigger(triggerId: string): Promise<{ success: boolean; task_id: string; message: string }> {
    const response = await apiClient.post(`/api/datacenter/triggers/${triggerId}/execute`)
    return response.data
  },

  async getMonitoring(): Promise<{
    timestamp: string
    queue: QueueStats
    triggers: { total_triggers: number; enabled: number }
    running_tasks: TaskDefinition[]
    recent_errors: Array<{ task_id: string; name: string; error: string }>
  }> {
    const response = await apiClient.get('/api/datacenter/monitoring')
    return response.data
  },

  async initDefaultTasks(): Promise<{
    success: boolean
    created_count: number
    skipped_count: number
    tasks: Array<{ task_id: string; name: string; task_type: string }>
    message: string
  }> {
    const response = await apiClient.post('/api/datacenter/init-default-tasks')
    return response.data
  },

  async getTaskTypes(): Promise<{
    task_types: Array<{
      type: string
      name: string
      description: string
      data_source: string
    }>
    total: number
  }> {
    const response = await apiClient.get('/api/datacenter/task-types')
    return response.data
  },

  async startQueue(): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post('/api/datacenter/queue/start')
    return response.data
  },

  async stopQueue(): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post('/api/datacenter/queue/stop')
    return response.data
  },
}
