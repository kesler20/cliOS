"""The cliOS interactive environment, entered with `run cli`.

Modelled on the sofia CLI's loop, which read a line, split it and handed it to
the same command mapper the one shot commands use. The difference is that this
one is entered on demand rather than being the only way in, and that it adds a
`run` verb of its own for reaching the native shell.
"""

import os
import pathlib
import shlex
import subprocess
import sys
import typing

from clios import traverse_command_mapper
from clios.actions import (
    CliOSError,
    expand_roots,
    log_invocation,
    platform_name,
    read_buffer,
)
from clios.ui import ERROR, HINT, TITLE, display_ui, print_line, print_message

EXIT_WORDS = ("exit", "quit")


def shell_command(command: str) -> int:
    """Run a command in the native shell with the user's profile loaded.

    The profile matters: without it none of the PowerShell functions and aliases
    would be there, which is most of what makes the passthrough worth having.
    `os.system` is not used because on Windows it runs cmd.exe.
    """
    if platform_name() == "windows":
        argv = ["pwsh", "-Command", command]
    else:
        argv = [os.environ.get("SHELL", "/bin/bash"), "-lc", command]
    try:
        return subprocess.run(argv, check=False).returncode
    except OSError as error:
        raise CliOSError(f"could not start the shell: {error}") from error


def change_directory(*words: str) -> int:
    """Move the environment, resolving a saved folder key before a path.

    Keys win over paths, so `cd papers` reaches the stored folder rather than a
    directory of the same name that happens to be here.
    """
    if not words:
        raise CliOSError("usage: cmd cd <folder key|path>")

    key = "-".join(words)
    folders = read_buffer("folders")
    if key in folders:
        target = pathlib.Path(expand_roots(folders[key]))
    elif key == "home":
        target = pathlib.Path.home()
    else:
        target = pathlib.Path(" ".join(words)).expanduser()

    if not target.is_dir():
        raise CliOSError(f"no such folder '{key}'")

    os.chdir(target)
    return 0


def run_verb(*words: str) -> int:
    """`cmd` inside the environment: reach the shell, or move with `cd`."""
    if not words:
        raise CliOSError("usage: cmd <command>")
    if words[0] == "cd":
        return change_directory(*words[1:])
    return shell_command(" ".join(words))


def execute_line(tokens: typing.List[str]) -> int:
    if tokens[0] == "cmd":
        try:
            return run_verb(*tokens[1:])
        except CliOSError as error:
            if str(error):
                print(f"{ERROR} {error}", file=sys.stderr)
            return 1
    return traverse_command_mapper(tokens)


def main() -> None:
    """Open the interactive environment.

    Example
    ```txt
    run cli
    ```
    """
    sys.stdout.write(TITLE)
    print_line()
    print_message("type a command, `cmd <shell command>` to reach the shell, or exit")
    print_line()

    while True:
        try:
            line = input(f"\n({display_ui()}): ")
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not line.strip():
            continue
        if line.strip().lower() in EXIT_WORDS:
            return

        try:
            tokens = shlex.split(line)
        except ValueError as error:
            print(f"{ERROR} {error}", file=sys.stderr)
            print(f"{HINT} check the quoting", file=sys.stderr)
            continue

        status = execute_line(tokens)
        log_invocation(status, command=line.strip())
