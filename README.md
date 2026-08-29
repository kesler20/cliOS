# ⚙️ command line Operating Systems (cliOS)

>`cliOS` is a command line interface for one-shotting commands to open links, folders and capture ideas

`run <command>`, typed at your normal prompt. Same on Windows and macOS.

## Install

```bash
uv tool install --editable .
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
run cleanup                          re-sort the buffer files alphabetically
```

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

## Everything else

`run` lists the commands and `run <verb> --help` explains one. Adding a command
is a function whose first docstring line is its help, plus a line in
`src/clios/user_input_map.py`. Links and folders live in `src/clios/buffer/`,
and every invocation is logged to `.cliOS/history.txt`.
