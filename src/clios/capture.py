import datetime
import pathlib
import shutil
import typing

from clios.actions import CliOSError, expand_roots

# ==================== #
#                      #
#   UI ICONS           #
#                      #
# ==================== #

CAPTURED = "✅"
INTO = "↳"

TARGETS: typing.Dict[str, typing.Dict[str, typing.Any]] = {
    "agenda": {
        "file": "${VAULT}/2 Activities/Meetings/Meetings Agenda.md",
        "after": "## Questions and Themes",
        "at": "start",
        "task": True,
    },
    "bi": {
        "file": "${VAULT}/2 Activities/Daily Notes/{date}.md",
        "after": "# Brain Inbox",
        "at": "start",
        "task": True,
        "template": "${VAULT}/3 Resources/Templates/Daily Notes Template.md",
    },
    "ai": {
        "file": "${VAULT}/2 Activities/Daily Notes/{date}.md",
        "after": "# Brain Inbox",
        "at": "start",
        "task": True,
        "template": "${VAULT}/3 Resources/Templates/Daily Notes Template.md",
        "prefix": "[AGENT] ",
    },
    "sop": {
        "file": "${VAULT}/2 Activities/Daily Notes/{date}.md",
        "after": "# SOPs",
        "at": "start",
        "task": True,
        "template": "${VAULT}/3 Resources/Templates/Daily Notes Template.md",
    },
    "study": {
        "file": "${VAULT}/2 Activities/Study OS/Inbox.md",
        "after": "# Learning Inbox",
        "at": "end",
        "task": True,
    },
}


def heading_level(text: str) -> int:
    return len(text) - len(text.lstrip("#"))


def insert_line(path: pathlib.Path, after: str, at: str, line: str) -> None:
    """Insert one line under a heading, keeping every existing line ending.

    The vault is mixed: the daily note is CRLF while the agenda and the Study OS
    inbox are LF, so lines are split on "\\n" only and each keeps its own "\\r".
    """
    text = path.read_bytes().decode("utf-8")
    had_trailing_newline = text.endswith("\n")
    lines = text.split("\n")
    if had_trailing_newline and lines:
        lines.pop()

    eol = ""
    heading_index = -1
    section_end = -1
    level = 0
    for index, raw in enumerate(lines):
        stripped = raw.rstrip("\r")
        if stripped != raw:
            eol = "\r"
        if heading_index < 0:
            # Prefix match: the real headings carry emoji (# Brain Inbox 🧠)
            # while QuickAdd stores the plain text.
            if stripped.startswith(after):
                heading_index = index
                level = heading_level(stripped)
        elif section_end < 0 and stripped.startswith("#"):
            if heading_level(stripped) <= level:
                section_end = index

    if heading_index < 0:
        raise CliOSError(f"heading '{after}' not found in {path.as_posix()}")

    if at == "start":
        target = heading_index
    else:
        target = section_end - 1 if section_end >= 0 else len(lines) - 1
        while target > heading_index and not lines[target].strip():
            target -= 1

    lines.insert(target + 1, line + eol)
    output = "\n".join(lines) + ("\n" if had_trailing_newline else "")
    path.write_bytes(output.encode("utf-8"))


def capture(target_id: str, *words: str) -> None:
    text = " ".join(word for word in words if not word.startswith("--")).strip()
    if not text:
        raise CliOSError(f"run {target_id} needs some text")

    target = TARGETS[target_id]
    now = datetime.datetime.now()
    path = pathlib.Path(
        expand_roots(target["file"].replace("{date}", now.strftime("%Y-%m-%d")))
    )
    line = f"{now.strftime('%H:%M')} {target.get('prefix', '')}{text}"
    if target.get("task"):
        line = f"- [ ] {line}"

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        template = target.get("template")
        if template:
            source = pathlib.Path(expand_roots(template))
            if not source.exists():
                raise CliOSError(f"template not found: {source.as_posix()}")
            shutil.copy(source, path)
        else:
            path.write_bytes(b"")

    insert_line(path, target["after"], target["at"], line)
    print(f"{CAPTURED} {line}")
    print(f"  {INTO} {path.as_posix()}")


def brain_inbox(*words: str) -> None:
    """Capture a thought into today's brain inbox.

    Example
    ```txt
    run bi remember to chase Egor
    ```
    """
    capture("bi", *words)


def agent_idea(*words: str) -> None:
    """Capture a thought into today's brain inbox, tagged for the FDE's own
    agent inbox rather than the whole brain inbox.

    Example
    ```txt
    run ai clean up the loops.json drift check
    ```
    """
    capture("ai", *words)


def sop(*words: str) -> None:
    """Capture an SOP idea into today's daily note.

    Example
    ```txt
    run sop always check the token first
    ```
    """
    capture("sop", *words)


def agenda(*words: str) -> None:
    """Add a question to the meetings agenda.

    Example
    ```txt
    run agenda ask Peyman about the deadline
    ```
    """
    capture("agenda", *words)


def study(*words: str) -> None:
    """Capture something you want to learn.

    Example
    ```txt
    run study cholesky decomposition
    ```
    """
    capture("study", *words)
