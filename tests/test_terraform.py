"""Static checks on the Terraform: it parses, and the security-relevant choices are present."""

from pathlib import Path

import hcl2

TF = Path(__file__).parent.parent / "deploy" / "terraform"


def _load() -> dict:
    merged: dict = {}
    for f in sorted(TF.glob("*.tf")):
        with f.open() as fh:
            for k, v in hcl2.load(fh).items():
                merged.setdefault(k, []).extend(v if isinstance(v, list) else [v])
    return merged


def test_all_terraform_files_parse():
    assert _load().get("resource")


def test_every_variable_used_is_declared():
    text = "\n".join(f.read_text() for f in TF.glob("*.tf"))
    declared = {next(iter(v)).strip('"') for v in _load()["variable"]}
    import re

    used = set(re.findall(r"\bvar\.(\w+)", text))
    assert used <= declared, used - declared


def test_service_is_private_by_default_and_roles_are_minimal():
    text = (TF / "main.tf").read_text()
    assert "allUsers" not in text and "allAuthenticatedUsers" not in text
    roles = {r for r in ("roles/owner", "roles/editor", "roles/admin") if r in text}
    assert not roles
    assert "roles/aiplatform.user" in text and "roles/cloudsql.client" in text


def test_secrets_use_secret_manager_not_plain_env():
    text = (TF / "main.tf").read_text()
    assert "secret_key_ref" in text and text.count("random_password") >= 2
