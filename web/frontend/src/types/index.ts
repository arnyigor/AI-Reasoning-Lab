export interface TestConfig {
  model_name: string
  temperature?: number
  max_tokens?: number
  api_key?: string
  custom_params?: Record<string, any>
}

export interface Test {
  id: string
  name: string
  description: string
  category: string
  difficulty: string
  file_path: string
  config_template: TestConfig
}

export interface TestResult {
  test_id: string
  session_id: string
  success: boolean
  accuracy?: number
  execution_time: number
  error_message?: string
  raw_output?: string
  timestamp: string
}

export interface Session {
  id: string
  name?: string
  status: 'created' | 'running' | 'completed' | 'failed' | 'stopped'
  test_ids: string[]
  config: Record<string, any>
  created_at: string
  started_at?: string
  completed_at?: string
  progress: number
  current_test?: string
  results: any[]
}

export interface LogEvent {
  type: string
  content: string
  timestamp: number
  chunk_index?: number
  session_id?: string
  test_id?: string
}