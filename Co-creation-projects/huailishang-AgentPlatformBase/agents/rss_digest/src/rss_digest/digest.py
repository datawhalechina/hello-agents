from __future__ import annotations

from datetime import datetime
from pathlib import Path
from html import escape


def _render_list(items: list[str]) -> str:
    if not items:
        return "<p class='muted'>暂无</p>"
    lis = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"<ul>{lis}</ul>"


def render_html(articles: list[dict[str, str]], output_path: Path) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cards = []

    for article in articles:
        summary_data = article.get("summary_data") or {}
        score = article.get("article_score") or summary_data.get("score") or 0
        worth = article.get("worth_reading") or summary_data.get("worth_reading") or "未评级"
        one_line = article.get("one_line") or summary_data.get("one_line") or "暂无一句话结论"
        article_type = article.get("article_type") or summary_data.get("article_type") or "未分类"
        summary = summary_data.get("summary") or article.get("summary_cn") or "暂无中文摘要"
        key_points = summary_data.get("key_points") or []
        keywords = summary_data.get("keywords") or []
        why_it_matters = summary_data.get("why_it_matters") or ""
        engineering_takeaway = summary_data.get("engineering_takeaway") or ""
        business_signal = summary_data.get("business_signal") or ""
        limitations = summary_data.get("limitations") or ""
        recommended_action = summary_data.get("recommended_action") or ""

        keyword_html = "".join(f"<span class='chip'>{escape(keyword)}</span>" for keyword in keywords)
        score_class = "high" if score >= 85 else "mid" if score >= 70 else "low"

        cards.append(
            f"""
            <section class="card">
              <div class="meta">
                <span class="tag">{escape(article.get("category", ""))}</span>
                <span class="type">{escape(article_type)}</span>
                <span class="source">{escape(article.get("source_name", ""))}</span>
                <span class="date">{escape(article.get("published_at", "")[:10])}</span>
              </div>
              <div class="headline">
                <h2><a href="{escape(article.get("link", ""))}" target="_blank" rel="noreferrer">{escape(article.get("title", ""))}</a></h2>
                <div class="score {score_class}">
                  <strong>{escape(str(score))}</strong>
                  <span>{escape(worth)}</span>
                </div>
              </div>
              <p class="one-line">{escape(one_line)}</p>
              <div class="summary-block">
                <h3>摘要</h3>
                <p>{escape(summary)}</p>
              </div>
              <div class="grid">
                <div class="panel">
                  <h3>关键点</h3>
                  {_render_list(key_points)}
                </div>
                <div class="panel">
                  <h3>为什么值得关注</h3>
                  <p>{escape(why_it_matters or '暂无')}</p>
                </div>
                <div class="panel">
                  <h3>工程 / 决策启发</h3>
                  <p>{escape(engineering_takeaway or '暂无')}</p>
                </div>
                <div class="panel">
                  <h3>商业信号</h3>
                  <p>{escape(business_signal or '暂无')}</p>
                </div>
                <div class="panel">
                  <h3>局限与边界</h3>
                  <p>{escape(limitations or '暂无')}</p>
                </div>
                <div class="panel">
                  <h3>下一步动作</h3>
                  <p>{escape(recommended_action or '暂无')}</p>
                </div>
              </div>
              <div class="keywords">{keyword_html or "<span class='muted'>暂无关键词</span>"}</div>
            </section>
            """
        )

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI RSS Daily Digest</title>
  <style>
    :root {{
      --bg: #f6f1e7;
      --panel: rgba(255, 252, 246, 0.92);
      --ink: #1d1a16;
      --muted: #6e6458;
      --line: #dbd0be;
      --accent: #9a4f2b;
      --accent-soft: #f5e0cf;
      --green: #2f6b4f;
      --green-soft: #dff1e7;
      --amber: #8a5d17;
      --amber-soft: #f6e7c5;
      --rose: #8a3e3a;
      --rose-soft: #f5dcd9;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, #f7e6d9 0, transparent 26%),
        radial-gradient(circle at left bottom, #ece1cf 0, transparent 22%),
        linear-gradient(180deg, #f7f2e8 0%, #efe7da 100%);
    }}
    .page {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 18px 56px;
    }}
    .hero {{
      padding: 24px 26px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: var(--panel);
      backdrop-filter: blur(6px);
      box-shadow: 0 14px 28px rgba(0, 0, 0, 0.04);
    }}
    .hero h1 {{
      margin: 0 0 10px;
      font-size: 34px;
      line-height: 1.08;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
    }}
    .list {{
      margin-top: 22px;
      display: grid;
      gap: 18px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 22px;
      box-shadow: 0 12px 26px rgba(0, 0, 0, 0.03);
    }}
    .meta {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 12px;
    }}
    .tag, .type, .chip {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 600;
    }}
    .tag {{
      background: var(--accent-soft);
      color: var(--accent);
    }}
    .type {{
      background: #ece6ff;
      color: #5744a3;
    }}
    .headline {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
    }}
    h2 {{
      margin: 0;
      font-size: 24px;
      line-height: 1.28;
      max-width: 82%;
    }}
    a {{
      color: inherit;
      text-decoration: none;
    }}
    a:hover {{
      color: var(--accent);
    }}
    .score {{
      min-width: 112px;
      text-align: center;
      border-radius: 16px;
      padding: 10px 12px;
      border: 1px solid var(--line);
    }}
    .score strong {{
      display: block;
      font-size: 24px;
      line-height: 1;
    }}
    .score span {{
      display: block;
      margin-top: 6px;
      font-size: 12px;
    }}
    .score.high {{
      background: var(--green-soft);
      color: var(--green);
    }}
    .score.mid {{
      background: var(--amber-soft);
      color: var(--amber);
    }}
    .score.low {{
      background: var(--rose-soft);
      color: var(--rose);
    }}
    .one-line {{
      margin: 14px 0 18px;
      font-size: 17px;
      line-height: 1.7;
      font-weight: 600;
    }}
    .summary-block {{
      padding: 16px 18px;
      border-radius: 16px;
      background: rgba(255,255,255,0.52);
      border: 1px solid var(--line);
    }}
    h3 {{
      margin: 0 0 8px;
      font-size: 15px;
    }}
    .summary-block p, .panel p, li {{
      margin: 0;
      line-height: 1.75;
      color: #2d2823;
    }}
    .grid {{
      margin-top: 16px;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .panel {{
      padding: 14px 16px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.56);
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
    .keywords {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 16px;
    }}
    .chip {{
      background: #efe9df;
      color: #574f45;
    }}
    .muted {{
      color: var(--muted);
    }}
    @media (max-width: 820px) {{
      .headline {{
        flex-direction: column;
      }}
      h2 {{
        max-width: 100%;
      }}
      .score {{
        min-width: 0;
      }}
      .grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>AI RSS Daily Digest</h1>
      <p>生成时间：{escape(generated_at)}。这不是逐篇翻译，而是按信息密度、可读价值和工程/产业启发整理出的中文阅读卡片。</p>
    </section>
    <section class="list">
      {''.join(cards) if cards else '<p class="muted">今天还没有可展示的文章。</p>'}
    </section>
  </main>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_doc, encoding="utf-8")
