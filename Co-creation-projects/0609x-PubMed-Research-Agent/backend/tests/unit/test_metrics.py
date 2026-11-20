from __future__ import annotations

from backend.services.metrics import RequestMetrics


def test_request_metrics_render_prometheus_histogram_and_job_gauges():
    metrics = RequestMetrics()
    metrics.observe(
        method="get",
        route="/api/v1/search/jobs/{job_id}",
        status_code=200,
        duration_seconds=0.04,
    )

    rendered = metrics.render(
        job_counts={"queued": 2, "failed": 1},
        oldest_queued_age_seconds=12.5,
        stale_running_jobs=1,
    )

    assert (
        'pubmed_http_requests_total{method="GET",'
        'route="/api/v1/search/jobs/{job_id}",status="200"} 1'
    ) in rendered
    assert (
        'pubmed_http_request_duration_seconds_bucket{method="GET",'
        'route="/api/v1/search/jobs/{job_id}",status="200",le="0.05"} 1'
    ) in rendered
    assert 'pubmed_search_jobs_current{status="queued"} 2' in rendered
    assert "pubmed_search_oldest_queued_age_seconds 12.500" in rendered
    assert "pubmed_search_stale_running_jobs 1" in rendered
