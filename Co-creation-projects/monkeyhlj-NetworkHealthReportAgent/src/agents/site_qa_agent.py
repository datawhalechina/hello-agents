from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from src.agents.base import BaseNetworkAgent


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"


class SiteQAAgent(BaseNetworkAgent):
    def __init__(self) -> None:
        prompt = (
            "你是企业网络运维全局问答助手。请优先根据给定的全局上下文回答。"
            "如果可以使用network_data工具，请调用工具核对数据后再回答。"
            "回答要简洁、专业、可执行。"
        )
        super().__init__(name="SiteQAAgent", system_prompt=prompt)

    def _build_prompt(
        self,
        question: str,
        context: Dict,
    ) -> str:
        return (
            "请回答用户关于企业网络健康的提问。"
            "\n\n[用户问题]\n"
            f"{question}"
            "\n\n[上下文JSON]\n"
            f"{json.dumps(context, ensure_ascii=False)}"
            "\n\n请用中文回答，输出结构：1)结论 2)关键证据 3)建议动作。"
        )

    def _looks_like_report_request(self, question: str) -> bool:
        q = question.lower()
        return any(keyword in q for keyword in ["生成", "导出", "下载", "报告", "周报", "一周", "近一周"])

    def _find_target_site(
        self,
        question: str,
        sites: List[Dict],
        selected_site_id: Optional[str] = None,
    ) -> Optional[Dict]:
        lowered = question.lower()
        for site in sites:
            site_id = str(site.get("site_id", "")).lower()
            site_name = str(site.get("site_name", "")).lower()
            city = str(site.get("city", "")).lower()
            province = str(site.get("province", "")).lower()
            if site_id and site_id in lowered:
                return site
            if site_name and site_name in lowered:
                return site
            if city and city in question:
                return site
            if province and province in question:
                return site

        candidates = re.findall(r"site[-_a-zA-Z0-9]+", lowered)
        for candidate in candidates:
            match = next((site for site in sites if str(site.get("site_id", "")).lower() == candidate), None)
            if match is not None:
                return match

        if selected_site_id:
            selected = next((site for site in sites if site.get("site_id") == selected_site_id), None)
            if selected is not None:
                return selected

        if len(sites) == 1 and self._looks_like_report_request(question):
            return sites[0]

        return None

    def _fallback_answer(
        self,
        question: str,
        sites: List[Dict],
        site_reports: List[Dict],
    ) -> str:
        q = question.strip().lower()
        if "几个site" in q or "多少site" in q or "多少个站点" in q:
            names = "、".join([s["site_name"] for s in sites])
            return f"当前共有 {len(sites)} 个 site，分别是：{names}。"

        if "上海" in question and ("site" in q or "站点" in question):
            sh_sites = [s for s in sites if s.get("city") == "上海" or s.get("province") == "上海市"]
            if not sh_sites:
                return "当前没有位于上海的 site。"
            details = "；".join([f"{s['site_name']}({s['site_id']})" for s in sh_sites])
            return f"上海相关 site 有 {len(sh_sites)} 个：{details}。"

        target = None
        for s in sites:
            if s["site_id"] in question or s["site_name"] in question or s.get("city", "") in question:
                target = s
                break

        if target:
            target_report = next((r for r in site_reports if r.get("site", {}).get("site_id") == target["site_id"]), None)
            if target_report:
                device = target_report.get("sections", {}).get("device_status", {})
                return (
                    f"{target['site_name']} 详细信息：城市{target.get('city')}，类型{target.get('site_type')}，"
                    f"关键等级{target.get('criticality')}。"
                    f"设备在线率{device.get('online_rate', 0) * 100:.2f}%，"
                    f"平均时延{device.get('avg_latency_ms', 0)}ms，"
                    f"平均丢包{device.get('avg_packet_loss', 0) * 100:.2f}%。"
                )

        levels = [r.get("health_level", "unknown") for r in site_reports]
        healthy = len([x for x in levels if x == "healthy"])
        warning = len([x for x in levels if x == "warning"])
        critical = len([x for x in levels if x == "critical"])
        return (
            f"全局概览：共{len(sites)}个site，healthy={healthy}，warning={warning}，critical={critical}。"
            "你可以继续问：上海有哪些site、某个site的详细信息、某个site的网络设备情况如何。"
        )

    def _summarize_report(self, report: Dict, question: str) -> Optional[str]:
        llm_prompt = (
            "你是企业网络健康报告的摘要撰写助手。"
            "请基于输入 JSON 生成一段中文摘要，适合直接放在报告首页。"
            "要求：简洁、专业、可执行，覆盖总体结论、主要风险、优先动作。"
            "如果用户问题里有明确的关注点，也要顺带回应。"
            "\n\n[用户问题]\n"
            f"{question}"
            "\n\n[报告JSON]\n"
            f"{json.dumps(report, ensure_ascii=False)}"
        )
        return self.run_llm(llm_prompt)

    def _build_report_markdown(
        self,
        site: Dict,
        report: Dict,
        question: str,
        summary: Optional[str],
    ) -> str:
        window = report.get("window", {})
        sections = report.get("sections", {})
        device = sections.get("device_status", {})
        user_status = sections.get("user_status", {})
        log_analysis = sections.get("log_analysis", {})
        recommendations = report.get("recommendations", [])

        lines = [
            f"# {site.get('site_name', site.get('site_id', 'site'))} 近一周网络健康报告",
            "",
            f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 统计窗口：{window.get('start_date', '')} 至 {window.get('end_date', '')}",
            f"- 站点编号：{site.get('site_id', '')}",
            f"- 站点城市：{site.get('city', '')}",
            f"- 健康评分：{report.get('health_score', 'N/A')}",
            f"- 健康等级：{report.get('health_level', 'N/A')}",
            "",
        ]

        if summary:
            lines.extend([
                "## 大模型摘要",
                summary.strip(),
                "",
            ])

        lines.extend([
            "## 核心指标",
            f"- 设备在线率：{device.get('online_rate', 0) * 100:.2f}%",
            f"- 平均时延：{device.get('avg_latency_ms', 0)} ms",
            f"- 平均丢包率：{device.get('avg_packet_loss', 0) * 100:.2f}%",
            f"- 终端合规率：{user_status.get('compliant_rate', 0) * 100:.2f}%",
            f"- 高风险终端数：{user_status.get('high_risk_terminals', 0)}",
            "",
            "## 日志分析",
            log_analysis.get("summary", "暂无日志摘要。"),
            "",
            "## 设备状态",
            device.get("summary", "暂无设备状态摘要。"),
            "",
            "## 用户状态",
            user_status.get("summary", "暂无用户状态摘要。"),
            "",
            "## 推荐动作",
        ])

        if recommendations:
            lines.extend([f"{idx + 1}. {item}" for idx, item in enumerate(recommendations)])
        else:
            lines.append("1. 继续观察站点运行状态，暂未发现明显风险。")

        lines.extend([
            "",
            "## 用户提问",
            question,
        ])
        return "\n".join(lines).strip() + "\n"

    def _save_report_artifact(self, site: Dict, start_date: str, end_date: str, content: str) -> Dict:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        safe_site_id = re.sub(r"[^0-9A-Za-z_-]+", "_", str(site.get("site_id", "site")))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_site_id}_{start_date}_{end_date}_{timestamp}.md"
        file_path = OUTPUT_DIR / filename
        file_path.write_text(content, encoding="utf-8")
        return {
            "file_name": filename,
            "file_path": str(file_path),
        }

    def _build_answer_payload(
        self,
        question: str,
        sites: List[Dict],
        site_reports: List[Dict],
        start_date: str,
        end_date: str,
        selected_site_id: Optional[str] = None,
    ) -> Dict:
        context = {
            "scope": "global",
            "window": {"start_date": start_date, "end_date": end_date},
            "site_count": len(sites),
            "sites": sites,
            "reports": site_reports,
            "selected_site_id": selected_site_id,
        }

        prompt = self._build_prompt(question=question, context=context)
        llm_answer: Optional[str] = self.run_llm(prompt)

        target_site = self._find_target_site(question, sites, selected_site_id=selected_site_id)
        is_report_request = self._looks_like_report_request(question)

        if is_report_request and target_site is not None:
            if not self.llm_enabled:
                return {
                    "answer": (
                        "检测到你在请求生成站点周报，但当前 LLM 未启用，无法按要求生成大模型报告。"
                        "请先在 .env 配置 LLM_API_KEY（或 OPENAI_API_KEY）后重试。"
                    ),
                    "artifact": None,
                    "debug": {
                        **self.debug_meta(),
                        "intent": "site_report_requires_llm",
                        "target_site_id": target_site.get("site_id"),
                    },
                }

            target_report = next((r for r in site_reports if r.get("site", {}).get("site_id") == target_site["site_id"]), None)
            if target_report is not None:
                report_summary = self._summarize_report(target_report, question)
                if not report_summary:
                    return {
                        "answer": (
                            "已识别到报告生成请求，但本次大模型调用失败，未生成周报文件。"
                            "请检查 LLM 配置和网络连通性后重试。"
                        ),
                        "artifact": None,
                        "debug": {
                            **self.debug_meta(),
                            "intent": "site_report_llm_failed",
                            "target_site_id": target_site.get("site_id"),
                        },
                    }
                answer_text = self._build_report_markdown(
                    site=target_site,
                    report=target_report,
                    question=question,
                    summary=report_summary,
                )
                artifact = self._save_report_artifact(target_site, start_date, end_date, answer_text)
                return {
                    "answer": answer_text,
                    "artifact": artifact,
                    "debug": {
                        **self.debug_meta(),
                        "intent": "site_report_export",
                        "target_site_id": target_site.get("site_id"),
                    },
                }

        answer_text = llm_answer or self._fallback_answer(question=question, sites=sites, site_reports=site_reports)
        return {
            "answer": answer_text,
            "artifact": None,
            "debug": {
                **self.debug_meta(),
                "intent": "general_qa",
                "target_site_id": target_site.get("site_id") if target_site else None,
            },
        }

    def answer_global(
        self,
        question: str,
        sites: List[Dict],
        site_reports: List[Dict],
        start_date: str,
        end_date: str,
    ) -> str:
        return self._build_answer_payload(
            question=question,
            sites=sites,
            site_reports=site_reports,
            start_date=start_date,
            end_date=end_date,
        )["answer"]

    def answer_global_payload(
        self,
        question: str,
        sites: List[Dict],
        site_reports: List[Dict],
        start_date: str,
        end_date: str,
        selected_site_id: Optional[str] = None,
    ) -> Dict:
        return self._build_answer_payload(
            question=question,
            sites=sites,
            site_reports=site_reports,
            start_date=start_date,
            end_date=end_date,
            selected_site_id=selected_site_id,
        )

    def debug_meta(self) -> Dict:
        return {
            "agent": "SiteQAAgent",
            "llm_enabled": self.llm_enabled,
            "mcp_enabled": self.mcp_enabled,
            "tools": self.list_tool_names(),
            "flow": [
                "collect_global_context",
                "build_prompt",
                "try_llm_or_stream",
                "fallback_if_needed",
            ],
        }

    def stream_answer_global(
        self,
        question: str,
        sites: List[Dict],
        site_reports: List[Dict],
        start_date: str,
        end_date: str,
        selected_site_id: Optional[str] = None,
    ) -> Iterator[str]:
        target_site = self._find_target_site(question, sites, selected_site_id=selected_site_id)
        if self._looks_like_report_request(question) and target_site is not None:
            payload = self._build_answer_payload(
                question=question,
                sites=sites,
                site_reports=site_reports,
                start_date=start_date,
                end_date=end_date,
                selected_site_id=selected_site_id,
            )
            yield payload["answer"]
            return

        context = {
            "scope": "global",
            "window": {"start_date": start_date, "end_date": end_date},
            "site_count": len(sites),
            "sites": sites,
            "reports": site_reports,
            "selected_site_id": selected_site_id,
        }
        prompt = self._build_prompt(question=question, context=context)
        stream_iter = self.stream_llm(prompt)
        if stream_iter is not None:
            try:
                for chunk in stream_iter:
                    yield chunk
                return
            except Exception:
                pass

        prompt = self._build_prompt(question=question, context=context)
        yield self.run_llm(prompt) or self._fallback_answer(question=question, sites=sites, site_reports=site_reports)
