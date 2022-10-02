"""Markdown text to html conversion module."""

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

# the first element should be the pattern matching common urls as this is
# used by the app to generate the links section on the item page.
link_patterns = [
    (re.compile(pattern), r"\1"),
    (re.compile(r"#(\d+)", re.I), r"/item/\1"),
]


def text_to_html(text):
    """Turn markdown text into html, plus some useful extensions."""
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
