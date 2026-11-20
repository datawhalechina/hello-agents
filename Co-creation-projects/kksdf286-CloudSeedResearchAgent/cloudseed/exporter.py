"""Reproducible Markdown/BibTeX exports and additive Obsidian notes."""

import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path


def clean(value):
    return str(value).replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def citations(row):
    return " ".join(f"[{eid}]" for eid in row.get("evidence_ids", []))


def bib_escape(value):
    return str(value).replace("\\", "\\textbackslash{} ").replace("{", "\\{").replace("}", "\\}").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")


def bibliography(sources):
    entries = []
    for s in sources:
        fields = {"title": s["title"], "author": " and ".join(s["authors"]), "year": s["year"],
                  "howpublished": s["venue"], "url": s["url"], "doi": s["doi"]}
        if not s["authors"] or s["year"] == "未核实":
            fields["note"] = "Bibliographic metadata requires manual verification"
        lines = [f"  {key} = {{{bib_escape(value)}}}" for key, value in fields.items() if value]
        entries.append(f"@misc{{{s['id']},\n" + ",\n".join(lines) + "\n}")
    return "\n\n".join(entries) + "\n"


def matrix(result):
    lines = ["# 论文对比矩阵", "", "> 本表用于比较任务和方法；评价口径不同的结果不能直接排名。", "",
             "| 资料 | 任务 | 数据与口径 | 方法 | 主要发现 | 局限 |", "| --- | --- | --- | --- | --- | --- |"]
    for p in result["analysis"]["papers"]:
        findings = "；".join(f"{c['text']} {citations(c)}" for c in p["findings"])
        limits = "；".join(f"{c['text']} {citations(c)}" for c in p["limitations"])
        lines.append("| " + " | ".join(clean(v) for v in [f"[[{p['source_id']}]]", p["task"], p["data"], p["method"], findings, limits]) + " |")
    lines += ["", "## 跨论文比较", "", result["comparison"]["summary"], ""]
    for c in result["comparison"]["comparisons"]:
        lines.append(f"- {'、'.join(c['source_ids'])}：{c['reason']} {citations(c)}（可直接比较指标：{'是' if c['can_compare_metrics'] else '否'}）")
    lines += ["", "## 待查证的问题", ""]
    for g in result["comparison"]["gaps"]:
        lines += [f"- **{g['question']}**：{g['basis']} {citations(g)}"]
    return "\n".join(lines) + "\n"


def topic_note(idea, result):
    lines = ["---", "type: topic", "status: candidate", "tags: [research, cloud-seeding, agent-draft]", "---", "",
             f"# {idea['title']}", "", "> 待验证候选假设；新颖性尚未系统检索核验。", "",
             "## 一句话研究问题", "", idea["research_question"], "", "## 可证伪假设", "", idea["hypothesis"], "",
             "## 数据、基线与评测协议", "", "数据要求：" + idea["data_requirements"], "", "基线："]
    lines += [f"- {x}" for x in idea["baselines"]]
    lines += ["", "评价指标："] + [f"- {x}" for x in idea["metrics"]]
    lines += ["", "## 最小可行实验", ""] + [f"{i}. {x}" for i, x in enumerate(idea["steps"], 1)]
    lines += ["", "## 停止条件与反证", "", idea["falsification"], "", "## 风险与替代解释", ""]
    lines += [f"- {x}" for x in idea["risks"]]
    lines += ["", "## 证据与审查", "", citations(idea), "", result["review"]["verdict"], "",
              "关联论文：" + "、".join(f"[[{sid}]]" for sid in dict.fromkeys(eid.split("-E")[0] for eid in idea["evidence_ids"])), "",
              "- [ ] 人工核对证据是否支持假设", "- [ ] 与导师确认地区、云型、数据和标签", "- [ ] 检索相似工作后再评估新颖性", ""]
    return "\n".join(lines)


