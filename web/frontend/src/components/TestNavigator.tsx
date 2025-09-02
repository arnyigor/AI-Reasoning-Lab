import { List, Typography, Collapse, Checkbox } from 'antd'
import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../store/store'
import { fetchTests } from '../store/slices/testsSlice'
import { Test } from '../types'

const { Title } = Typography
const { Panel } = Collapse

export function TestNavigator() {
  const dispatch = useDispatch()
  const { tests, loading } = useSelector((state: RootState) => state.tests)
  const [selectedTests, setSelectedTests] = useState<string[]>([])

  useEffect(() => {
    dispatch(fetchTests())
  }, [dispatch])

  const testItems = Object.values(tests) as Test[]

  // Группировка тестов по категориям
  const testsByCategory = testItems.reduce((acc: Record<string, Test[]>, test: Test) => {
    if (!acc[test.category]) {
      acc[test.category] = []
    }
    acc[test.category].push(test)
    return acc
  }, {} as Record<string, Test[]>)

  const handleTestSelect = (testId: string, checked: boolean) => {
    let newSelected: string[]
    if (checked) {
      newSelected = [...selectedTests, testId]
    } else {
      newSelected = selectedTests.filter(id => id !== testId)
    }
    setSelectedTests(newSelected)
    localStorage.setItem('selectedTests', JSON.stringify(newSelected))
  }

  const handleCategorySelect = (category: string, checked: boolean) => {
    const categoryTests = testsByCategory[category].map(test => test.id)
    let newSelected: string[]
    if (checked) {
      newSelected = [...new Set([...selectedTests, ...categoryTests])]
    } else {
      newSelected = selectedTests.filter(id => !categoryTests.includes(id))
    }
    setSelectedTests(newSelected)
    localStorage.setItem('selectedTests', JSON.stringify(newSelected))
  }

  const isCategorySelected = (category: string) => {
    const categoryTests = testsByCategory[category].map(test => test.id)
    return categoryTests.every(testId => selectedTests.includes(testId))
  }

  const isCategoryIndeterminate = (category: string) => {
    const categoryTests = testsByCategory[category].map(test => test.id)
    const selectedInCategory = categoryTests.filter(testId => selectedTests.includes(testId))
    return selectedInCategory.length > 0 && selectedInCategory.length < categoryTests.length
  }

  return (
    <div style={{ padding: '16px' }}>
      <Title level={4}>Available Tests</Title>
      <div style={{ marginBottom: '16px' }}>
        <span>Selected: {selectedTests.length} tests</span>
      </div>
      <Collapse defaultActiveKey={Object.keys(testsByCategory)} ghost>
        {Object.entries(testsByCategory).map(([category, categoryTests]) => (
          <Panel
            key={category}
            header={
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <Checkbox
                  checked={isCategorySelected(category)}
                  indeterminate={isCategoryIndeterminate(category)}
                  onChange={(e) => handleCategorySelect(category, e.target.checked)}
                  style={{ marginRight: '8px' }}
                />
                <span>{category} ({categoryTests.length})</span>
              </div>
            }
          >
            <List
              loading={loading}
              dataSource={categoryTests.sort((a, b) => a.name.localeCompare(b.name))}
              renderItem={(test) => (
                <List.Item style={{ padding: '8px 0' }}>
                  <Checkbox
                    checked={selectedTests.includes(test.id)}
                    onChange={(e) => handleTestSelect(test.id, e.target.checked)}
                    style={{ marginRight: '8px' }}
                  />
                  <List.Item.Meta
                    title={test.name}
                    description={test.difficulty}
                  />
                </List.Item>
              )}
            />
          </Panel>
        ))}
      </Collapse>
    </div>
  )
}