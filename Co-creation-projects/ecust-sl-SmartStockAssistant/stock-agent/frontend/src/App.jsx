import { useState } from 'react'
import { Layout, ConfigProvider, theme, Switch, Space, Typography } from 'antd'
import { BulbOutlined, BulbFilled, StockOutlined } from '@ant-design/icons'
import zhCN from 'antd/locale/zh_CN'
import Dashboard from './pages/Dashboard'

const { Header } = Layout
const { Title } = Typography

export default function App() {
  const [isDark, setIsDark] = useState(false)

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#185FA5',
          borderRadius: 8,
        },
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          height: 52,
        }}>
          <Space>
            <StockOutlined style={{ fontSize: 20, color: '#fff' }} />
            <Title level={5} style={{ color: '#fff', margin: 0 }}>
              Stock Agent
            </Title>
          </Space>
          <Space>
            <BulbOutlined style={{ color: '#fff', fontSize: 16 }} />
            <Switch
              checked={isDark}
              onChange={setIsDark}
              size="small"
            />
            <BulbFilled style={{ color: isDark ? '#FAC775' : '#fff', fontSize: 16 }} />
          </Space>
        </Header>

        <Dashboard isDark={isDark} />
      </Layout>
    </ConfigProvider>
  )
}
