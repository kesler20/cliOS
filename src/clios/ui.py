"""Shared presentation for cliOS, ported from the sofia CLI's UI module.

Both the one shot commands and the interactive environment render through here,
so a command looks the same whichever way it was typed. The sofia original also
raised Windows toast notifications through `winotify`; that is left behind so
cliOS stays standard library only and identical on both machines.
"""

import os
import pathlib
import subprocess
import sys
import time
import typing

# ==================== #
#                      #
#   UI ICONS           #
#                      #
# ==================== #

LOGO = "⚙️"
SPARKLE = "✨"
ERROR = "❌"
HINT = "💡"

LINK = "🔗"
FOLDER = "📂"
FILE = "📄"
SEARCH = "🔍"
GITHUB = "🐙"
CODE = "💻"
ADDED = "✨"
REMOVED = "🗑️"
CLEANED = "🧹"
COPIED = "📋"

NAME = f"cliOS {LOGO}{SPARKLE}"

# The window title, using the same escape sequence sofia used.
TITLE = f"\033]0;cliOS {LOGO}\a"

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]


def print_line() -> None:
    """Print a line spanning the width of the console."""
    try:
        columns = os.get_terminal_size().columns
    except OSError:
        columns = 80
    print("-" * columns)


def loading_animation(loading_time: int = 10) -> None:
    """Spin a cursor for roughly `loading_time` ticks."""
    animation = "|/-\\"
    for tick in range(loading_time):
        time.sleep(0.2)
        sys.stdout.write("\r" + animation[tick % len(animation)])
        sys.stdout.flush()
    sys.stdout.write("\rDone!\n")


def print_message(*args: typing.Any) -> None:
    """Print a message badged with the cliOS icons."""
    print(f"\n{LOGO}{SPARKLE}|", *args)


# ==================== #
#                      #
#   GIT STATE          #
#                      #
# ==================== #


def _git(*arguments: str) -> str:
    """Run a git command inside the cliOS repository, returning its output."""
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=REPOSITORY,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def git_state() -> str:
    """Describe cliOS's own repository for the prompt.

    Local state is recomputed on every call because it costs nothing and an edit
    should show immediately. The behind count reflects the last fetch, so it only
    moves once `run update` has fetched.
    """
    dirty = len([line for line in _git("status", "--porcelain").splitlines() if line])
    counts = _git("rev-list", "--left-right", "--count", "@{u}...HEAD")

    behind, ahead = 0, 0
    if counts:
        parts = counts.split()
        if len(parts) == 2:
            behind, ahead = int(parts[0]), int(parts[1])

    marks = []
    if ahead:
        marks.append(f"↑{ahead}")
    if behind:
        marks.append(f"↓{behind}")
    if dirty:
        marks.append(f"●{dirty}")
    return " ".join(marks) if marks else "clean"


def display_ui() -> str:
    """The interactive environment's prompt."""
    return f"{os.getcwd()} | {git_state()} | {NAME}"
