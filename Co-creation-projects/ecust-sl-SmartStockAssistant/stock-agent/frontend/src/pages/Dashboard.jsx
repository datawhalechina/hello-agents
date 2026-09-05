import { Layout, Space, Row, Col, Button } from 'antd'
import { HomeOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import SearchBar from '../components/SearchBar'
import MetricCards from '../components/MetricCards'
import KlineChart from '../components/KlineChart'
import ScorePanel from '../components/ScorePanel'
import ReportPanel from '../components/ReportPanel'
import HotStocks from '../components/HotStocks'
import AnalysisProgress from '../components/AnalysisProgress'
import { useAnalysis } from '../hooks/useAnalysis'

const { Content } = Layout

export default function Dashboard() {
  const { result, loading, error, analyze, reset } = useAnalysis()

  const handlePickHot = (stock) => {
    analyze(stock.symbol, stock.market)
    setTimeout(() => {
      window.scrollTo({ top: 200, behavior: 'smooth' })
    }, 50)
  }

  const handleGoHome = () => {
    reset()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // 首屏（无结果、未加载、无错误）展示热门股票网格
  const showHome = !result && !loading && !error
  const showBackButton = result || error || loading

  return (
    <Content style={{
      padding: '24px',
      maxWidth: 1280,
      margin: '0 auto',
      width: '100%',
    }}>
      <Space orientation="vertical" size={20} style={{ width: '100%' }}>

        {/* 顶部条：返回首页 + 搜索栏 */}
        <div style={{
          background: 'var(--ant-color-bg-container, #fff)',
          borderRadius: 8,
          padding: '14px 20px',
          border: '1px solid rgba(0,0,0,0.06)',
        }}>
          {showBackButton && (
            <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Button
                type="text"
                icon={<ArrowLeftOutlined />}
                onClick={handleGoHome}
                disabled={loading}
                style={{ paddingLeft: 0 }}
              >
                返回首页
              </Button>
              <Button
                type="text"
                icon={<HomeOutlined />}
                onClick={handleGoHome}
                disabled={loading}
              >
                热门涨幅榜
              </Button>
            </div>
          )}
          <SearchBar onAnalyze={analyze} loading={loading} />
        </div>

        {/* 热门股票（首屏） */}
        {showHome && <HotStocks onPick={handlePickHot} />}

        {/* 分析进度 */}
        <AnalysisProgress active={loading} />

        {/* 指标卡 */}
        {result && <MetricCards result={result} />}

        {/* K线 + 三维评分 */}
        {result && (
          <Row gutter={16} align="stretch">
            <Col span={16}>
              <KlineChart klineData={result.kline_data || []} />
            </Col>
            <Col span={8}>
              <ScorePanel scores={result.scores} />
            </Col>
          </Row>
        )}

        {/* 分析报告 */}
        {(result || error) && (
          <ReportPanel
            report={result?.report}
            error={error}
            loading={false}
          />
        )}

        {/* 分析完成后底部再放一个返回入口，方便切换 */}
        {(result || error) && !loading && (
          <div style={{ textAlign: 'center', padding: '12px 0 4px' }}>
            <Button
              type="primary"
              ghost
              size="large"
              icon={<HomeOutlined />}
              onClick={handleGoHome}
            >
              返回热门涨幅榜
            </Button>
          </div>
        )}

      </Space>
    </Content>
  )
}
