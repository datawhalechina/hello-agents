// 前端共享类型定义：与后端 backend/models/schemas.py 保持一致

/** 七步漏斗式信息收敛链路的阶段标识 */
export type StageKey =
  | 'step1_parse'
  | 'step2_extract'
  | 'step3_index'
  | 'step4_gap'
  | 'step5_innovation'
  | 'step6_experiment'
  | 'step7_integrate'

/** 单步状态：待执行 / 运行中 / 完成 / 失败 / 降级 / 复用缓存 */
export type StepStatus = 'pending' | 'running' | 'done' | 'failed' | 'degraded' | 'cached'

/** 后端推送的进度事件（SSE 单条 data 反序列化结果） */
export interface ProgressEvent {
  stage: StageKey
  status: 'running' | 'done' | 'failed' | 'degraded' | 'cached'
  message: string
  /** 整体进度 0-1 */
  progress: number
  /** 附加载荷，例如该步骤的中间产物摘要 */
  payload?: Record<string, unknown> | null
}

/** 三维评分：新颖性 / 可行性 / 显著性，0-10 分 */
export interface ThreeDScore {
  novelty: number
  feasibility: number
  significance: number
}

/** 工具调用记录 */
export interface ToolCallRecord {
  tool_name: string
  args_summary: string
  success: boolean
  duration_sec: number
  error?: string | null
  timestamp?: string
}

/** 评估报告：随最终报告一并输出 */
export interface Evaluation {
  innovations_scores: ThreeDScore[]
  /** 工具调用成功率 0-1 */
  tool_call_success_rate: number
  total_tool_calls: number
  failed_tool_calls: number
  /** 平均自校验置信度 0-1 */
  avg_confidence: number
  tool_calls: ToolCallRecord[]
}

/** 创新点 */
export interface Innovation {
  title: string
  idea: string
  source: string
  gap_origin: string
  score: ThreeDScore
  novelty_check?: string | null
  supporting_evidence?: string
}

/** 实验方案 */
export interface ExperimentPlan {
  innovation_title: string
  hypothesis: string
  datasets: string[]
  baselines: string[]
  metrics: string[]
  ablation: string[]
  steps: string[]
  expected_results: string
  risks: string
}

/** 后端最终报告（步骤7 整合输出）的结构化对象 */
export interface FinalReport {
  background_review?: string
  innovations?: Innovation[]
  experiment_plans?: ExperimentPlan[]
  references?: Array<Record<string, unknown>>
  evaluation?: Evaluation | null
  markdown?: string
  generated_at?: string
}

/** GET /api/report/{task_id} 的响应 */
export interface Report {
  markdown: string
  report: FinalReport
  evaluation: Evaluation | null
  status: string
}

/** GET /api/tasks/{task_id} 的响应 */
export interface TaskStatus {
  task_id: string
  status: string
  progress: number
  current_stage?: StageKey | null
}

/** GET /api/health 的响应 */
export interface HealthInfo {
  status: string
  model: string
}

/** 步骤元信息：用于时间线渲染 */
export interface StageInfo {
  key: StageKey
  label: string
  description: string
}

/** 七步链路定义（与后端 StepStage 枚举对齐） */
export const STAGE_LIST: StageInfo[] = [
  { key: 'step1_parse', label: '论文解析', description: 'PyMuPDF 解析 PDF 章节结构（已预处理则复用缓存）' },
  { key: 'step2_extract', label: '结构化抽取', description: '单篇字段抽取 + Reflexion 自校验（已预处理则复用缓存）' },
  { key: 'step3_index', label: '向量索引构建', description: 'BGE-m3 嵌入 + Chroma + BM25 混合检索（已预处理则复用缓存）' },
  { key: 'step4_gap', label: 'Gap 识别', description: '跨论文综合分析，识别研究空白' },
  { key: 'step5_innovation', label: '创新点生成', description: '生成并筛选 2-3 个创新点（结合研究方向）' },
  { key: 'step6_experiment', label: '实验方案设计', description: '为创新点设计完整实验方案' },
  { key: 'step7_integrate', label: '整合输出', description: '生成 Markdown 研究提案报告' },
]

/** 预处理状态 */
export type PreprocessStatus = 'pending' | 'done' | 'failed'

/** 论文库中的论文元数据 */
export interface Paper {
  paper_id: string
  filename: string
  source: 'upload' | 'folder'
  original_path: string
  upload_time: string
  title: string
  parse_status: PreprocessStatus
  extract_status: PreprocessStatus
  index_status: PreprocessStatus
  parsed_at?: string | null
  extracted_at?: string | null
  indexed_at?: string | null
}

/** 上传论文响应 */
export interface UploadResponse {
  paper_id: string
  filename: string
  duplicate: boolean
}

/** 分析请求参数 */
export interface AnalyzeParams {
  folder_path?: string
  paper_ids?: string[]
  research_direction?: string
}
