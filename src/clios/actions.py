import datetime
import json
import os
import pathlib
import subprocess
import sys
import typing

from clios import print_error

BUFFER_FOLDER = pathlib.Path(__file__).parent / "buffer"
HOME = pathlib.Path.home()
LOG_PATH = HOME / ".cliOS" / "history.txt"

# The shells keep this in config/cli.json. run keeps it in code, so the
# buffer files hold nothing but keys and values.
ROOTS: typing.Dict[str, typing.Dict[str, str]] = {
    "DOWNLOADS": {"default": "${HOME}/Downloads"},
    "HOME": {"default": "${HOME}"},
    "ONEDRIVE": {"windows": "${HOME}/OneDrive/00 PKM"},
    "ONEDRIVE_HOME": {"windows": "${HOME}/OneDrive"},
    "PHD_ONEDRIVE": {"windows": "${HOME}/OneDrive - University College London/00 PKM"},
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


def dry_run() -> bool:
    return "--dry-run" in sys.argv


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
    raise CliOSError(f"unknown table '{name}', expected link or folder")


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
    print_error("try one of the following:")
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


def log_invocation(status: int) -> None:
    """Append to the log the shell frontends share, so all three rank together."""
    if dry_run():
        return
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
        if os.environ.get("COMPUTERNAME"):
            machine = os.environ["COMPUTERNAME"]
        else:
            import socket

            machine = socket.gethostname()
        command = "run " + " ".join(sys.argv[1:])
        line = "\t".join([stamp, machine, "python", str(status), command])
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
        print_error(f"no such link '{key}'")
        list_keys("links", "link", near=key)
        raise CliOSError("")
    url = links[key]
    if dry_run():
        print(f"url {url}")
        return
    open_url(url)
    print(url)


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
        print_error(f"no such folder '{key}'")
        list_keys("folders", "folder", near=key)
        raise CliOSError("")
    path = expand_roots(folders[key])
    if dry_run():
        print(f"path {path}")
        return
    open_path(path)
    print(path)


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
        print_error("usage: run search [vertical] <query>")
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
    if dry_run():
        print(f"url {url}")
        return
    open_url(url)
    print(url)


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
    if dry_run():
        print(f"code {path.as_posix()}")
        return
    if not path.is_dir():
        url = f"https://github.com/{GITHUB_USER}/{project}"
        print(f"{path.as_posix()} does not exist")
        if input(f"clone {url} ? [y/N] ").strip().lower() != "y":
            return
        subprocess.run(["git", "clone", url], cwd=root, check=True)
    subprocess.run(["code", str(path)], shell=platform_name() == "windows")
    print(path.as_posix())


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
    if dry_run():
        print(f"url {url}")
        return
    open_url(url)
    print(url)


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
    if dry_run():
        print(f"exec git clone {url} (cwd {root.as_posix()})")
        return
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
        raise CliOSError("usage: run set link|folder <key> <value>")
    table = resolve_table(table)
    if dry_run():
        print(f"set {table}.{key} = {words[0]}")
        return
    values = read_buffer(table)
    values[key] = words[0]
    write_buffer(table, values)
    print(f"set {table} {key} -> {words[0]}")


def remove_key(table: str = "", key: str = "", *rest: str) -> None:
    """Remove a link or folder.

    Example
    ```txt
    run rm link infra-grafana
    ```
    """
    if not table or not key:
        raise CliOSError("usage: run rm link|folder <key>")
    table = resolve_table(table)
    values = read_buffer(table)
    if key not in values:
        print_error(f"no such key '{key}' in {table}")
        list_keys(table, table[:-1], near=key)
        raise CliOSError("")
    if dry_run():
        print(f"rm {table}.{key}")
        return
    del values[key]
    write_buffer(table, values)
    print(f"removed {table} {key}")
