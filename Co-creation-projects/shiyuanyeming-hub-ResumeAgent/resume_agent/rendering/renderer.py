"""Pure, evidence-only resume rendering."""

from __future__ import annotations

import html
import re
from collections.abc import Iterable

from resume_agent.domain.models import (
    CareerFactBase,
    ConfidenceStatus,
    Experience,
    QualityDimension,
    ResumeVersion,
)
from resume_agent.rendering.models import (
    RenderedExperience,
    RenderedResume,
    RenderWarning,
)
from resume_agent.rendering.styles import default_style, get_theme


DIMENSION_ORDER = (
    QualityDimension.ACTION,
    QualityDimension.METHOD,
    QualityDimension.RESULT,
    QualityDimension.RESPONSIBILITY,
    QualityDimension.CONTEXT,
    QualityDimension.EVIDENCE,
)

COPY = {
    "zh": {
        "title": "简历",
        "experience": "工作经历",
        "skills": "技能",
        "summary": "职业概述",
        "target": "求职意向",
        "present": "至今",
    },
    "en": {
        "title": "Resume",
        "experience": "Experience",
        "skills": "Skills",
        "summary": "Summary",
        "target": "Target Role",
        "present": "Present",
    },
    "ja": {
        "title": "職務経歴書",
        "experience": "職務経歴",
        "skills": "活かせるスキル",
        "summary": "職務要約",
        "target": "希望職種",
        "present": "現在",
    },
}


