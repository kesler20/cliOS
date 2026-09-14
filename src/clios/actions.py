import datetime
import json
import os
import pathlib
import subprocess
import sys
import typing

from clios import print_error
from clios.ui import (
    ADDED,
    CLEANED,
    CODE,
    COPIED,
    ERROR,
    FILE,
    FOLDER,
    GITHUB,
    HINT,
    LINK,
    REMOVED,
    SEARCH,
)

BUFFER_FOLDER = pathlib.Path(__file__).parent / "buffer"
HOME = pathlib.Path.home()
LOG_PATH = HOME / "protocol" / "cliOS" / ".cliOS" / "history.txt"

# The shells keep this in config/cli.json. run keeps it in code, so the
# buffer files hold nothing but keys and values.
ROOTS: typing.Dict[str, typing.Dict[str, str]] = {
    "DOWNLOADS": {"default": "${HOME}/Downloads"},
    "HOME": {"default": "${HOME}"},
    "ONEDRIVE": {"windows": "${HOME}/OneDrive/00 PKM"},
    "ONEDRIVE_HOME": {"windows": "${HOME}/OneDrive"},
    "PHD_ONEDRIVE": {"windows": "${HOME}/OneDrive - University College London/00 PKM"},
    "GOUSTO_DRIVE": {
        "darwin": "${HOME}/Library/CloudStorage/GoogleDrive-kesler.isoko@gousto.co.uk/My Drive"
    },
    "GOUSTO_SHARED_DRIVES": {
        "darwin": "${HOME}/Library/CloudStorage/GoogleDrive-kesler.isoko@gousto.co.uk/Shared drives"
    },
    "PROTOCOL": {"default": "${HOME}/protocol"},
    "VAULT": {"default": "${HOME}/protocol/00 PKM"},
}

SEARCHES: typing.Dict[str, str] = {
    "amazon": "https://www.amazon.co.uk/s?k={query}",
    "gh": "https://github.com/search?q={query}&type=repositories",
    "google": "https://www.google.com/search?q={query}",
    "icons": "https://www.google.com/search?tbm=isch&q={query}+icon",
    "images": "https://www.google.com/search?tbm=isch&q={query}",
    "maps": "https://www.google.com/maps/search/{query}",
    "scholar": "https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q={query}",
    "yt": "https://www.youtube.com/results?search_query={query}",
}

GITHUB_USER = "kesler20"


class CliOSError(Exception):
    """A failure the user should read, not a traceback."""


# ================= #
#                   #
#     PLATFORM      #
#                   #
# ================= #


def platform_name() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "darwin"
    return "linux"


def expand_roots(value: str) -> str:
    """Replace every ${ROOT} token with its path for this platform.

    A root with no entry for the current platform is an error rather than a
    silent empty path: the OneDrive folder keys are expected to fail this way
    on the Mac.
    """
    platform = platform_name()
    while "${" in value:
        start = value.index("${")
        end = value.index("}", start)
        name = value[start + 2 : end]
        if name == "HOME":
            resolved = str(HOME).replace("\\", "/")
        else:
            root = ROOTS.get(name, {})
            template = root.get(platform, root.get("default", ""))
            if not template:
                raise CliOSError(
                    f"root {name} is not configured on this machine ({platform})"
                )
            resolved = expand_roots(template)
        value = value[:start] + resolved + value[end + 1 :]
    return value


# ================= #
#                   #
#      BUFFER       #
#                   #
# ================= #


def buffer_path(table: str) -> pathlib.Path:
    return BUFFER_FOLDER / f"{table}.json"


def read_buffer(table: str) -> typing.Dict[str, str]:
    return json.loads(buffer_path(table).read_text(encoding="utf-8"))


def write_buffer(table: str, values: typing.Dict[str, str]) -> None:
    """Sorted keys, two space indent, LF, so a set is a one line diff."""
    content = json.dumps(dict(sorted(values.items())), indent=2, ensure_ascii=False)
    buffer_path(table).write_bytes((content + "\n").encode("utf-8"))


