import { Card, Button, Progress, Alert } from 'antd'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../store/store'
import { createSession } from '../store/slices/sessionsSlice'

export function TestRunner() {
  const dispatch = useDispatch()
  const { currentSession, loading } = useSelector((state: RootState) => state.sessions)

  const handleStartSession = () => {
    dispatch(createSession())
  }

  return (
    <div style={{ padding: '24px' }}>
      <Card title="Test Runner" style={{ marginBottom: '16px' }}>
        {!currentSession ? (
          <Button
            type="primary"
            size="large"
            onClick={handleStartSession}
            loading={loading}
          >
            Start New Session
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