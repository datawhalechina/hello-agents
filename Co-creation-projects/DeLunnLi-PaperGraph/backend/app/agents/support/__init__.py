__all__ = ["SearchExplainer"]


class SearchExplainer:
    def format_search_explanation(self, intent, papers):
        if not papers:
            return "未找到匹配的论文"
        n = len(papers)
        years = sorted({p.year for p in papers if p.year}, reverse=True)
        yr = f" ({years[0]}-{years[-1]})" if len(years) >= 2 else f" ({years[0]})" if years else ""
        return f"找到 {n} 篇相关论文{yr}"
