from duckduckgo_search import DDGS

def search(keywords, **kwargs):
    results = []
    try:
        with DDGS(proxy=kwargs.get("proxy", None)) as ddgs:
            for index, result in enumerate(
                ddgs.news(
                    keywords,
                    max_results=kwargs.get("max_results", 8),
                    timelimit=kwargs.get("timelimit", "d"),
                )
            ):
                results.append({
                    "id": index,
                    "title": result["title"],
                    "brief": result["body"],
                    "url": result["url"],
                    "source": result["source"],
                    "date": result["date"],
                })
        return results
    except Exception as e:
        if "logger" in kwargs:
            kwargs["logger"].error(f"[Search]: Can not search '{ keywords }'.\tError: { str(e) }")
        return [] 
