import { Card, Table, Empty } from 'antd'
import { useSelector } from 'react-redux'
import { RootState } from '../store/store'

export function ResultsViewer() {
  const { currentSession } = useSelector((state: RootState) => state.sessions)

  const columns = [
    {
      title: 'Test ID',
      dataIndex: 'test_id',
      key: 'test_id',
    },
    {
      title: 'Success',
      dataIndex: 'success',
      key: 'success',
      render: (success: boolean) => success ? '✅' : '❌',
    },
    {
      title: 'Accuracy',
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (accuracy?: number) => accuracy ? `${(accuracy * 100).toFixed(1)}%` : '-',
    },
    {
      title: 'Execution Time',
      dataIndex: 'execution_time',
      key: 'execution_time',
      render: (time: number) => `${time.toFixed(2)}s`,
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Card title="Results Viewer">
        {currentSession && currentSession.results.length > 0 ? (
          <Table
            dataSource={currentSession.results}
            columns={columns}
            rowKey="test_id"
            pagination={false}
          />
        ) : (
          <Empty description="No results available" />
        )}
      </Card>
    </div>
  )
}