class ResumeRenderer:
    def render(
        self,
        base: CareerFactBase,
        version: ResumeVersion,
    ) -> RenderedResume:
        if base.id != version.fact_base_id:
            raise ValueError("version does not belong to fact base")
        if version.locale not in COPY:
            raise ValueError(f"unsupported locale: {version.locale}")

        style = version.styles.get(version.locale) or default_style(version.locale)
        theme = get_theme(version.locale, style)
        experiences, has_estimates = self._resolve_experiences(base, version)
        skills = self._collect_skills(base, version)
        warnings = self._warnings(base, version, experiences, has_estimates)
        candidate_name = base.profile.name or self._candidate_fallback(version.locale)
        headline = version.target_role or base.target.role or version.name
        contact_line = " · ".join(
            value
            for value in (
                base.profile.email,
                base.profile.phone,
                base.profile.location,
                *base.profile.links,
            )
            if value
        )
        summary = self._summary(version.locale, headline, len(experiences))
        filename_stem = self._filename_stem(version.name, version.locale)
        markdown = self._markdown(
            version.locale,
            candidate_name,
            headline,
            contact_line,
            summary,
            experiences,
            skills,
        )
        rendered_html = self._html(
            version.locale,
            theme,
            candidate_name,
            headline,
            contact_line,
            summary,
            experiences,
            skills,
        )
        return RenderedResume(
            version_id=version.id,
            base_revision=base.revision,
            version_base_revision=version.base_revision,
            locale=version.locale,
            style=style,
            title=COPY[version.locale]["title"],
            filename_stem=filename_stem,
            candidate_name=candidate_name,
            headline=headline,
            contact_line=contact_line,
            summary=summary,
            experiences=experiences,
            skills=skills,
            markdown=markdown,
            html=rendered_html,
            warnings=warnings,
        )

    def _resolve_experiences(
        self,
        base: CareerFactBase,
        version: ResumeVersion,
    ) -> tuple[list[RenderedExperience], bool]:
        by_id = {experience.id: experience for experience in base.experiences}
        unknown = set(version.selected_experience_ids) - set(by_id)
        if unknown:
            raise ValueError(
                "unknown experience references: "
                + ", ".join(sorted(str(item) for item in unknown))
            )
        selected = set(version.selected_experience_ids)
        ordered_ids = [item for item in version.ordering if item in selected]
        ordered_ids.extend(
            item for item in version.selected_experience_ids if item not in ordered_ids
        )
        rendered = []
        has_estimates = False
        for experience_id in ordered_ids:
            experience = by_id[experience_id]
            bullets, experience_has_estimates = self._bullets(experience)
            has_estimates = has_estimates or experience_has_estimates
            rendered.append(
                RenderedExperience(
                    organization=experience.organization,
                    role=experience.role,
                    period=self._period(
                        experience.start,
                        experience.end,
                        version.locale,
                    ),
                    bullets=bullets,
                )
            )
        return rendered, has_estimates

    @staticmethod
    def _bullets(experience: Experience) -> tuple[list[str], bool]:
        bullets: list[str] = []
        seen = set()
        has_estimates = False
        for dimension in DIMENSION_ORDER:
            for value in experience.statements.get(dimension, []):
                if value.confidence is ConfidenceStatus.UNVERIFIED:
                    continue
                has_estimates = (
                    has_estimates or value.confidence is ConfidenceStatus.ESTIMATED
                )
                if value.text not in seen:
                    seen.add(value.text)
                    bullets.append(value.text)
        return bullets, has_estimates

    @staticmethod
    def _collect_skills(
        base: CareerFactBase,
        version: ResumeVersion,
    ) -> list[str]:
        by_id = {experience.id: experience for experience in base.experiences}
        skills: list[str] = []
        seen = set()
        for experience_id in version.selected_experience_ids:
            experience = by_id.get(experience_id)
            if experience is None:
                continue
            for skill in experience.linked_skills:
                normalized = skill.strip()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    skills.append(normalized)
        return skills

    @staticmethod
    def _warnings(
        base: CareerFactBase,
        version: ResumeVersion,
        experiences: list[RenderedExperience],
        has_estimates: bool,
    ) -> list[RenderWarning]:
        warnings = []
        if not base.profile.name or not base.profile.email or not base.profile.phone:
            warnings.append(
                RenderWarning(
                    code="missing_profile",
                    message="姓名、邮箱或电话尚未补全，导出前建议完善基本信息。",
                )
            )
        if has_estimates:
            warnings.append(
                RenderWarning(
                    code="estimated_evidence",
                    message="简历包含估算信息，请在投递前再次核对。",
                )
            )
        if version.base_revision != base.revision:
            warnings.append(
                RenderWarning(
                    code="stale_version",
                    message="证据档案已有更新，这个投递版本尚未刷新。",
                )
            )
        if not experiences or not any(item.bullets for item in experiences):
            warnings.append(
                RenderWarning(
                    code="empty_evidence",
                    message="当前版本没有可写入简历的已确认经历证据。",
                )
            )
        return warnings

    @staticmethod
    def _summary(locale: str, headline: str, count: int) -> str:
        if locale == "en":
            return f"Target role: {headline}. Evidence selected from {count} experience(s)."
        if locale == "ja":
            return f"希望職種：{headline}。確認済みの職務経験 {count} 件を掲載しています。"
        return f"目标岗位：{headline}。以下内容来自 {count} 段已确认经历。"

    @staticmethod
    def _candidate_fallback(locale: str) -> str:
        return {"zh": "候选人", "en": "Candidate", "ja": "候補者"}[locale]

    @staticmethod
    def _period(start: str, end: str, locale: str) -> str:
        if not start and not end:
            return ""
        normalized_start = start.replace("-", ".") if start else ""
        normalized_end = end.replace("-", ".") if end else COPY[locale]["present"]
        return f"{normalized_start} – {normalized_end}".strip()

    @staticmethod
    def _filename_stem(name: str, locale: str) -> str:
        normalized = re.sub(r"[^\w\u3400-\u9fff-]+", "_", name, flags=re.UNICODE)
        normalized = normalized.strip("_-") or "resume"
        return f"{normalized}_{locale}"

    @staticmethod
    def _markdown_escape(value: str) -> str:
        escaped = value.replace("\\", "\\\\")
        for marker in ("*", "_", "`", "[", "]", "#"):
            escaped = escaped.replace(marker, f"\\{marker}")
        return escaped

    def _markdown(
        self,
        locale: str,
        candidate_name: str,
        headline: str,
        contact_line: str,
        summary: str,
        experiences: Iterable[RenderedExperience],
        skills: list[str],
    ) -> str:
        copy = COPY[locale]
        lines = [f"# {self._markdown_escape(candidate_name)}", ""]
        if headline:
            lines.extend(
                [f"**{copy['target']}：** {self._markdown_escape(headline)}", ""]
            )
        if contact_line:
            lines.extend([self._markdown_escape(contact_line), ""])
        lines.extend([f"## {copy['summary']}", "", self._markdown_escape(summary), ""])
        lines.extend([f"## {copy['experience']}", ""])
        for experience in experiences:
            heading = f"{experience.role} — {experience.organization}"
            if experience.period:
                heading += f" | {experience.period}"
            lines.extend([f"### {self._markdown_escape(heading)}", ""])
            lines.extend(f"- {self._markdown_escape(item)}" for item in experience.bullets)
            lines.append("")
        if skills:
            lines.extend(
                [
                    f"## {copy['skills']}",
                    "",
                    " · ".join(self._markdown_escape(item) for item in skills),
                    "",
                ]
            )
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _html(
        locale,
        theme,
        candidate_name,
        headline,
        contact_line,
        summary,
        experiences,
        skills,
    ) -> str:
        copy = COPY[locale]
        escape = lambda value: html.escape(value, quote=True)
        experience_html = []
        for experience in experiences:
            meta = " · ".join(
                value
                for value in (experience.organization, experience.period)
                if value
            )
            bullets = "".join(f"<li>{escape(item)}</li>" for item in experience.bullets)
            experience_html.append(
                f'<section class="experience"><h3>{escape(experience.role)}</h3>'
                f'<p class="meta">{escape(meta)}</p><ul>{bullets}</ul></section>'
            )
        skills_html = "".join(f'<span class="skill">{escape(item)}</span>' for item in skills)
        css = f"""
        :root {{--accent:{theme.accent};--secondary:{theme.secondary};--tint:{theme.tint};--border:{theme.border};}}
        @page {{ size: A4; margin: 14mm 16mm; }}
        * {{ box-sizing: border-box; }}
        body {{ font-family:{theme.font_family}; color:#1f2937; font-size:10pt; line-height:1.58; margin:0; }}
        header {{ border-bottom:2.2pt solid var(--accent); padding-bottom:3mm; margin-bottom:5mm; }}
        h1 {{ color:var(--accent); font-size:21pt; margin:0; letter-spacing:.4px; }}
        .headline {{ color:var(--secondary); font-size:10.5pt; margin:1mm 0; }}
        .contact,.meta {{ color:#5f6772; font-size:9pt; margin:.8mm 0; }}
        h2 {{ color:var(--accent); font-size:11.5pt; border-left:3.5pt solid var(--accent); padding-left:2.5mm; margin:5mm 0 2mm; }}
        h3 {{ font-size:10.5pt; margin:2.5mm 0 .5mm; color:#20252b; }}
        p {{ margin:1mm 0; }}
        ul {{ margin:1mm 0 2mm; padding-left:5mm; }}
        li {{ margin:.7mm 0; }}
        li::marker {{ color:var(--accent); }}
        .skill {{ display:inline-block; background:var(--tint); border:.5pt solid var(--border); border-radius:2.5mm; padding:.5mm 2.2mm; margin:.5mm; color:var(--accent); font-size:9pt; }}
        """
        contact = f'<p class="contact">{escape(contact_line)}</p>' if contact_line else ""
        skills_section = (
            f"<h2>{copy['skills']}</h2><div>{skills_html}</div>" if skills else ""
        )
        body = (
            f'<header><h1>{escape(candidate_name)}</h1>'
            f'<p class="headline">{escape(copy["target"])}：{escape(headline)}</p>'
            f"{contact}</header>"
            f'<h2>{copy["summary"]}</h2><p>{escape(summary)}</p>'
            f'<h2>{copy["experience"]}</h2>{"".join(experience_html)}'
            f"{skills_section}"
        )
        return (
            "<!DOCTYPE html>\n"
            f'<html lang="{locale}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{escape(copy["title"])}</title><style>{css}</style></head>'
            f"<body>{body}</body></html>"
        )
