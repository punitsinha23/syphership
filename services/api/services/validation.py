import re

COMMIT_SHA = re.compile(r"[0-9a-f]{40}")


# Characters git refuses in branch names (see `git check-ref-format`).
BAD_BRANCH_CHARS = re.compile(r"[\s~^:?*\[\\]")


def is_valid_sha(sha: str) -> bool:
    """True for a full 40-character lowercase hex commit SHA."""
    return isinstance(sha, str) and COMMIT_SHA.fullmatch(sha) is not None


def is_valid_branch(branch: str) -> bool:
    """True if git would accept this as a branch name.

    A leading "-" would make git read the name as an option."""
    if not isinstance(branch, str) or not branch or branch.startswith("-"):
        return False
    return ".." not in branch and BAD_BRANCH_CHARS.search(branch) is None


GITHUB_TOKEN = re.compile(r"gh[pousr]_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+")
def scrub(text: str | None, *secrets: str | None) -> str | None:
    """Replace the given secrets, and anything shaped like a GitHub token, with ***."""
    if not text:
        return text

    for secret in secrets:
        if not secret:
            continue
        text = text.replace(secret, "***")

    return GITHUB_TOKEN.sub("***", text)