def resolve_table(name: str) -> str:
    if name in ("link", "links"):
        return "links"
    if name in ("folder", "folders"):
        return "folders"
    if name in ("file", "files"):
        return "files"
    raise CliOSError(f"unknown table '{name}', expected link, folder or file")


def list_keys(table: str, verb: str, near: str = "") -> None:
    """List a table's keys alphabetically, narrowed to a near miss if there is one.

    Typing a key as words makes near misses likelier, and dumping 130 keys at
    someone who mistyped one is not a listing anyone reads. When `near` is given,
    only the keys sharing a word with it are shown, falling back to everything
    when that matches nothing.
    """
    keys = sorted(read_buffer(table))
    words = [word for word in near.split("-") if word]
    if words:
        candidates = [key for key in keys if any(word in key for word in words)]
        if candidates:
            keys = candidates
    print_error(f"{HINT} try one of the following:")
    for key in keys:
        print_error(f"  run {verb} {key}")


# ================= #
#                   #
#      OPENERS      #
#                   #
# ================= #


def open_url(url: str) -> None:
    # Imported here rather than at module scope: it costs about 25ms of a
    # command that should feel instant, and most commands never open a URL.
    import webbrowser

    webbrowser.open(url)


def open_file(target: str) -> None:
    """Open a file with whatever application owns it."""
    path = pathlib.Path(target)
    if not path.exists():
        raise CliOSError(f"file does not exist: {target}")
    platform = platform_name()
    if platform == "windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif platform == "darwin":
        subprocess.run(["open", str(path)])
    else:
        subprocess.run(["xdg-open", str(path)])


def open_path(target: str) -> None:
    path = pathlib.Path(target)
    if not path.exists():
        raise CliOSError(f"path does not exist: {target}")
    platform = platform_name()
    if platform == "windows":
        if path.is_dir():
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["explorer.exe", f"/select,{path}"], check=False)
    elif platform == "darwin":
        subprocess.run(["open"] + ([] if path.is_dir() else ["-R"]) + [str(path)])
    else:
        subprocess.run(["xdg-open", str(path if path.is_dir() else path.parent)])


# ================= #
#                   #
#       LOG         #
#                   #
# ================= #


def log_invocation(status: int, command: str = "") -> None:
    """Append to the log the shell frontends share, so all three rank together.

    `command` is given by the interactive environment, where the typed line is
    not in `sys.argv`. It defaults to the one shot invocation.
    """
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
        if os.environ.get("COMPUTERNAME"):
            machine = os.environ["COMPUTERNAME"]
        else:
            import socket

            machine = socket.gethostname()
        command = command or "run " + " ".join(sys.argv[1:])
        line = "\t".join([stamp, machine, str(status), command])
        with open(LOG_PATH, "a", encoding="utf-8", newline="") as log_file:
            log_file.write(line + "\n")
    except OSError:
        pass


# ================= #
#                   #
#     COMMANDS      #
#                   #
# ================= #


def compose_key(*parts: str) -> str:
    """Join the words of a command into one composite key.

    The keys are composite by design (`youtube-watch-history`), so the words can
    be typed as words and joined here. A key typed with its dashes already in
    place survives unchanged, and the two forms can be mixed.
    """
    words = [part for part in parts if not part.startswith("--")]
    return "-".join(word.strip("-") for word in words if word.strip("-"))


def open_link(*parts: str) -> None:
    """Open a stored link in the browser.

    Example
    ```txt
    run link youtube watch history
    run link youtube-watch-history
    ```
    """
    key = compose_key(*parts)
    if not key:
        list_keys("links", "link")
        raise CliOSError("")
    links = read_buffer("links")
    if key not in links:
        print_error(f"{ERROR} no such link '{key}'")
        list_keys("links", "link", near=key)
        raise CliOSError("")
    url = links[key]
    open_url(url)
    print(f"{LINK} {url}")


