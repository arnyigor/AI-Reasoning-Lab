import { Card, Button, Progress, Alert, Select, Form, InputNumber, Input, Divider } from 'antd'
import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../store/store'
import { createSession, startSession } from '../store/slices/sessionsSlice'

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
  const dispatch = useDispatch()
  const { currentSession, loading } = useSelector((state: RootState) => state.sessions)
  const { tests } = useSelector((state: RootState) => state.tests)

  const [modelName, setModelName] = useState<string>('')
  const [provider, setProvider] = useState<string>('')
  const [apiBase, setApiBase] = useState<string>('')
  const [temperature, setTemperature] = useState<number>(0.7)
  const [maxTokens, setMaxTokens] = useState<number>(1000)
  const [selectedTestIds, setSelectedTestIds] = useState<string[]>([])
  const [testCount, setTestCount] = useState<number>(1)

  // Получаем выбранные тесты из TestNavigator через localStorage или props
  useEffect(() => {
    const handleStorageChange = () => {
      const stored = localStorage.getItem('selectedTests')
      if (stored) {
        setSelectedTestIds(JSON.parse(stored))
      }
    }

    handleStorageChange()
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [])

  // Автоматическая подстановка URL при выборе провайдера
  useEffect(() => {
    if (provider && PROVIDER_URLS[provider as keyof typeof PROVIDER_URLS]) {
      setApiBase(PROVIDER_URLS[provider as keyof typeof PROVIDER_URLS])
    }
  }, [provider])

  const handleStartSession = () => {
    if (!modelName || !provider || selectedTestIds.length === 0) {
      alert('Please enter model name, select provider and at least one test')
      return
    }

    const sessionData = {
      test_ids: selectedTestIds.slice(0, testCount), // Ограничиваем количество тестов
      model_configuration: {
        model_name: modelName,
        client_type: provider,
        api_base: apiBase,
        temperature,
        max_tokens: maxTokens
      },
      session_name: `Session with ${modelName} (${testCount} tests)`
    }

    dispatch(createSession(sessionData)).then((result) => {
      if (createSession.fulfilled.match(result)) {
        // Автоматически запускаем сессию после создания
        const sessionId = result.payload.id
        dispatch(startSession(sessionId))
      }
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

          <Form.Item label="Number of Tests">
            <InputNumber
              min={1}
              max={selectedTestIds.length || 1}
              value={testCount}
              onChange={(value) => setTestCount(value || 1)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Divider />

          <Form.Item>
            <div>
              <p><strong>Selected Tests:</strong> {selectedTestIds.length} (Running: {Math.min(testCount, selectedTestIds.length)})</p>
              {selectedTestIds.length > 0 && (
                <ul>
                  {selectedTestIds.slice(0, testCount).map(testId => {
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
            <Progress percent={currentSession.progress * 100} />
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
    </div>
  )
}