"""Accessibility-tree extraction — the token-saving core of the service.

A raw DOM dump sent to an LLM carries every <div>, class, inline style,
script and tracking attribute. The accessibility tree carries only what a
user (and therefore an agent) can act on: role, accessible name, state and
value. On the demo pages in this repo that cuts the prompt by >55%
(measured by evals/measure_tokens.py and tests/test_a11y.py).

Two extractors live here:
  * ``snapshot_from_html`` — pure-Python (BeautifulSoup), used for tests,
    token measurement and any page source you already have.
  * Playwright's ``page.accessibility.snapshot()`` / locator ARIA snapshots
    are used live by the browser layer and normalised into the same shape.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

# Roles we keep. Everything else (generic wrappers, presentation) is pruned.
KEEP_ROLES = {
    "link", "button", "textbox", "searchbox", "checkbox", "radio", "combobox",
    "listbox", "option", "heading", "form", "navigation", "main", "article",
    "list", "listitem", "table", "row", "cell", "columnheader", "img",
    "switch", "slider", "spinbutton", "paragraph", "alert", "status",
}

_TAG_ROLE = {
    "a": "link", "button": "button", "input": "textbox", "textarea": "textbox",
    "select": "combobox", "option": "option", "nav": "navigation",
    "main": "main", "form": "form", "table": "table", "tr": "row",
    "td": "cell", "th": "columnheader", "img": "img", "ul": "list",
    "ol": "list", "li": "listitem", "article": "article",
    "h1": "heading", "h2": "heading", "h3": "heading", "h4": "heading",
    "h5": "heading", "h6": "heading", "p": "paragraph",
}

_INPUT_ROLE = {
    "checkbox": "checkbox", "radio": "radio", "submit": "button",
    "button": "button", "search": "searchbox", "number": "spinbutton",
    "range": "slider",
}


@dataclass
class A11yNode:
    role: str
    name: str = ""
    value: str = ""
    ref: str = ""          # stable selector the browser layer can act on
    disabled: bool = False
    checked: bool | None = None
    children: list["A11yNode"] = field(default_factory=list)

    def flatten(self) -> list["A11yNode"]:
        out = [self]
        for c in self.children:
            out.extend(c.flatten())
        return out


def _accessible_name(tag) -> str:
    for attr in ("aria-label", "placeholder", "title", "alt", "value"):
        if tag.get(attr):
            return str(tag[attr]).strip()
    if tag.get("id"):
        label = tag.find_parent().find("label", attrs={"for": tag["id"]}) if tag.find_parent() else None
        if label:
            return label.get_text(" ", strip=True)
    # Wrapping <label>
    parent_label = tag.find_parent("label")
    if parent_label:
        return parent_label.get_text(" ", strip=True)
    return tag.get_text(" ", strip=True)[:80]


def _ref_for(tag, index: int) -> str:
    if tag.get("id"):
        return f"#{tag['id']}"
    if tag.get("name"):
        return f"[name='{tag['name']}']"
    return f"{tag.name}:nth({index})"


def snapshot_from_html(html: str) -> A11yNode:
    """Build a pruned accessibility tree from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for junk in soup(["script", "style", "noscript", "svg", "head", "meta", "link"]):
        junk.decompose()

    root = A11yNode(role="document", name=(soup.title.string.strip() if soup.title and soup.title.string else "page"))
    counters: dict[str, int] = {}

    def walk(tag, parent: A11yNode) -> None:
        for child in getattr(tag, "children", []):
            if not getattr(child, "name", None):
                continue
            role = child.get("role") if child.get("role") else None
            if child.name == "input":
                role = _INPUT_ROLE.get((child.get("type") or "text").lower(), "textbox")
            role = role or _TAG_ROLE.get(child.name)
            if role in KEEP_ROLES:
                counters[child.name] = counters.get(child.name, 0) + 1
                node = A11yNode(
                    role=role,
                    name=_accessible_name(child) if role not in {"list", "navigation", "main", "table", "row"} else "",
                    value=str(child.get("value", "")),
                    ref=_ref_for(child, counters[child.name]),
                    disabled=child.has_attr("disabled"),
                    checked=True if child.has_attr("checked") else (False if role in {"checkbox", "radio"} else None),
                )
                parent.children.append(node)
                walk(child, node)
            else:
                walk(child, parent)  # prune wrapper, keep its children

    if soup.body:
        walk(soup.body, root)
    else:
        walk(soup, root)
    return root


def render_tree(node: A11yNode, depth: int = 0) -> str:
    """Compact text rendering — this exact string is what the LLM sees."""
    lines: list[str] = []

    def rec(n: A11yNode, d: int) -> None:
        parts = [n.role]
        if n.name:
            parts.append(f'"{n.name}"')
        if n.value:
            parts.append(f"value={n.value!r}")
        if n.checked is not None:
            parts.append(f"checked={str(n.checked).lower()}")
        if n.disabled:
            parts.append("disabled")
        if n.ref:
            parts.append(f"[{n.ref}]")
        lines.append("  " * d + " ".join(parts))
        for c in n.children:
            rec(c, d + 1)

    rec(node, depth)
    return "\n".join(lines)


def estimate_tokens(text: str) -> int:
    """Cheap, dependency-free token estimate (~4 chars/token for English/code).

    Good enough for a *ratio*; swap in tiktoken if you need exact billing counts.
    """
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def token_saving(html: str) -> dict:
    """Compare raw DOM vs accessibility tree for one page."""
    tree_text = render_tree(snapshot_from_html(html))
    raw = re.sub(r"\s+", " ", html).strip()
    raw_tokens, a11y_tokens = estimate_tokens(raw), estimate_tokens(tree_text)
    saving = 1 - (a11y_tokens / raw_tokens) if raw_tokens else 0.0
    return {
        "raw_dom_tokens": raw_tokens,
        "a11y_tokens": a11y_tokens,
        "saving_pct": round(saving * 100, 1),
        "tree": tree_text,
    }