def open_folder(key: str = "", *rest: str) -> None:
    """Open a stored folder in the file explorer.

    Example
    ```txt
    run folder papers
    ```
    """
    if not key or key.startswith("--"):
        list_keys("folders", "folder")
        raise CliOSError("")
    folders = read_buffer("folders")
    if key not in folders:
        print_error(f"{ERROR} no such folder '{key}'")
        list_keys("folders", "folder", near=key)
        raise CliOSError("")
    path = expand_roots(folders[key])
    open_path(path)
    print(f"{FOLDER} {path}")


def open_stored_file(*parts: str) -> None:
    """Open a stored file with its default application.

    Values in `buffer/files.json` are paths relative to the home directory,
    which is resolved at run time so the same key works on both machines.

    Example
    ```txt
    run file powershell profile
    run file powershell-profile
    ```
    """
    key = compose_key(*parts)
    if not key:
        list_keys("files", "file")
        raise CliOSError("")
    files = read_buffer("files")
    if key not in files:
        print_error(f"{ERROR} no such file '{key}'")
        list_keys("files", "file", near=key)
        raise CliOSError("")
    value = expand_roots(files[key])
    path = pathlib.Path(value)
    if not path.is_absolute():
        path = HOME / value
    open_file(str(path))
    print(f"{FILE} {path.as_posix()}")


def search(*query: str) -> None:
    """Search a site. The first word may be a vertical.

    Example
    ```txt
    run search scholar mrna vaccine
    run search how to exit vim
    ```
    """
    words = [word for word in query if not word.startswith("--")]
    if not words:
        print_error(f"{HINT} usage: run search [vertical] <query>")
        print_error("verticals:")
        for vertical in sorted(SEARCHES):
            print_error(f"  {vertical}")
        raise CliOSError("")
    vertical = "google"
    if words[0] in SEARCHES:
        vertical = words[0]
        words = words[1:]
    if not words:
        raise CliOSError(f"run search {vertical} needs a query")
    from urllib.parse import quote

    url = SEARCHES[vertical].replace("{query}", quote(" ".join(words), safe=""))
    open_url(url)
    print(f"{SEARCH} {url}")


def open_in_code(project: str = "", *rest: str) -> None:
    """Open ~/protocol/<project> in VS Code, offering the clone if it is absent.

    Example
    ```txt
    run code automation_engine
    ```
    """
    if not project or project.startswith("--"):
        raise CliOSError("usage: run code <project>")
    root = pathlib.Path(expand_roots("${PROTOCOL}"))
    path = root / project
    if not path.is_dir():
        url = f"https://github.com/{GITHUB_USER}/{project}"
        print(f"{path.as_posix()} does not exist")
        if input(f"clone {url} ? [y/N] ").strip().lower() != "y":
            return
        subprocess.run(["git", "clone", url], cwd=root, check=True)
    subprocess.run(["code", str(path)], shell=platform_name() == "windows")
    print(f"{CODE} {path.as_posix()}")


def github(*parts: str) -> None:
    """Open a GitHub repository, or your repository list with no name.

    Example
    ```txt
    run github automation_engine
    run github anthropics/claude-code
    ```
    """
    words = [part for part in parts if not part.startswith("--")]
    if not words:
        url = f"https://github.com/{GITHUB_USER}?tab=repositories"
    else:
        # Taken verbatim rather than dash joined the way link keys are: repo
        # names carry underscores, as in automation_engine and wiz_iot_hub.
        repo = words[0]
        owner_and_repo = repo if "/" in repo else f"{GITHUB_USER}/{repo}"
        url = f"https://github.com/{owner_and_repo}"
    open_url(url)
    print(f"{GITHUB} {url}")


def clone(project: str = "", *rest: str) -> None:
    """Clone kesler20/<project> into ~/protocol.

    Example
    ```txt
    run clone modelOS
    ```
    """
    if not project or project.startswith("--"):
        raise CliOSError("usage: run clone <project>")
    root = pathlib.Path(expand_roots("${PROTOCOL}"))
    url = f"https://github.com/{GITHUB_USER}/{project}"
    subprocess.run(["git", "clone", url], cwd=root, check=True)


