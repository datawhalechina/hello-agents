"""Source navigation must scope real persisted results without touching evidence."""
import json


def ingest(client, source_id, message_id, text):
    message = {"id": message_id, "source_id": source_id, "text": text, "timestamp": "2026-11-09T09:00:00+08:00", "sender": "Synthetic author"}
    response = client.post("/api/import", json={"source_id": source_id, "messages": [message]})
    assert response.status_code == 200


def test_source_scope_filters_shared_project_graph_facts_stats_and_export(client):
    ingest(client, "虚构/甲", "m1", "【虚构共用项目】[任务:甲接口] 开始接口开发")
    ingest(client, "虚构/乙", "m2", "【虚构共用项目】[任务:乙接口] 开始接口开发")
    ingest(client, "虚构/乙", "m3", "【虚构乙独有项目】[任务:验证] 开始测试")
    assert client.post("/api/process", json={}).json()["status"] == "completed"
    scope = {"source_id": "虚构/甲"}
    stats = client.get("/api/stats", params=scope).json()
    assert stats["messages"] == stats["facts"] == stats["projects"] == stats["nodes"] == 1
    projects = client.get("/api/projects", params=scope).json()
    assert len(projects) == 1 and projects[0]["name"] == "虚构共用项目"
    graph = client.get(f"/api/projects/{projects[0]['id']}/workflow", params=scope).json()
    assert len(graph["facts"]) == len(graph["nodes"]) == 1
    assert all(e["source_id"] == "虚构/甲" for f in graph["facts"] for e in f["evidence"])
    assert len(client.get("/api/facts", params=scope).json()) == 1
    exported = client.get("/api/export", params={**scope, "format": "json"}).json()
    assert len(exported["facts"]) == len(exported["nodes"]) == len(exported["projects"]) == 1
    jsonl = client.get("/api/export", params={**scope, "format": "jsonl"}).text.splitlines()
    assert len(jsonl) == 1 and json.loads(jsonl[0])["evidence"][0]["source_id"] == "虚构/甲"
    assert client.get("/api/export", params={**scope, "format": "training"}).text == ""
    historical = client.get(f"/api/projects/{projects[0]['id']}/workflow", params={**scope, "version": graph['version']}).json()
    assert historical == graph


def test_analysis_distinguishes_unassigned_and_unread_attachment_messages(client):
    ingest(client, "synthetic-input", "work", "明天安排测试")
    raw = {"message_id": "attachment", "msg_type": "image", "create_time": "1794190000000", "body": {"content": '{"image_key":"synthetic-key"}'}, "sender": {"id": "synthetic-author"}, "parent_id": "work"}
    response = client.post("/api/import/file", params={"source_id": "synthetic-input", "format": "jsonl"}, content=json.dumps(raw))
    assert response.status_code == 200
    client.post("/api/process", json={})
    report = client.get("/api/sources/analysis", params={"source_id": "synthetic-input"}).json()
    assert report["messages"] == 2 and report["attachment_messages"] == report["reply_messages"] == 1
    assert report["facts"] == report["unassigned_facts"] == report["extracted_messages"] == 1
    assert report["assigned_facts"] == report["projects"] == report["nodes"] == 0
    assert any("准确率" in note for note in report["notes"])
    assert client.get("/api/sources/analysis", params={"source_id": "missing"}).status_code == 404


def test_source_history_omits_versions_before_that_source_arrived(client):
    ingest(client, "source-before", "m1", "【虚构共享项目】[任务:设备] 开始设备测试")
    client.post("/api/process", json={})
    project = client.get("/api/projects").json()[0]
    before = client.get(f"/api/projects/{project['id']}/workflow").json()["version"]
    ingest(client, "source-after", "m2", "【虚构共享项目】[任务:接口] 开始接口测试")
    client.post("/api/process", json={})
    versions = client.get(f"/api/projects/{project['id']}/versions", params={"source_id": "source-after"}).json()
    assert versions and all(entry["version"] > before for entry in versions)
    for entry in versions:
        graph = client.get(f"/api/projects/{project['id']}/workflow", params={"source_id": "source-after", "version": entry['version']})
        assert graph.status_code == 200 and all(f["evidence"][0]["source_id"] == "source-after" for f in graph.json()["facts"])


def test_rebuild_prunes_empty_stale_project_but_preserves_old_snapshot(client):
    ingest(client, "synthetic", "m1", "【虚构旧项目】[任务:设备] 开始设备测试")
    client.post("/api/process", json={})
    repository = client.app.state.repository
    version, original = repository.latest()
    project_id = original.projects[0].id
    proposal = original.model_copy(deep=True)
    proposal.facts = []
    proposal.nodes = []
    proposal.edges = []
    repository.apply(proposal, {})
    assert repository.projects() == []
    assert repository.latest(version)[1].projects[0].id == project_id
