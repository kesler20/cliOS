import typing
from clios import actions, capture, interactive

mapper: typing.Dict[str, typing.Any] = {
  # quick add capture commands. 
    "agenda": {"leaf node": capture.agenda},
    "bi": {"leaf node": capture.brain_inbox},
    "sop": {"leaf node": capture.sop},
    "study": {"leaf node": capture.study},

    # special commands.
    "cli": {"leaf node": interactive.main},
    "code": {"leaf node": actions.open_in_code},
    "clone": {"leaf node": actions.clone},
    "github": {"leaf node": actions.github},

    # file and link commands.
    "folder": {"leaf node": actions.open_folder},
    "folders": {"leaf node": actions.open_folder},
    "file": {"leaf node": actions.open_stored_file},
    "files": {"leaf node": actions.open_stored_file},
    "link": {"leaf node": actions.open_link},
    "links": {"leaf node": actions.open_link},
    "cleanup": {"leaf node": actions.cleanup},
    "copy": {"leaf node": actions.copy_value},
    "rm": {"leaf node": actions.remove_key},
    "set": {"leaf node": actions.set_key},
    "update": {"leaf node": actions.update},

    # search commands.
    "search": {
        "leaf node": actions.search,
        "amazon": {"leaf node": lambda *q: actions.search("amazon", *q)},
        "gh": {"leaf node": lambda *q: actions.search("gh", *q)},
        "icons": {"leaf node": lambda *q: actions.search("icons", *q)},
        "images": {"leaf node": lambda *q: actions.search("images", *q)},
        "maps": {"leaf node": lambda *q: actions.search("maps", *q)},
        "scholar": {"leaf node": lambda *q: actions.search("scholar", *q)},
        "yt": {"leaf node": lambda *q: actions.search("yt", *q)},
    },
}
