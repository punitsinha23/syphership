
import subprocess

import pytest

import services.repository_service as repository_service


def test_clone_repository_checks_out_requested_commit(tmp_path, monkeypatch):
    # Create a fake Git repository locally.
    source = tmp_path / "source"
    source.mkdir()

    subprocess.run(["git", "init", str(source)], check=True)
    subprocess.run(
        ["git", "-C", str(source), "config", "user.name", "Test User"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(source), "config", "user.email", "test@example.com"],
        check=True,
    )

    # Create the first commit.
    (source / "app.txt").write_text("version 1")
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(source), "commit", "-m", "first commit"],
        check=True,
    )
    first_commit = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        text=True,
    ).strip()

    # Create a second commit so we can verify checkout behavior.
    (source / "app.txt").write_text("version 2")
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(source), "commit", "-m", "second commit"],
        check=True,
    )

    # Point the service's clone root at our temporary test directory.
    monkeypatch.setattr(repository_service, "DEPLOYMENT_ROOT", tmp_path / "deployments")
    
    # Clone locally and request the first commit.
    result = repository_service.clone_repository(
        repo_url=str(source),
        commit_sha=first_commit,
        deployment_id=1,
    )


    assert (result / "app.txt").read_text() == "version 1"
    assert subprocess.check_output(
        ["git", "-C", str(result), "rev-parse", "HEAD"],
        text=True,
    ).strip() == first_commit