def source_note(source, result):
    s = source
    lines = ["---", "type: paper" if s["kind"] == "paper" else "type: standard", "status: agent-draft",
             "tags: [paper, cloud-seeding]", "---", "", f"# {s['title']}", "", "## 引用信息", "",
             f"- 作者：{'；'.join(s['authors']) or '未核实'}", f"- 年份：{s['year']}", f"- 出版信息：{s['venue']}",
             f"- DOI：{s['doi'] or '未报告'}", f"- 来源：{s['url'] or '本地用户资料'}", f"- 阅读范围：{s['reading_scope']}", ""]
    paper = next(p for p in result["analysis"]["papers"] if p["source_id"] == s["id"])
    lines += ["## 任务与方法", "", paper["task"], "", paper["data"], "", paper["method"], "", "## 主要发现", ""]
    lines += [f"- {c['text']} {citations(c)}" for c in paper["findings"]]
    lines += ["", "## 局限和待核实项", ""] + [f"- {c['text']} {citations(c)}" for c in paper["limitations"]]
    for evidence in result["evidence"]:
        if evidence["source_id"] == s["id"]:
            lines += ["", f"## 证据 {evidence['id']}", "", f"位置：{evidence['location']}；材料类型：{evidence['provenance']}", "", evidence["text"]]
    return "\n".join(lines) + "\n"


def report(result):
    m = result["meta"]
    mode = "真实HelloAgents模型调用" if m["mode"] == "live" else "离线手写示例（未调用模型）"
    lines = ["# 人工增雨科研选题报告", "", f"研究问题：{m['topic']}", "", f"资源条件：{m['resources']}", "",
             f"运行方式：{mode}；模型：{m['model']}；时间：{m['generated_at']}", "",
             "> 本报告用于文献研究和实验规划，不提供实际作业决策。证据ID校验只检查来源存在，不保证语义支持；候选选题尚需全文核验和相似工作检索。", "",
             matrix(result)]
    for idea in result["ideas"]["ideas"]:
        lines += [topic_note(idea, result)]
    lines += ["## 审查意见", "", result["review"]["verdict"], ""]
    for check in result["review"]["checks"]:
        lines += [f"- **{check['item']}**（{check['status']}）：{check['detail']} {citations(check)}"]
    lines += ["", "## 下一步检索", ""] + [f"- {q}" for q in result["review"]["next_searches"]]
    lines += ["", "## 来源与证据", ""]
    for s in result["sources"]:
        title = s["title"]
        link = f"[{title}]({s['url']})" if s["url"] else title
        lines += [f"### {s['id']} · {link}", "", f"阅读范围：{s['reading_scope']}", ""]
        for e in result["evidence"]:
            if e["source_id"] == s["id"]:
                lines += [f"- **{e['id']}** · {e['location']} · {e['provenance']}：{e['text']}"]
        lines.append("")
    lines += ["## 运行记录", "", "| Agent | 模式 | 模型尝试次数 | 耗时（秒） |", "| --- | --- | ---: | ---: |"]
    lines += [f"| {t['agent']} | {t['mode']} | {t['attempts']} | {t['elapsed_seconds']} |" for t in result["trace"]]
    return "\n".join(lines) + "\n"


def export_files(result):
    files = {"report.md": report(result), "result.json": json.dumps(result, ensure_ascii=False, indent=2),
             "references.bib": bibliography(result["sources"]), "comparison.md": matrix(result),
             "obsidian/01_Sources/论文对比矩阵.md": matrix(result)}
    for s in result["sources"]:
        files[f"obsidian/01_Sources/Papers/{s['id']}.md"] = source_note(s, result)
    for idea in result["ideas"]["ideas"]:
        files[f"obsidian/03_Topics/Topic Pool/{idea['id']}.md"] = topic_note(idea, result)
    return files


def zip_bytes(result):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in export_files(result).items():
            archive.writestr(name, text.encode("utf-8"))
    return buffer.getvalue()


def save_result(result, destination, vault=None):
    destination = Path(destination).resolve()
    files = export_files(result)
    destination.mkdir(parents=True, exist_ok=False)
    for name, text in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if vault:
        vault = Path(vault).expanduser().resolve()
        if not vault.is_dir():
            raise ValueError("Obsidian知识库目录不存在；报告已保存到输出目录。")
        # New batch folder avoids replacing existing hand-written notes.
        batch = vault / "00_Inbox" / ("CloudSeed-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        batch.mkdir(parents=True, exist_ok=False)
        for name, text in files.items():
            if name.startswith("obsidian/"):
                path = batch / name.removeprefix("obsidian/")
                path.parent.mkdir(parents=True, exist_ok=True)
                # Resolve links to this batch even after multiple exports into one vault.
                for source in result["sources"]:
                    target = (batch / "01_Sources/Papers" / source["id"]).relative_to(vault).as_posix()
                    text = text.replace(f"[[{source['id']}]]", f"[[{target}|{source['id']}]]")
                path.write_text(text, encoding="utf-8")
        return destination, batch
    return destination, None
