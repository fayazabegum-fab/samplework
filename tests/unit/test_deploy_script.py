from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_infrastructure_preflight_never_runs_terraform_apply(tmp_path: Path) -> None:
    terraform_calls = tmp_path / "terraform-calls.txt"
    terraform_executable = tmp_path / "terraform"
    terraform_executable.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> "$TERRAFORM_CALLS"\n'
        'case " $* " in *" apply "*) exit 99 ;; esac\n',
        encoding="utf-8",
    )
    terraform_executable.chmod(0o755)
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "TERRAFORM_CALLS": str(terraform_calls),
    }

    subprocess.run(
        ["bash", str(REPOSITORY_ROOT / "scripts/deploy_infrastructure.sh"), "dev"],
        check=True,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert all("apply" not in call.split() for call in terraform_calls.read_text().splitlines())
