"""The py-cli command tree.

Each edge is a key and each leaf is a callable under "leaf node". Adding a
command is adding a function and one line here. Search verticals are lambdas,
the way sofia's mapper had them.
"""

import typing

from clios import actions, capture

mapper: typing.Dict[str, typing.Any] = {
    "agenda": {"leaf node": capture.agenda},
    "bi": {"leaf node": capture.brain_inbox},
    "clone": {"leaf node": actions.clone},
    "code": {"leaf node": actions.open_in_code},
    "folder": {"leaf node": actions.open_folder},
    "folders": {"leaf node": actions.open_folder},
    "link": {"leaf node": actions.open_link},
    "links": {"leaf node": actions.open_link},
    "rm": {"leaf node": actions.remove_key},
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
    "set": {"leaf node": actions.set_key},
    "sop": {"leaf node": capture.sop},
    "study": {"leaf node": capture.study},
}
