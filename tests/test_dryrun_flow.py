import pytest
from hermes_anvil.dryrun.fakes import FailureInjection, FakeGcpToolRouter, FakeSecretWriter
from hermes_anvil.gcp import bootstrap, compute, identity, naming, network
from hermes_anvil.gcp.state import RunState

BILLING_ACCOUNT = "012345-ABCDEF"


async def test_full_dry_run_flow(tmp_path):
    router = FakeGcpToolRouter(latency=0)
    secret_writer = FakeSecretWriter()

    slug = naming.slugify("Athena")
    state = RunState.load_or_create(slug, "Athena", tmp_path)

    await bootstrap.ensure_project(router, state, billing_account=BILLING_ACCOUNT)
    assert state.project
    assert state.is_done("project_created")
    assert state.is_done("billing_linked")

    await bootstrap.enable_apis(router, state)
    assert state.is_done("apis_enabled")

    await identity.ensure_service_account(router, state)
    assert state.service_account_email
    assert state.is_done("service_account_created")

    await network.ensure_iap_firewall_rule(router, state)
    assert state.firewall_rule
    assert state.is_done("firewall_created")

    secret_id = secret_writer.write_api_key(state, "sk-test-123")
    assert state.secret_name == secret_id
    assert secret_writer.written[secret_id] == "sk-test-123"

    await identity.grant_secret_access(router, state, state.secret_name)
    assert state.is_done("secret_access_granted")

    await compute.provision_instance(router, state)
    assert state.instance_name
    assert state.is_done("instance_created")

    await compute.wait_for_running(router, state, poll_interval=0, timeout=5)
    assert state.is_done("instance_running")

    await router.close()

    # State survives a fresh load from disk -- what a resumed process would see.
    reloaded = RunState.load(slug, tmp_path)
    assert reloaded is not None
    assert reloaded.is_done("instance_running")


async def test_resume_after_injected_failure(tmp_path):
    slug = "resume-test"
    state = RunState.load_or_create(slug, "Resume Bot", tmp_path)

    failing_router = FakeGcpToolRouter(
        latency=0,
        failures=[FailureInjection(match="projects create", fail_times=1)],
    )
    with pytest.raises(RuntimeError):
        await bootstrap.ensure_project(failing_router, state, billing_account=BILLING_ACCOUNT)

    # The failure happened before ensure_project got to mark anything done --
    # simulate a fresh process resuming by reloading from disk.
    reloaded = RunState.load(slug, tmp_path)
    assert reloaded is not None
    assert not reloaded.is_done("project_created")

    # A resumed run against a healthy router should now succeed cleanly.
    healthy_router = FakeGcpToolRouter(latency=0)
    await bootstrap.ensure_project(healthy_router, reloaded, billing_account=BILLING_ACCOUNT)
    assert reloaded.is_done("project_created")
    assert reloaded.is_done("billing_linked")


async def test_ensure_project_resumes_against_existing_project(tmp_path):
    """If state already references a project that still exists, ensure_project
    must not try to create a new one."""
    router = FakeGcpToolRouter(latency=0)
    state = RunState.load_or_create("already-there", "Already There", tmp_path)

    first = await bootstrap.ensure_project(router, state, billing_account=BILLING_ACCOUNT)
    second = await bootstrap.ensure_project(router, state, billing_account=BILLING_ACCOUNT)

    assert first == second
    # Only one "projects create" call should have happened.
    create_calls = [c for c in router._call_log if c.startswith("projects create")]
    assert len(create_calls) == 1
