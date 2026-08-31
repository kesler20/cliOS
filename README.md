# ⚙️ command line Operating Systems (cliOS)

>`cliOS` is a command line interface for one-shotting commands to open links, folders and capture ideas

`run <command>`, typed at your normal prompt. Same on Windows and macOS.

## Installation

### macOS

cliOS requires Python 3.14 or newer. Install it as an isolated command-line tool
with `pipx` instead of adding it to Homebrew's global Python environment. The
editable installation exposes `run` everywhere while continuing to execute the
source in the cloned repository.

#### Prerequisites

Confirm that Homebrew and `pipx` are available.

```bash
brew --version
pipx --version
```

Install the required Python version through Homebrew.

```bash
brew install python@3.14
"$(brew --prefix python@3.14)/bin/python3.14" --version
```

#### Clone and install

Clone cliOS into `~/protocol` if it is not already present.

```bash
mkdir -p "$HOME/protocol"
git clone https://github.com/kesler20/cliOS.git "$HOME/protocol/cliOS"
```

The name `clios` is also used by an unrelated package on PyPI. Remove any
existing `pipx` installation with that package name before installing this
repository.

```bash
pipx uninstall clios
pipx install \
  --python "$(brew --prefix python@3.14)/bin/python3.14" \
  --editable "$HOME/protocol/cliOS"
```

Make sure the directory where `pipx` exposes commands is on `PATH`, then restart
the login shell.

```bash
pipx ensurepath
exec zsh -l
```

#### Verify the installation

Run cliOS from a directory outside its repository.

```bash
cd /tmp
command -v run
run
```

`command -v run` should resolve to `~/.local/bin/run`. The final command should
print the cliOS command list.

#### Update or remove cliOS

Because the installation is editable, source changes take effect immediately.
Pull repository updates normally. Reinstall only when dependencies, entry points,
or package metadata change.

```bash
git -C "$HOME/protocol/cliOS" pull
pipx reinstall clios
```

Remove the global command without deleting the repository.

```bash
pipx uninstall clios
```

### Windows

cliOS uses the same editable tool installation on Windows, managed by `uv`.
Install Python 3.14 and confirm that `uv` can find it.

```powershell
uv python install 3.14
uv python find 3.14
```

Clone cliOS into the `protocol` folder if it is not already present.

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\protocol" | Out-Null
git clone https://github.com/kesler20/cliOS.git "$HOME\protocol\cliOS"
Set-Location "$HOME\protocol\cliOS"
```

Install the repository as an editable global tool. This retains the original
Windows installation command.

```powershell
uv tool install --python 3.14 --editable .
uv tool update-shell
```

Open a new PowerShell window after `uv tool update-shell`, then verify the command
from another directory.

```powershell
Set-Location $HOME
Get-Command run
run
```

If an unrelated package named `clios` is already installed through `uv`, replace
it with this repository.

```powershell
uv tool uninstall clios
Set-Location "$HOME\protocol\cliOS"
uv tool install --python 3.14 --editable .
```

Source changes take effect immediately. Reinstall after dependency, entry-point,
or package metadata changes.

```powershell
git -C "$HOME\protocol\cliOS" pull
uv tool install --force --python 3.14 --editable "$HOME\protocol\cliOS"
```

## Quick add

Captures into the vault, matching the Obsidian QuickAdd commands.

```
run bi remember to chase Egor        today's brain inbox
run sop always check the token       today's daily note, SOPs
run agenda ask Peyman about X        the meetings agenda
run study cholesky decomposition     the Study OS inbox
```

## Projects

A bare project name, under `~/protocol` and `github.com/kesler20`.

```
run code automation_engine           open it in VS Code, offering the clone
run clone modelOS                    clone it into ~/protocol
run github wiz_iot_hub               open it on GitHub
```

## Links, folders and files

```
run link youtube watch later         open a stored link
run folder papers                    open a stored folder in the file explorer
run file links                       open a stored file in its default app
run set link foo https://foo.com     add a key
run rm link foo                      remove a key
run copy folder papers               put a stored value on the clipboard
run cleanup                          re-sort the buffer files alphabetically
```

`copy` exists because a `run` process cannot change the directory of the shell
that launched it. Copy the folder path, then paste it after `cd`.

Keys are composite, so `link` and `file` join their words: `youtube watch later`
and `youtube-watch-later` are the same thing. On a miss you get the keys sharing
a word with what you typed.

`file` values are paths relative to your home directory, resolved at run time so
the same key works on both machines. It comes seeded with the three buffer files
themselves, so `run file links` opens the link list for editing.

## Search

```
run search how to exit vim           google
run search scholar mrna vaccine      also yt, gh, images, icons, maps, amazon
```

## The interactive environment

```
run cli                              open it
run update                           fetch cliOS and refresh the prompt's git state
```

The prompt is `{cwd} | {git state} | cliOS`, where the git state describes cliOS's
own repository: `↑` ahead, `↓` behind, `●` uncommitted. Nothing fetches on its
own, so `↓` only moves once `run update` has fetched. `update` never pulls or
touches the working tree.

Inside, every verb above works as it does outside, and `run` gains a second
meaning: it reaches the native shell, with your profile loaded, so aliases and
functions are there.

```
run cd papers                        move, resolving a folder key before a path
run cd ..                            and ordinary paths, plus home
run git log --oneline -5             anything else goes to the shell
exit                                 or quit, Ctrl-D, Ctrl-C
```

`cd` is the one command not passed through, since a directory change inside a
spawned shell would die with it. Commands typed here are logged like any other.

## Everything else

`run` lists the commands and `run <verb> --help` explains one. Adding a command
is a function whose first docstring line is its help, plus a line in
`src/clios/user_input_map.py`. Links and folders live in `src/clios/buffer/`,
and every invocation is logged to `.cliOS/history.txt`.
