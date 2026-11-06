import pytest
from fastapi import HTTPException

import github.service
from services.repository_service import clone_repository
from services.validation import is_valid_branch, is_valid_sha, scrub

SHA = "a1b2c3d4" * 5


def test_valid_sha_passes():
    assert is_valid_sha(SHA) is True


@pytest.mark.parametrize(
    "sha",
    [
        "",
        None,
        "abc123",  # too short
        SHA + "0",  # too long
        SHA.upper(),
        "-" + SHA[1:],  # git would read this as an option
        "g" * 40,  # not hex
        SHA[:-1] + "\n",
        SHA + "\n",
    ],
)
def test_invalid_sha_fails(sha):
    assert is_valid_sha(sha) is False


@pytest.mark.parametrize("branch", ["main", "master", "feature/login", "release-1.2", "fix_bug"])
def test_valid_branch_passes(branch):
    assert is_valid_branch(branch) is True


@pytest.mark.parametrize(
    "branch",
    ["", None, "-x", "--upload-pack=evil", "a..b", "a b", "a\nb", "a~1", "a^", "a:b", "a?", "a*", "a[b", "a\\b"],
)
def test_invalid_branch_fails(branch):
    assert is_valid_branch(branch) is False


def test_clone_rejects_option_shaped_sha():
    with pytest.raises(ValueError, match="Invalid commit SHA"):
        clone_repository("https://github.com/octo/app.git", "--orphan=evil" + "a" * 28, 1, "token")


def test_repo_config_rejects_bad_branch(monkeypatch):
    calls = []

    def fake_get(path, token, params=None):
        calls.append(path)
        return {"default_branch": "main", "full_name": "octo/app"}

    monkeypatch.setattr(github.service, "github_get", fake_get)

    with pytest.raises(HTTPException) as error:
        github.service.fetch_repo_config("token", "octo/app", "-bad")

    assert error.value.status_code == 422
    assert calls == ["/repos/octo/app"]  # The branch never reached GitHub.


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (("clone failed for abc123", "abc123"), "clone failed for ***"),
        (("a tok1 b tok2", "tok1", "tok2"), "a *** b ***"),
        (("token ghp_AbC123xyz here",), "token *** here"),
        (("gho_x ghs_y github_pat_11ABC_def",), "*** *** ***"),
        (("hello", ""), "hello"),  # replace("") would put *** between every character
        (("hello", None), "hello"),
        (("plain",), "plain"),
        ((None,), None),
        (("",), ""),
    ],
)
def test_scrub(args, expected):
    assert scrub(*args) == expected


def test_repo_config_rejects_huge_repo(monkeypatch):
    monkeypatch.setattr(
        github.service,
        "github_get",
        lambda path, token, params=None: {"size": github.service.MAX_REPO_SIZE_KB + 1, "default_branch": "main"},
    )

    with pytest.raises(HTTPException) as error:
        github.service.fetch_repo_config("token", "octo/app", "main")

    assert error.value.status_code == 422
