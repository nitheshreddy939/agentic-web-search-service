"""Playwright browser layer.

Every action is timed. The eval suite asserts each action stays under the
3-second budget from the resume (in practice local actions are 5–80 ms;
the budget covers real sites + an LLM planning call).
"""
from __future__ import annotations

import time

from playwright.async_api import Page, async_playwright

from ..a11y import estimate_tokens
from ..agent.types import Action, Node, Observation

# Extract an accessibility-style snapshot in-page: interactive + semantic
# elements only, with a stable selector for each. Scripts, styles, layout
# divs and attributes never leave the browser — that is the token saving.
_SNAPSHOT_JS = r"""
() => {
  const roleFor = (el) => {
    if (el.getAttribute('role')) return el.getAttribute('role');
    const t = el.tagName.toLowerCase();
    if (t === 'a') return 'link';
    if (t === 'button') return 'button';
    if (t === 'select') return 'combobox';
    if (t === 'textarea') return 'textbox';
    if (t === 'input') {
      const type = (el.getAttribute('type') || 'text').toLowerCase();
      if (type === 'checkbox') return 'checkbox';
      if (type === 'radio') return 'radio';
      if (type === 'submit' || type === 'button') return 'button';
      if (type === 'search') return 'searchbox';
      if (type === 'number') return 'spinbutton';
      return 'textbox';
    }
    if (/^h[1-6]$/.test(t)) return 'heading';
    if (t === 'form') return 'form';
    return null;
  };
  const nameFor = (el) => {
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label').trim();
    if (el.id) {
      const lab = document.querySelector(`label[for="${el.id}"]`);
      if (lab) return lab.innerText.trim();
    }
    const wrap = el.closest('label');
    if (wrap) return wrap.innerText.trim();
    if (el.getAttribute('placeholder')) return el.getAttribute('placeholder').trim();
    if (el.getAttribute('alt')) return el.getAttribute('alt').trim();
    return (el.innerText || el.value || '').trim().slice(0, 80);
  };
  const tagCounts = {};
  const refFor = (el) => {
    if (el.id) return '#' + el.id;
    if (el.getAttribute('name')) return `[name='${el.getAttribute('name')}']`;
    return el.tagName.toLowerCase() + ':nth-match';
  };
  const els = document.querySelectorAll(
    'a,button,input,select,textarea,h1,h2,h3,[role="button"],[role="link"],[role="checkbox"]'
  );
  const nodes = [];
  els.forEach((el, i) => {
    const tagKey = el.tagName.toLowerCase();
    const tagIndex = tagCounts[tagKey] || 0;
    tagCounts[tagKey] = tagIndex + 1;
    const role = roleFor(el);
    if (!role) return;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return;
    nodes.push({
      role, name: nameFor(el), ref: refFor(el),
      value: el.value !== undefined ? String(el.value) : '',
      checked: el.checked !== undefined ? !!el.checked : null,
      disabled: !!el.disabled,
      nth: tagIndex, tag: el.tagName.toLowerCase(),
    });
  });
  return { nodes, text: document.body ? document.body.innerText : '', title: document.title };
}
"""


def _locator(page: Page, node_ref: str, nodes: list[dict]):
    """Resolve our ref back to a Playwright locator."""
    for n in nodes:
        if n["ref"] == node_ref:
            if node_ref.startswith("#") or node_ref.startswith("[name="):
                return page.locator(node_ref).first
            return page.locator(n["tag"]).nth(n["nth"])
    return page.locator(node_ref).first


class BrowserSession:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw = None
        self._browser = None
        self.page: Page | None = None
        self._last_nodes: list[dict] = []

    async def __aenter__(self) -> "BrowserSession":
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        self.page = await self._browser.new_page()
        self.page.set_default_timeout(5000)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def goto(self, url: str) -> float:
        start = time.perf_counter()
        await self.page.goto(url, wait_until="domcontentloaded")
        return (time.perf_counter() - start) * 1000

    async def observe(self) -> Observation:
        snap = await self.page.evaluate(_SNAPSHOT_JS)
        html = await self.page.content()
        self._last_nodes = snap["nodes"]
        nodes = [Node(role=n["role"], name=n["name"], ref=n["ref"], value=n["value"],
                      checked=n["checked"], disabled=n["disabled"]) for n in snap["nodes"]]
        a11y_text = "\n".join(
            f'{n.role} "{n.name}" [{n.ref}]' + (f" value={n.value!r}" if n.value else "")
            for n in nodes
        )
        return Observation(
            url=self.page.url, title=snap["title"], text=snap["text"], nodes=nodes,
            a11y_text=a11y_text,
            raw_dom_tokens=estimate_tokens(html), a11y_tokens=estimate_tokens(a11y_text),
        )

    async def act(self, action: Action) -> float:
        """Execute one action, return its latency in ms."""
        start = time.perf_counter()
        page = self.page
        if action.kind == "goto":
            await page.goto(action.value, wait_until="domcontentloaded")
        elif action.kind == "fill":
            await _locator(page, action.ref, self._last_nodes).fill(action.value)
        elif action.kind == "select":
            await _locator(page, action.ref, self._last_nodes).select_option(label=action.value)
        elif action.kind == "check":
            loc = _locator(page, action.ref, self._last_nodes)
            want = action.value.lower() not in {"false", "no", "off"}
            if want:
                await loc.check()
            else:
                await loc.uncheck()
        elif action.kind == "click":
            await _locator(page, action.ref, self._last_nodes).click()
            await page.wait_for_load_state("domcontentloaded")
        elif action.kind == "press":
            await page.keyboard.press(action.value or "Enter")
        else:
            raise ValueError(f"Browser cannot execute: {action.kind}")
        return (time.perf_counter() - start) * 1000
