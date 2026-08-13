"""Application service joining canonical facts, version overlays, and exporters."""

from uuid import UUID

from resume_agent.application.ports import FactBaseRepository, VersionRepository
from resume_agent.rendering.exporters import ExportedFile, RenderFormat, ResumeExporter
from resume_agent.rendering.models import RenderedResume
from resume_agent.rendering.renderer import ResumeRenderer


class ResumeRenderService:
    def __init__(
        self,
        fact_bases: FactBaseRepository,
        versions: VersionRepository,
        renderer: ResumeRenderer,
        exporter: ResumeExporter,
    ) -> None:
        self.fact_bases = fact_bases
        self.versions = versions
        self.renderer = renderer
        self.exporter = exporter

    def preview(self, version_id: UUID) -> RenderedResume:
        version = self.versions.get(version_id)
        base = self.fact_bases.get(version.fact_base_id)
        return self.renderer.render(base, version)

    def export(self, version_id: UUID, format: RenderFormat) -> ExportedFile:
        return self.exporter.export(self.preview(version_id), format)
