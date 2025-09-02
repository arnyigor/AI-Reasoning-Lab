import { List, Typography } from 'antd'
import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../store/store'
import { fetchTests } from '../store/slices/testsSlice'

const { Title } = Typography

export function TestNavigator() {
  const dispatch = useDispatch()
  const { tests, loading } = useSelector((state: RootState) => state.tests)

  useEffect(() => {
    dispatch(fetchTests())
  }, [dispatch])

  const testItems = Object.values(tests)

  return (
    <div style={{ padding: '16px' }}>
      <Title level={4}>Available Tests</Title>
      <List
        loading={loading}
        dataSource={testItems}
        renderItem={(test) => (
          <List.Item>
            <List.Item.Meta
              title={test.name}
              description={`${test.category} • ${test.difficulty}`}
            />
          </List.Item>
        )}
      />
    </div>
  )
}