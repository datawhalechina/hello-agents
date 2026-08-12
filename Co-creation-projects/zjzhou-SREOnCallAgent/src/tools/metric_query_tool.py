from typing import Dict, Any


class MetricQueryTool:
    """
    Queries simulated time-series metrics for the incident's service.

    Input to run(): a metric name substring (e.g. 'db_pool', 'latency', 'memory')
    Returns: time-series data as a formatted string
    """

    name = "metric_query"
    description = (
        "Query time-series metrics for the incident service. "
        "Input: a metric name or keyword (e.g. 'db_pool', 'memory', 'latency', 'error_rate'). "
        "Returns time-series values showing how the metric changed over time."
    )

    def __init__(self, incident_data: Dict[str, Any]):
        self.metrics: Dict[str, Dict] = incident_data.get("metrics", {})
        self.service: str = incident_data.get("service", "unknown")

    def run(self, metric_name: str) -> str:
        query = metric_name.lower().strip()
        matched = {k: v for k, v in self.metrics.items() if query in k.lower()}

        if not matched:
            available = ", ".join(self.metrics.keys())
            return (
                f"No metrics found matching '{metric_name}' for {self.service}.\n"
                f"Available metrics: {available}"
            )

        lines = [f"Metrics for {self.service} matching '{metric_name}':"]
        for name, values in matched.items():
            series = " | ".join(f"{t}: {v}" for t, v in sorted(values.items()))
            lines.append(f"  {name}: [{series}]")
        return "\n".join(lines)
