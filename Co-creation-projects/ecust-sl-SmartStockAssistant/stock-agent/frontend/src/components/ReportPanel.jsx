import { FileTextOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { Card, Tag, Alert, Skeleton, Typography, Spin } from 'antd'

const { Text } = Typography

export default function ReportPanel({ report, error, loading }) {
  if (loading) return (
    <Card>
      <div style={{ textAlign: "center", padding: "40px 0" }}>
        <Spin size="large" />
        <div style={{ marginTop: 16, color: "#888", fontSize: 13 }}>
          正在获取实时数据并生成 AI 分析报告，请稍候约 20 秒...
        </div>
      </div>
    </Card>
  )
  if (error) return (
    <Alert type="error" message="分析失败" description={error} showIcon />
  )

  if (!report) return null

  return (
    <Card
      title={<span><FileTextOutlined /> 投资分析报告</span>}
      size="small"
      extra={<Tag color="blue">AI 生成</Tag>}
    >
      <div style={{
        fontSize: 13,
        lineHeight: 1.8,
        color: 'inherit',
        maxHeight: 400,
        overflowY: 'auto',
      }}>
        <ReactMarkdown>{report}</ReactMarkdown>
      </div>
      <div style={{ marginTop: 12, fontSize: 11, color: '#aaa' }}>
        * 本报告由 AI 生成，仅供参考，不构成投资建议。
      </div>
    </Card>
  )
}