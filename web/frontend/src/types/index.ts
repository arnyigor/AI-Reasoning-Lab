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
  logs?: LogEntry[]
}

export interface LogEntry {
  timestamp: string
  level: string
  message: string
  type?: string
}

export interface LogEvent {
  type: string
  content: string
  timestamp: number
  chunk_index?: number
  session_id?: string
  test_id?: string
}

export interface Model {
  id: string
  name: string
  client_type: string
  api_base: string
  temperature: number
  max_tokens: number
  description: string
}

export interface CreateSessionRequest {
  test_ids: string[]
  model_configuration: {
    model_name: string
    client_type: string
    api_base?: string
    api_key?: string
    temperature?: number
    max_tokens?: number
    top_p?: number
    num_ctx?: number
    repeat_penalty?: number
    num_gpu?: number
    num_thread?: number
    num_parallel?: number
    low_vram?: boolean
    query_timeout?: number
    stream?: boolean
    think?: boolean
    system_prompt?: string
  }
  test_configuration?: {
    runs_per_test?: number
    show_payload?: boolean
    raw_save?: boolean
  }
  ollama_configuration?: {
    use_params?: boolean
    num_parallel?: number
    max_loaded_models?: number
    cpu_threads?: number
    flash_attention?: boolean
    keep_alive?: string
    host?: string
  }
  session_name?: string
}