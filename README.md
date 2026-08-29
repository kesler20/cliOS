# cliOS

One-shot commands for the things the sofia CLI was used for, typed at your normal
prompt instead of inside a REPL. Same commands on Windows and macOS.

```
run link pkm-ticktick              open a stored link
run folder papers                  open a stored folder in the file explorer
run search scholar mrna vaccine    search a site
run bi remember to chase Egor      capture into today's brain inbox
run sop always check the token     capture an SOP idea
run agenda ask Peyman about X      add a question to the meetings agenda
run study cholesky decomposition   capture something to learn
run code automation_engine         open ~/protocol/<project> in VS Code
run clone modelOS                  clone kesler20/<project> into ~/protocol
run set link foo https://foo.com   add a key
run rm link foo                    remove a key
```

`run` on its own lists the commands with their one line help. A bare verb or
an unknown key lists that section's keys alphabetically. `--dry-run` prints the
resolved action without doing anything. `--help` after a verb prints its help
and signature, `--explain` its full docstring.

## Install

```bash
uv tool install --editable .
```

Editable, so edits take effect without reinstalling, and the tool environment is
isolated from whatever Python is otherwise active. Stdlib only, no dependencies.

## Layout

| file | holds |
| --- | --- |
| `src/clios/__init__.py` | command traversal, error listings, `main` |
| `src/clios/user_input_map.py` | the command tree |
| `src/clios/actions.py` | roots, openers, lookups, search, git, config writes |
| `src/clios/capture.py` | the four quick-add targets and the heading insert |
| `src/clios/buffer/` | `links.json` and `folders.json`, flat key to value |

Links and folders are one flat alphabetical namespace. There are no groups: the
hierarchy lives in the key, like `google-calendar` and `youtube-watch-later`.
Add one with `run set link <key> <url>`, which rewrites the buffer file with
sorted keys and two space indent so the diff is the line you changed.

Folder paths carry `${ROOT}` tokens resolved from the `ROOTS` table in
`actions.py`, which is keyed by platform. A root with no entry for the current
platform fails with `root X is not configured on this machine`, which is what
the OneDrive keys do on the Mac.

Platform handling is one place: `webbrowser.open` for URLs, and `os.startfile` /
`open -R` / `xdg-open` for paths.

## Adding a command

Write a function whose first docstring line is its one line help, then add one
line to `user_input_map.py`:

```python
"weather": {"leaf node": actions.weather},
```

The summary shows up in `run` and in `run weather --help`, and the
signature is printed when the arguments are wrong. Nested paths work too: a dict
of dicts gives `run search scholar <query>`.

## Captures

The four capture verbs mirror `00 PKM/.obsidian/plugins/quickadd/data.json`
field for field, so a line captured here is indistinguishable from one captured
through the Obsidian QuickAdd command.

| verb | file | heading | position |
| --- | --- | --- | --- |
| `bi` | today's daily note | `# Brain Inbox` | first line of the section |
| `sop` | today's daily note | `# SOPs` | first line of the section |
| `agenda` | `2 Activities/Meetings/Meetings Agenda.md` | `## Questions and Themes` | first line |
| `study` | `2 Activities/Study OS/Inbox.md` | `# Learning Inbox` | end of the section |

Headings are matched by prefix, since the real ones carry emoji
(`# Brain Inbox 🧠`) while QuickAdd stores `# Brain Inbox`. A missing daily note
is created from the Daily Notes template. A missing heading is an error rather
than something the tool invents. Line endings are preserved per line, because
the vault is mixed: the daily note is CRLF while the agenda and the Study OS
inbox are LF.

## Usage log

Every real invocation appends a tab separated line to `~/.cliOS/history.txt`:
timestamp, machine, frontend, exit status, the command as typed. Failures are
logged too, since a mistyped key is the signal for what to add next. `--dry-run`
is not logged.

```bash
cut -f5 ~/.cliOS/history.txt | sort | uniq -c | sort -rn | head -20
```

The `frontend` column exists because cliOS was briefly two implementations: a
bash and a PowerShell pair driven by a declarative `config/cli.json`, and this
Python one. Python won on 2026-08-29 and the shells were removed. Their history
is in the log's `bash` and `pwsh` rows and in git.
