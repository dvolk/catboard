import html
import re

import markdown2

pattern = (
    r"((([A-Za-z]{3,9}:(?:\/\/)?)"  # scheme
    r"(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:\[0-9]+)?"  # user@hostname:port
    r"|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)"  # www.|user@hostname
    r"((?:\/[\+~%\/\.\w\-_]*)?"  # path
    r"\??(?:[\-\+=&;%@\.\w_]*)"  # query parameters
    r"#?(?:[\.\!\/\\\w]*))?)"  # fragment
    r"(?![^<]*?(?:<\/\w+>|\/?>))"  # ignore anchor HTML tags
    r"(?![^\(]*?\))"  # ignore links in brackets (Markdown links and images)
)
link_patterns = [
    (re.compile(pattern), r"\1"),
    (re.compile("#(\d+)", re.I), r"/item/\1"),
]


def text_to_html(text):
    return markdown2.markdown(
        html.escape(text),
        extras=[
            "link-patterns",
            "wiki-tables",
            "task_list",
            "code-friendly",
            "cuddled-lists",
            "fenced-code-blocks",
            "break-on-newline",
        ],
        link_patterns=link_patterns,
    )
