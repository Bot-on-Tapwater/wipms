"""Jinja2 template rendering for emails and printable reports."""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

template_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_template(name: str, context: dict) -> str:
    """
    Render the template at ``templates/<name>`` with the given context.

    Args:
        name (str): Template file name relative to ``app/templates``.
        context (dict): Values available inside the template.

    Returns:
        str: The rendered HTML.
    """
    return template_env.get_template(name).render(**context)
