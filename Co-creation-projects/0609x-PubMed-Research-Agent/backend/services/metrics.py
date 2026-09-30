"""Small, dependency-free Prometheus metrics used by the API process."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


HISTOGRAM_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


@dataclass
class _RequestSeries:
    count: int = 0
    duration_sum: float = 0.0
    bucket_counts: list[int] = field(
        default_factory=lambda: [0] * len(HISTOGRAM_BUCKETS)
    )


class RequestMetrics:
    """Thread-safe request counters with normalized route labels."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._series: dict[tuple[str, str, int], _RequestSeries] = {}

    def observe(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        key = (method.upper(), route, status_code)
        with self._lock:
            series = self._series.setdefault(key, _RequestSeries())
            series.count += 1
            series.duration_sum += duration_seconds
            for index, boundary in enumerate(HISTOGRAM_BUCKETS):
                if duration_seconds <= boundary:
                    series.bucket_counts[index] += 1

    def render(
        self,
        *,
        job_counts: dict[str, int],
        oldest_queued_age_seconds: float,
        stale_running_jobs: int,
    ) -> str:
        with self._lock:
            snapshot = {
                key: _RequestSeries(
                    count=value.count,
                    duration_sum=value.duration_sum,
                    bucket_counts=value.bucket_counts.copy(),
                )
                for key, value in self._series.items()
            }

        lines = [
            "# HELP pubmed_http_requests_total Total HTTP requests handled by the API.",
            "# TYPE pubmed_http_requests_total counter",
        ]
        for (method, route, status_code), series in sorted(snapshot.items()):
            labels = (
                f'method="{_escape_label(method)}",'
                f'route="{_escape_label(route)}",status="{status_code}"'
            )
            lines.append(f"pubmed_http_requests_total{{{labels}}} {series.count}")

        lines.extend(
            [
                "# HELP pubmed_http_request_duration_seconds HTTP request duration.",
                "# TYPE pubmed_http_request_duration_seconds histogram",
            ]
        )
        for (method, route, status_code), series in sorted(snapshot.items()):
            labels = (
                f'method="{_escape_label(method)}",'
                f'route="{_escape_label(route)}",status="{status_code}"'
            )
            for boundary, count in zip(HISTOGRAM_BUCKETS, series.bucket_counts):
                lines.append(
                    "pubmed_http_request_duration_seconds_bucket"
                    f'{{{labels},le="{boundary:g}"}} {count}'
                )
            lines.append(
                "pubmed_http_request_duration_seconds_bucket"
                f'{{{labels},le="+Inf"}} {series.count}'
            )
            lines.append(
                f"pubmed_http_request_duration_seconds_sum{{{labels}}} "
                f"{series.duration_sum:.9f}"
            )
            lines.append(
                f"pubmed_http_request_duration_seconds_count{{{labels}}} {series.count}"
            )

        lines.extend(
            [
                "# HELP pubmed_search_jobs_current Current persisted search jobs by status.",
                "# TYPE pubmed_search_jobs_current gauge",
            ]
        )
        expected_statuses = {
            "queued",
            "running",
            "completed",
            "partial",
            "failed",
            "cancelled",
        }
        for status in sorted(expected_statuses | set(job_counts)):
            lines.append(
                "pubmed_search_jobs_current"
                f'{{status="{_escape_label(status)}"}} {job_counts.get(status, 0)}'
            )

        lines.extend(
            [
                "# HELP pubmed_search_oldest_queued_age_seconds Age of the oldest queued job.",
                "# TYPE pubmed_search_oldest_queued_age_seconds gauge",
                "pubmed_search_oldest_queued_age_seconds "
                f"{max(0.0, oldest_queued_age_seconds):.3f}",
                "# HELP pubmed_search_stale_running_jobs Running jobs with no recent progress.",
                "# TYPE pubmed_search_stale_running_jobs gauge",
                f"pubmed_search_stale_running_jobs {stale_running_jobs}",
            ]
        )
        return "\n".join(lines) + "\n"


request_metrics = RequestMetrics()
