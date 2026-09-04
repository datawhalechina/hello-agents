export interface ConfigSchemaField {
  type: 'string' | 'number' | 'boolean' | 'select';
  label: string;
  default: string | number | boolean;
  options?: string[];
  description?: string;
  minimum?: number;
  maximum?: number;
}

export interface ConfigSchema {
  title: string;
  fields: Record<string, ConfigSchemaField>;
}

export type ConfigSchemas = Record<string, ConfigSchema>;

export interface ConfigValues {
  [key: string]: unknown;
}

/** 模型注册表中的一个模型项（api_key 由后端掩码返回） */
export interface ModelEntry {
  name: string;
  label: string;
  base_url: string;
  api_key: string;
  model: string;
}

/** 添加模型的请求体 */
export interface ModelInput {
  name: string;
  label: string;
  base_url: string;
  api_key: string;
  model: string;
}

export interface ModelListResponse {
  active_model: string;
  models: ModelEntry[];
}

/** Embedding 模型配置（api_key 由后端掩码返回） */
export interface EmbeddingConfig {
  label: string;
  base_url: string;
  api_key: string;
  model: string;
}

/** Reranker 模型配置（api_key 由后端掩码返回） */
export interface RerankerConfig {
  label: string;
  base_url: string;
  api_key: string;
  model: string;
}

/** 更新 embedding / reranker 的请求体（api_key 留空 = 保留原 key） */
export interface AuxModelUpdate {
  label?: string;
  base_url?: string;
  api_key?: string;
  model?: string;
}

/** 反思笔记严重程度 */
export type ReflectionSeverity = 'fatal' | 'high' | 'medium' | 'low';

/** 反思笔记一条记录（tags 为逗号分隔字符串，与后端存储一致） */
export interface ReflectionEntry {
  ref_id: string;
  error_desc: string;
  solution: string;
  philosophy: string;
  tags: string;
  severity: ReflectionSeverity;
  timestamp: string;
  updated_at?: string;
}

/** 新增反思笔记的请求体 */
export interface ReflectionCreate {
  error_desc: string;
  solution: string;
  philosophy: string;
  tags?: string;
  severity?: string;
}

/** 局部更新反思笔记的请求体（全可选，仅合并传入字段） */
export interface ReflectionUpdate {
  error_desc?: string;
  solution?: string;
  philosophy?: string;
  tags?: string;
  severity?: string;
}
