from pathlib import Path

from sdk_agent.core.persistence import StatePersistence
from sdk_agent.models import AutonomyLevel, FlowType, TrustProfile, WorkflowState


def test_persistence_save_and_load(tmp_path: Path) -> None:
    state = WorkflowState.create(
        flow=FlowType.FEATURE,
        request="Add auth",
        artifacts_path=tmp_path,
        autonomy_level=AutonomyLevel.IMPLEMENT,
        trust_profile=TrustProfile.NORMAL_INTERNAL,
    )
    state.changed_files = ["src/app.py"]

    persistence = StatePersistence(run_dir=tmp_path / state.run_id)
    persistence.save(state)
    loaded = persistence.load()

    assert loaded.run_id == state.run_id
    assert loaded.changed_files == ["src/app.py"]
