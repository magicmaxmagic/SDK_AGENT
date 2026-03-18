from sdk_agent.web.tracker import InMemoryStatusTracker


def test_tracker_progress_is_clamped():
    tracker = InMemoryStatusTracker()

    low = tracker.update_agent("developer", "coding", -20, "bad low")
    low_progress = low.progress
    high = tracker.update_agent("developer", "coding", 120, "bad high")

    assert low_progress == 0
    assert high.progress == 100


def test_tracker_duplicate_run_id_rejected():
    tracker = InMemoryStatusTracker()
    tracker.start_run(request="first", run_id="run-1")

    try:
        tracker.start_run(request="second", run_id="run-1")
    except ValueError as exc:
        assert "run_id already exists" in str(exc)
    else:
        raise AssertionError("Expected ValueError on duplicate run_id")


def test_tracker_snapshot_timeline_limit():
    tracker = InMemoryStatusTracker()

    for i in range(250):
        tracker.update_agent("tester", f"stage-{i}", i, "step")

    snapshot = tracker.snapshot()
    assert len(snapshot["timeline"]) == 200
