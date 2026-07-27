from hermes_anvil.gcp.state import RunState


def test_load_nonexistent(tmp_path):
    assert RunState.load("missing-slug", tmp_path) is None


def test_save_load_round_trip(tmp_path):
    state = RunState(slug="test-slug", agent_name="Agent Smith", project="matrix")
    state.save(tmp_path)

    loaded = RunState.load("test-slug", tmp_path)
    assert loaded is not None
    assert loaded.slug == "test-slug"
    assert loaded.agent_name == "Agent Smith"
    assert loaded.project == "matrix"
    assert loaded.completed_steps == []


def test_load_or_create(tmp_path):
    state = RunState.load_or_create("new-slug", "New Agent", tmp_path)
    assert state.slug == "new-slug"
    assert state.agent_name == "New Agent"

    # Existing state wins -- load_or_create must not clobber it with the
    # agent_name passed on a second call.
    state2 = RunState.load_or_create("new-slug", "Overwritten Agent", tmp_path)
    assert state2.slug == "new-slug"
    assert state2.agent_name == "New Agent"
    assert state2.agent_name != "Overwritten Agent"


def test_mark_done_and_is_done(tmp_path):
    state = RunState(slug="progress-slug")
    # mark_done()/save() with no args write to state._state_dir, which
    # defaults to the real global STATE_DIR -- bind it to tmp_path first
    # so this test never touches the developer's actual home directory.
    state._state_dir = tmp_path
    state.save()

    assert not state.is_done("step-1")
    state.mark_done("step-1")
    assert state.is_done("step-1")

    loaded = RunState.load("progress-slug", tmp_path)
    assert loaded is not None
    assert loaded.is_done("step-1")

    # Idempotent: marking the same step done twice doesn't duplicate it.
    state.mark_done("step-1")
    assert state.completed_steps.count("step-1") == 1

    loaded_again = RunState.load("progress-slug", tmp_path)
    assert loaded_again is not None
    assert loaded_again.completed_steps.count("step-1") == 1
