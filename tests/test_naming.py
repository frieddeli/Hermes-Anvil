from hermes_anvil.gcp.naming import (
    firewall_rule_name,
    instance_name,
    project_id,
    public_firewall_rule_name,
    random_suffix,
    secret_name,
    service_account_email,
    service_account_id,
    slugify,
)


def test_slugify():
    # Mixed case
    assert slugify("SomeMixedCase") == "somemixedcase"

    # Punctuation and repeated separators
    assert slugify("hello...world!!!") == "hello-world"
    assert slugify("a_b@c#d$e") == "a-b-c-d-e"

    # Leading/trailing punctuation
    assert slugify("---leading-and-trailing---") == "leading-and-trailing"

    # Empty-string fallback to "agent"
    assert slugify("") == "agent"
    assert slugify("!!!") == "agent"

    # Truncation at SLUG_MAX_LEN (20 chars), with no trailing hyphen left
    # even if the raw slice lands exactly on a hyphen boundary.
    long_name = "this-is-a-very-long-name-that-should-be-truncated"
    assert slugify(long_name) == "this-is-a-very-long"
    assert len(slugify(long_name)) == 19
    assert not slugify(long_name).endswith("-")


def test_random_suffix():
    suf = random_suffix()
    assert len(suf) == 4
    assert suf.isalnum()
    assert len(random_suffix(6)) == 6


def test_project_id():
    pid = project_id("myslug", "1234")
    assert pid == "hermes-anvil-myslug-1234"
    assert len(pid) <= 30

    long_pid = project_id("a" * 20, "b" * 10)
    assert long_pid.startswith("hermes-anvil-")
    assert len(long_pid) <= 30
    assert not long_pid.endswith("-")
    # The suffix must survive truncation, not just the prefix -- a bug
    # here previously let a long slug silently eat the whole 30-char
    # budget, dropping the suffix entirely and making every collision
    # retry in bootstrap.ensure_project produce an identical ID.
    assert long_pid.endswith("-bbbbbbbbbb")


def test_project_id_suffix_always_survives_realistic_long_slugs():
    # SLUG_MAX_LEN allows slugs up to 20 chars (e.g. "the-great-destroyer",
    # a perfectly plausible user-chosen agent name) -- with the
    # default 4-char suffix, the suffix must never be truncated away.
    long_slug = "the-great-destroyer"  # 19 chars
    assert len(long_slug) > 12  # more than the old, unreserved budget

    id_a = project_id(long_slug, suffix="aaaa")
    id_b = project_id(long_slug, suffix="bbbb")

    assert id_a.endswith("-aaaa")
    assert id_b.endswith("-bbbb")
    assert id_a != id_b  # a new suffix must actually change the ID
    assert len(id_a) <= 30 and len(id_b) <= 30


def test_instance_name():
    name = instance_name("myslug")
    assert name == "hermes-vm-myslug"

    long_name = instance_name("a" * 100)
    assert long_name.startswith("hermes-vm-")
    assert len(long_name) <= 63


def test_service_account_id():
    sa = service_account_id("myslug")
    assert sa == "hermes-vm-myslug"
    assert len(sa) <= 30

    long_sa = service_account_id("a" * 50)
    assert long_sa.startswith("hermes-vm-")
    assert len(long_sa) <= 30
    assert not long_sa.endswith("-")


def test_service_account_email():
    email = service_account_email("myslug", "myproject")
    assert email == "hermes-vm-myslug@myproject.iam.gserviceaccount.com"


def test_firewall_rule_name():
    name = firewall_rule_name("myslug")
    assert name == "allow-iap-ssh-myslug"

    long_name = firewall_rule_name("a" * 100)
    assert long_name.startswith("allow-iap-ssh-")
    assert len(long_name) <= 63


def test_public_firewall_rule_name():
    name = public_firewall_rule_name("myslug")
    assert name == "allow-public-ssh-myslug"

    long_name = public_firewall_rule_name("a" * 100)
    assert long_name.startswith("allow-public-ssh-")
    assert len(long_name) <= 63


def test_secret_name():
    name = secret_name("myslug")
    assert name == "hermes-agent-key-myslug"

    long_name = secret_name("a" * 300)
    assert long_name.startswith("hermes-agent-key-")
    assert len(long_name) <= 255
