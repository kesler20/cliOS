# cliOS

One-shot commands for the things the sofia CLI was used for, typed at your normal
prompt instead of inside a REPL. Same commands on Windows (PowerShell or Git Bash)
and macOS (zsh or bash).

```
cli link pkm-ticktick              open a stored link
cli folder papers                  open a stored folder in the file explorer
cli search scholar mrna vaccine    search a site
cli bi remember to chase Egor      capture into today's brain inbox
cli sop always check the token     capture an SOP idea
cli agenda ask Peyman about X      add a question to the meetings agenda
cli study cholesky decomposition   capture something to learn
cli code automation_engine         open ~/protocol/<project> in VS Code
cli clone modelOS                  clone kesler20/<project> into ~/protocol
cli set link foo https://foo.com   add a key
cli rm link foo                    remove a key
```

`cli` on its own lists the commands. A bare verb or an unknown key lists that
section's keys alphabetically. `--dry-run` prints the resolved action without
doing anything. `--help` after a verb prints its one-line help.

## Install

```bash
bash install.sh          # bash and zsh: symlinks bin/cli into ~/.local/bin
pwsh -File install.ps1   # PowerShell: adds a `cli` function to $PROFILE
```

`jq` is required by the bash frontend. It ships with anaconda on this Windows
machine; on the Mac, `brew install jq`.

## How it works

Everything is data in `config/cli.json`. Two thin interpreters read it,
`bin/cli` (bash) and `bin/cli.ps1` (PowerShell), and they must stay
behaviourally identical - `bash tests/parity.sh` walks every leaf in the spec,
dry-runs it through both, and diffs the results.

Adding a command means editing JSON, not writing shell. The config has these
sections:

- `roots` - logical roots per platform. `${VAULT}`, `${PROTOCOL}`, `${ONEDRIVE}`
  and friends are substituted into any path. A root with no entry for the
  current platform fails with `root X is not configured on this machine`, which
  is what the OneDrive folder keys do on the Mac.
- `links` - one flat alphabetical namespace. No groups: the hierarchy lives in
  the key, like `google-calendar` and `youtube-watch-later`.
- `folders` - same, for paths.
- `searches` - vertical to URL template containing `{query}`.
- `captures` - the quick-add targets, mirroring the Obsidian QuickAdd config.
- `commands` - the verb tree. Each verb has a `help` string, optional `aliases`,
  and an `action`.

### Action types

| type | fields | what it does |
| --- | --- | --- |
| `lookup` | `table`, `as` (`url` or `path`) | resolves a key from a table, then opens it |
| `search` | `table`, `default` | url-encodes the remaining args into `{query}` |
| `code` | `root`, `clone` | opens `root/<name>` in VS Code, offering the clone if absent |
| `exec` | `cwd`, `argv` | runs an argv template, `{1}`, `{2}` filled from the args |
| `capture` | `id` | inserts a line into a markdown file under a heading |
| `config-set` / `config-rm` | `tables` | edits `links` or `folders` in place |

### Adding a link by hand

```json
"links": {
  "infra-grafana": "https://grafana.example.com"
}
```

or `cli set link infra-grafana https://grafana.example.com`, which rewrites the
config in canonical form: keys sorted, two space indent. Both frontends use the
same canonical writer so the diff is the one line you changed.

## Captures

The four capture verbs mirror
`00 PKM/.obsidian/plugins/quickadd/data.json` field for field, so a line
captured here is indistinguishable from one captured through the Obsidian
QuickAdd command.

| verb | file | heading | position |
| --- | --- | --- | --- |
| `bi` | today's daily note | `# Brain Inbox` | first line of the section |
| `sop` | today's daily note | `# SOPs` | first line of the section |
| `agenda` | `2 Activities/Meetings/Meetings Agenda.md` | `## Questions and Themes` | first line |
| `study` | `2 Activities/Study OS/Inbox.md` | `# Learning Inbox` | end of the section |

Headings are matched by prefix, since the real ones carry emoji
(`# Brain Inbox 🧠`) while QuickAdd stores `# Brain Inbox`. A missing daily note
is created from the Daily Notes template. A missing heading is an error rather
than something the tool invents.

## Usage log

Every real invocation appends a tab separated line to `~/.cliOS/history.txt`:
timestamp, machine, frontend, exit status, the command as typed. Failures are
logged too, since a mistyped key is the signal for what to add next. `--dry-run`
is not logged. Set `"log": false` in the config to turn it off, or `log_path` to
move it.

```bash
cut -f5 ~/.cliOS/history.txt | sort | uniq -c | sort -rn | head -20
```

## py-cli, the Python implementation

A second implementation of the same command surface, running as a trial. If it
wins, the PowerShell frontend goes. Until then all three coexist and `cli` keeps
meaning the shell implementation.

```bash
uv tool install --editable .
py-cli link pkm-ticktick
```

Measured here on Windows, five runs of the same lookup:

| implementation | per invocation |
| --- | --- |
| py-cli | 523ms |
| bin/cli.ps1 | 1122ms |
| bin/cli | 1353ms |

### It is separate, not a third frontend

py-cli does not read `config/cli.json`. It has its own `src/clios/buffer/links.json`
and `folders.json`, flat key to value and nothing else. Search verticals, the
four capture targets and the roots table live in Python code instead.

The consequence to know about: `cli set link foo` and `py-cli set link foo`
write different files, so the two link sets drift from here on. That is the
price of keeping this side simple, and the trial ends with one winner.

### Layout

| file | holds |
| --- | --- |
| `src/clios/__init__.py` | command traversal, error listings, `main` |
| `src/clios/user_input_map.py` | the command tree |
| `src/clios/actions.py` | roots, openers, lookups, search, git, config writes |
| `src/clios/capture.py` | the four quick-add targets and the heading insert |
| `src/clios/buffer/` | links and folders |

### Adding a command

Write a function with a docstring whose first line is its one line help, then
add one line to `user_input_map.py`:

```python
"weather": {"leaf node": actions.weather},
```

The docstring summary shows up in `py-cli` and in `py-cli <verb> --help`, and
the signature is printed when the arguments are wrong. Nested paths work too:
a dict of dicts gives `py-cli search scholar <query>`.

Platform handling is one place rather than two shims: `webbrowser.open` for
URLs, and `os.startfile` / `open -R` / `xdg-open` for paths.