def set_key(table: str = "", key: str = "", *value: str) -> None:
    """Add or update a link or folder.

    Example
    ```txt
    run set link infra-grafana https://grafana.example.com
    ```
    """
    words = [word for word in value if not word.startswith("--")]
    if not table or not key or not words:
        raise CliOSError("usage: run set link|folder|file <key> <value>")
    table = resolve_table(table)
    values = read_buffer(table)
    values[key] = words[0]
    write_buffer(table, values)
    print(f"{ADDED} set {table} {key} -> {words[0]}")


def cleanup(*args: str) -> None:
    """Rewrite every buffer file in canonical form, keys alphabetical.

    `set` and `rm` already write this way, so this is for the files after they
    have been edited by hand.

    Example
    ```txt
    run cleanup
    ```
    """
    for path in sorted(BUFFER_FOLDER.glob("*.json")):
        before = path.read_bytes()
        seen: typing.List[str] = []

        def collect(pairs, seen=seen):
            seen.extend(key for key, _ in pairs)
            return dict(pairs)

        try:
            values = json.loads(before.decode("utf-8"), object_pairs_hook=collect)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CliOSError(f"{path.name} is not valid JSON: {error}") from error

        # A duplicate key is legal JSON and the last one silently wins, so it
        # would vanish here without a word.
        duplicates = sorted({key for key in seen if seen.count(key) > 1})
        for key in duplicates:
            print_error(f"{ERROR} {path.stem}: '{key}' appeared more than once, kept the last")

        write_buffer(path.stem, values)
        was_tidy = path.read_bytes() == before
        state = "already in order" if was_tidy else "reordered"
        print(f"{CLEANED} {path.stem}: {len(values)} keys, {state}")


def remove_key(table: str = "", key: str = "", *rest: str) -> None:
    """Remove a link or folder.

    Example
    ```txt
    run rm link infra-grafana
    ```
    """
    if not table or not key:
        raise CliOSError("usage: run rm link|folder|file <key>")
    table = resolve_table(table)
    values = read_buffer(table)
    if key not in values:
        print_error(f"{ERROR} no such key '{key}' in {table}")
        list_keys(table, table[:-1], near=key)
        raise CliOSError("")
    del values[key]
    write_buffer(table, values)
    print(f"{REMOVED} removed {table} {key}")


def copy_value(table: str = "", *parts: str) -> None:
    """Copy a stored link, folder or file value to the clipboard.

    A `run` process cannot change the directory of the shell that launched it,
    so a folder key is copied for you to paste after `cd`.

    Example
    ```txt
    run copy folder papers
    ```
    """
    if not table or table.startswith("--"):
        raise CliOSError("usage: run copy link|folder|file <key>")
    table = resolve_table(table)
    key = "-".join(word for word in parts if not word.startswith("--"))
    if not key:
        list_keys(table, f"copy {table}")
        raise CliOSError("")

    values = read_buffer(table)
    if key not in values:
        print_error(f"{ERROR} no such {table[:-1]} '{key}'")
        list_keys(table, f"copy {table}", near=key)
        raise CliOSError("")

    value = values[key]
    if table == "folders":
        value = expand_roots(value)
    elif table == "files":
        value = str(HOME / expand_roots(value))

    copy_to_clipboard(value)
    print(f"{COPIED} {value}")


def copy_to_clipboard(value: str) -> None:
    """Put text on the clipboard using whatever the platform ships with."""
    platform = platform_name()
    if platform == "windows":
        command = ["clip"]
    elif platform == "darwin":
        command = ["pbcopy"]
    else:
        command = ["xclip", "-selection", "clipboard"]
    try:
        subprocess.run(command, input=value, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise CliOSError(f"could not reach the clipboard: {error}") from error


def update() -> None:
    """Fetch cliOS's own repository and report what the prompt will show.

    Read only: it never pulls, merges or touches the working tree.

    Example
    ```txt
    run update
    ```
    """
    from clios import ui

    result = subprocess.run(
        ["git", "fetch"],
        cwd=ui.REPOSITORY,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise CliOSError(f"could not fetch: {result.stderr.strip()}")
    print(f"{GITHUB} cliOS {ui.git_state()}")
