const RESULT_SOURCE_META: Record<string, { label: string; color: string }> = {
  arxiv: { label: 'arXiv', color: 'orange' },
  semantic_scholar: { label: 'S2', color: 'geekblue' },
  dblp: { label: 'DBLP', color: 'cyan' },
  openalex: { label: 'OpenAlex', color: 'purple' },
  crossref: { label: 'Crossref', color: 'default' },
  pubmed: { label: 'PubMed', color: 'green' },
  unknown: { label: '其他', color: 'default' },
}

export function resultSourceMeta(src: string | undefined) {
  const key = (src || 'unknown').toLowerCase()
  return RESULT_SOURCE_META[key] ?? { label: src || '其他', color: 'default' }
}
