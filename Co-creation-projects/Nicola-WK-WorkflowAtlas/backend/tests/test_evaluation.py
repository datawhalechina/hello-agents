from evaluation.run import evaluate


def test_controlled_fixture_gold_labels_and_evidence():
    report = evaluate()
    assert report["messages"] == 29 and report["stage_count"] == 6
    assert report["work_classification"]["f1"] == 1
    assert report["atomic_fact_fields"]["f1"] == 1
    assert report["explicit_relations"]["f1"] == 1
    assert report["evidence_integrity"]["ratio"] == 1
    assert report["unassigned_facts"] == 1
    assert "synthetic" in report["scope"]
