import { Card, Button, Progress, Alert, Select, Form, InputNumber, Input, Divider, Checkbox, List, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState, AppDispatch } from '../store/store'
import { createSession, startSession } from '../store/slices/sessionsSlice'
import { fetchTests } from '../store/slices/testsSlice'

const { Option } = Select

// Маппинг провайдеров к дефолтным URL (согласно client_factory.py)
const PROVIDER_URLS = {
  ollama: 'http://localhost:11434',  // без /v1
  jan: 'http://127.0.0.1:1337/v1',
  lmstudio: 'http://127.0.0.1:1234/v1',
  openai_compatible: 'http://localhost:8000/v1',
  gemini: ''  // не требуется URL
}

export function TestRunner() {
  const dispatch = useDispatch<AppDispatch>()
  const { currentSession, loading } = useSelector((state: RootState) => state.sessions)
  const { tests } = useSelector((state: RootState) => state.tests)

  const [modelName, setModelName] = useState<string>('')
  const [provider, setProvider] = useState<string>('')
  const [apiBase, setApiBase] = useState<string>('')
  const [apiKey, setApiKey] = useState<string>('')
  const [temperature, setTemperature] = useState<number>(0.7)
  const [maxTokens, setMaxTokens] = useState<number>(1000)
  const [topP, setTopP] = useState<number>(0.9)
  const [numCtx, setNumCtx] = useState<number>(4096)
  const [repeatPenalty, setRepeatPenalty] = useState<number>(1.1)
  const [numGpu, setNumGpu] = useState<number>(1)
  const [numThread, setNumThread] = useState<number>(6)
  const [numParallel, setNumParallel] = useState<number>(1)
  const [lowVram, setLowVram] = useState<boolean>(false)
  const [queryTimeout, setQueryTimeout] = useState<number>(600)
  const [stream, setStream] = useState<boolean>(false)
  const [think, setThink] = useState<boolean>(true)
  const [systemPrompt, setSystemPrompt] = useState<string>('')
  const [selectedTestIds, setSelectedTestIds] = useState<string[]>([])
  // testCount убрано - используем все выбранные тесты
  const [runsPerTest, setRunsPerTest] = useState<number>(2)
  const [showPayload, setShowPayload] = useState<boolean>(false)
  const [rawSave, setRawSave] = useState<boolean>(false)

  // Получаем выбранные тесты из TestNavigator через localStorage или props
  useEffect(() => {
    const handleStorageChange = () => {
      const stored = localStorage.getItem('selectedTests')
      if (stored) {
        const parsed = JSON.parse(stored)
        console.log('Loaded selected tests from localStorage:', parsed)
        setSelectedTestIds(parsed)
      } else {
        console.log('No selected tests in localStorage')
      }
    }

    handleStorageChange()
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [])

  // Загрузка тестов при монтировании компонента
  useEffect(() => {
    console.log('Loading tests...')
    dispatch(fetchTests())
  }, [dispatch])

  // Отладка состояния
  useEffect(() => {
    console.log('Current state:')
    console.log('- modelName:', modelName)
    console.log('- provider:', provider)
    console.log('- selectedTestIds:', selectedTestIds)
    console.log('- tests in store:', Object.keys(tests))
    console.log('- currentSession:', currentSession)
    console.log('- loading:', loading)
    console.log('- currentSession exists:', !!currentSession)
    console.log('- currentSession status:', currentSession?.status)
    console.log('- currentSession progress:', currentSession?.progress)
  }, [modelName, provider, selectedTestIds, tests, currentSession, loading])

  // Автоматическая подстановка URL при выборе провайдера
  useEffect(() => {
    if (provider && PROVIDER_URLS[provider as keyof typeof PROVIDER_URLS]) {
      setApiBase(PROVIDER_URLS[provider as keyof typeof PROVIDER_URLS])
    }
  }, [provider])

  const handleStartSession = () => {
    console.log('handleStartSession called')
    console.log('modelName:', modelName)
    console.log('provider:', provider)
    console.log('selectedTestIds:', selectedTestIds)

    if (!modelName || !provider || selectedTestIds.length === 0) {
      alert('Please enter model name, select provider and at least one test')
      return
    }

    // Для некоторых провайдеров API ключ обязателен
    if ((provider === 'openai' || provider === 'gemini') && !apiKey && !apiBase) {
      alert('Please provide API key or custom API base URL for this provider')
      return
    }

    console.log('Validation passed, creating session data...')

    const sessionData = {
      test_ids: selectedTestIds, // Используем все выбранные тесты
      model_configuration: {
        model_name: modelName,
        client_type: provider,
        api_base: apiBase,
        api_key: apiKey,
        temperature,
        max_tokens: maxTokens,
        top_p: topP,
        num_ctx: numCtx,
        repeat_penalty: repeatPenalty,
        num_gpu: numGpu,
        num_thread: numThread,
        num_parallel: numParallel,
        low_vram: lowVram,
        query_timeout: queryTimeout,
        stream,
        think,
        system_prompt: systemPrompt
      },
      test_configuration: {
        runs_per_test: runsPerTest,
        show_payload: showPayload,
        raw_save: rawSave
      },
      session_name: `Session with ${modelName} (${selectedTestIds.length} tests)`
    }

    console.log('sessionData:', sessionData)

    dispatch(createSession(sessionData)).then((result: any) => {
      console.log('createSession result:', result)
      if (createSession.fulfilled.match(result)) {
        console.log('Session created successfully, starting session...')
        // Автоматически запускаем сессию после создания
        const sessionId = result.payload.id
        console.log('Starting session with ID:', sessionId)
        dispatch(startSession(sessionId)).then((startResult: any) => {
          console.log('startSession result:', startResult)
          // Не проверяем state здесь - он обновится асинхронно через useEffect
        })
      } else {
        console.error('Failed to create session:', result)
      }
    }).catch((error: any) => {
      console.error('Error creating session:', error)
    })
  }

  return (
    <div style={{ padding: '24px' }}>
      <Card title="Test Configuration" style={{ marginBottom: '16px' }}>
        <Form layout="vertical">
          <Form.Item label="Model Name" required>
            <Input
              placeholder="Enter model name (e.g., gpt-4, llama2, jan-nano)"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="Provider" required>
            <Select
              placeholder="Select provider"
              value={provider}
              onChange={(value) => setProvider(value)}
              style={{ width: '100%' }}
            >
              <Option value="ollama">Ollama</Option>
              <Option value="jan">Jan</Option>
              <Option value="lmstudio">LM Studio</Option>
              <Option value="openai_compatible">OpenAI Compatible</Option>
              <Option value="gemini">Gemini</Option>
            </Select>
          </Form.Item>

          <Form.Item label="API Base URL">
            <Input
              placeholder="API Base URL (auto-filled based on provider)"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="API Key">
            <Input.Password
              placeholder="API Key (optional)"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Divider>Generation Parameters</Divider>

          <Form.Item label="Temperature">
            <InputNumber
              min={0}
              max={2}
              step={0.1}
              value={temperature}
              onChange={(value) => setTemperature(value || 0.7)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="Max Tokens">
            <InputNumber
              min={1}
              max={10000}
              value={maxTokens}
              onChange={(value) => setMaxTokens(value || 1000)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="Top P">
            <InputNumber
              min={0}
              max={1}
              step={0.1}
              value={topP}
              onChange={(value) => setTopP(value || 0.9)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="Context Length">
            <InputNumber
              min={512}
              max={32768}
              value={numCtx}
              onChange={(value) => setNumCtx(value || 4096)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="Repeat Penalty">
            <InputNumber
              min={1}
              max={2}
              step={0.1}
              value={repeatPenalty}
              onChange={(value) => setRepeatPenalty(value || 1.1)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Divider>Performance Settings</Divider>

          <Form.Item label="GPU Count">
            <InputNumber
              min={0}
              max={8}
              value={numGpu}
              onChange={(value) => setNumGpu(value || 1)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="CPU Threads">
            <InputNumber
              min={1}
              max={32}
              value={numThread}
              onChange={(value) => setNumThread(value || 6)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="Parallel Requests">
            <InputNumber
              min={1}
              max={10}
              value={numParallel}
              onChange={(value) => setNumParallel(value || 1)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="Low VRAM Mode">
            <Checkbox
              checked={lowVram}
              onChange={(e) => setLowVram(e.target.checked)}
            >
              Enable Low VRAM Mode
            </Checkbox>
          </Form.Item>

          <Divider>Advanced Options</Divider>

          <Form.Item label="Query Timeout (seconds)">
            <InputNumber
              min={30}
              max={3600}
              value={queryTimeout}
              onChange={(value) => setQueryTimeout(value || 600)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="Stream Response">
            <Checkbox
              checked={stream}
              onChange={(e) => setStream(e.target.checked)}
            >
              Enable Streaming
            </Checkbox>
          </Form.Item>

          <Form.Item label="Enable Thinking">
            <Checkbox
              checked={think}
              onChange={(e) => setThink(e.target.checked)}
            >
              Enable Chain-of-Thought Reasoning
            </Checkbox>
          </Form.Item>

          <Form.Item label="System Prompt">
            <Input.TextArea
              placeholder="Custom system prompt (optional)"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={3}
            />
          </Form.Item>

          <Divider>Test Configuration</Divider>

          <Form.Item label="Runs Per Test">
            <InputNumber
              min={1}
              max={10}
              value={runsPerTest}
              onChange={(value) => setRunsPerTest(value || 2)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="Show Payload">
            <Checkbox
              checked={showPayload}
              onChange={(e) => setShowPayload(e.target.checked)}
            >
              Show Request Payload
            </Checkbox>
          </Form.Item>

          <Form.Item label="Save Raw Results">
            <Checkbox
              checked={rawSave}
              onChange={(e) => setRawSave(e.target.checked)}
            >
              Save Raw Results
            </Checkbox>
          </Form.Item>

          {/* Number of Tests поле убрано - используем все выбранные тесты */}

          <Divider />

          <Form.Item>
            <div>
              <p><strong>Selected Tests:</strong> {selectedTestIds.length}</p>
              {selectedTestIds.length > 0 && (
                <ul>
                  {selectedTestIds.map(testId => {
                    const test = tests[testId]
                    return test ? (
                      <li key={testId}>{test.name} ({test.category})</li>
                    ) : null
                  })}
                </ul>
              )}
            </div>
          </Form.Item>
        </Form>
      </Card>

      <Card title="Test Runner" style={{ marginBottom: '16px' }}>
        {!currentSession ? (
          <Button
            type="primary"
            size="large"
            onClick={handleStartSession}
            loading={loading}
            disabled={!modelName || !provider || selectedTestIds.length === 0}
          >
            Start Testing Session
          </Button>
        ) : (
          <div>
            <p>Session ID: {currentSession.id}</p>
            <p>Status: {currentSession.status}</p>
            <p>Progress value: {currentSession.progress}</p>
            <Progress percent={Math.max(0, Math.min(100, currentSession.progress * 100))} />
            {currentSession.current_test && (
              <Alert
                message={`Running: ${currentSession.current_test}`}
                type="info"
                showIcon
                style={{ marginTop: '16px' }}
              />
            )}
          </div>
        )}
      </Card>

      {/* Логи выполнения */}
      {currentSession && currentSession.logs && currentSession.logs.length > 0 && (
        <Card title="Execution Logs" style={{ marginBottom: '16px' }}>
          <List
            size="small"
            dataSource={currentSession.logs.slice(-50)} // Показываем последние 50 логов
            renderItem={(log: any) => (
              <List.Item>
                <div style={{ width: '100%' }}>
                  <Typography.Text code style={{ fontSize: '12px', color: '#666' }}>
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </Typography.Text>
                  <Typography.Text
                    style={{
                      marginLeft: '8px',
                      color: log.level === 'error' ? '#ff4d4f' :
                             log.level === 'warning' ? '#faad14' : '#1890ff'
                    }}
                  >
                    [{log.type || 'log'}]
                  </Typography.Text>
                  <Typography.Text style={{ marginLeft: '8px' }}>
                    {log.message}
                  </Typography.Text>
                </div>
              </List.Item>
            )}
          />
        </Card>
      )}

      <Card title="Test Runner" style={{ marginBottom: '16px' }}>
      </Card>
    </div>
  )
}