import { Layout } from 'antd'
import { TestNavigator } from './components/TestNavigator'
import { TestRunner } from './components/TestRunner'
import { ResultsViewer } from './components/ResultsViewer'

const { Header, Sider, Content } = Layout

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ color: 'white', fontSize: '20px', fontWeight: 'bold' }}>
        AI-Reasoning-Lab Web Interface
      </Header>
      <Layout>
        <Sider width={300} style={{ background: '#fff' }}>
          <TestNavigator />
        </Sider>
        <Content style={{ padding: '24px', background: '#fff' }}>
          <TestRunner />
          <ResultsViewer />
        </Content>
      </Layout>
    </Layout>
  )
}

export default App