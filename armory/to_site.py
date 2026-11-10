"""DONE, DO NOT RERUN: the page is now convergentblue src/pages/bot/index.astro, merged with the bot console
(2026-11-10); rerunning would overwrite that. Edit the .astro file directly.

One-time port of armory.html (the claude.ai artifact template) to convergentblue.com/armory/.

    python armory/to_site.py ../convergentblue/src/pages/armory/index.astro

Scopes the template's CSS under .armory (the site's global.css owns body, h1/h2, .wrap, .card...), maps its palette onto
the site's tokens (item-quality colours stay: in D2 they mean something), drops its fonts for the site's, and wraps the
script so the data comes from /api/bot/armory instead of being baked in. After the port the site page is the template:
edit GOALS/FARMS/WANT there. build.py's own armory_built.html output is no longer used; only pagedata.json is.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path(__file__).with_name("armory.html")

PALETTE = """
.armory {
  --panel: var(--surface); --raise: var(--code-bg); --line: var(--rule); --fg: var(--ink); --mute: var(--muted);
  --line2: #cfcab9; --faint: #6b7282;
  --unique: #7a5f22; --set: #23731f; --rare: #756500; --magic: #2f4fb5; --rw: #a1500b; --normal: #3d3a35;
  --ok: #23722a; --bad: #b02a2a; --flash: #dfe2ff;
  --display: var(--sans); --body: var(--sans);
  font: 1rem/1.5 var(--sans);
}
.armory .top h1 { color: var(--ink) !important; letter-spacing: -0.01em; }
@media (prefers-color-scheme: dark) {
  .armory {
    --line2: #34405a; --faint: #8590a4;
    --unique: #d2b77f; --set: #63d660; --rare: #eedd5c; --magic: #93a3ff; --rw: #eda352; --normal: #ddd8cd;
    --ok: #7fd08a; --bad: #ff8a80; --flash: #26306a;
  }
}
"""


def split_rules(css: str):
    """Top-level (prelude, body) pairs; body of an @media block is returned raw for recursion."""
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        prelude = css[i:j].strip()
        depth, k = 1, j + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        out.append((prelude, css[j + 1:k - 1]))
        i = k
    return out


def scope_sel(sel: str) -> str | None:
    sel = sel.strip()
    if sel.startswith(("body::before",)):
        return None
    for root in (":root", "html", "body"):
        if sel == root or sel.startswith(root + "[") or sel.startswith(root + ":"):
            return None if root == ":root" else ".armory" + sel[len(root):]
    return f".armory {sel}"


def scope(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    for prelude, body in split_rules(css):
        if prelude.startswith("@keyframes"):
            out.append(f"{prelude}{{{body}}}")
        elif prelude.startswith("@media"):
            if "prefers-color-scheme" in prelude:
                continue  # the palette is redone in PALETTE
            inner = scope(body)
            if inner.strip():
                out.append(f"{prelude}{{{inner}}}")
        else:
            sels = [s for s in (scope_sel(x) for x in prelude.split(",")) if s]
            if sels:
                out.append(f"{','.join(sels)}{{{body}}}")
    return "\n".join(out)


def main(dest: str) -> None:
    s = SRC.read_text()
    css = s[s.index("<style>") + 7:s.index("</style>")]
    body = s[s.index("<body>") + 6:s.index("<script>")]
    js = s[s.index("<script>") + 8:s.rindex("</script>")]

    body = body.replace('<div class="wrap">', '<div class="wide armory">', 1)
    body = body.replace("<main>", '<div class="amain">', 1).replace("</main>", "</div>", 1)
    body = body.replace('<footer id="foot"></footer>', '<p class="afoot" id="foot"></p>', 1)
    css = css.replace("footer{", ".afoot{")
    assert "const D = __DATA__;" in js
    js = js.replace("const D = __DATA__;", "")
    js = js.replace(
        """<p><b>To refresh:</b> in Claude, open your scheduled tasks and hit <b>Run now</b> on <b>Update Armory</b> (or just say <code>update the armory</code>). It backs up your saves, rescans them, and refreshes this page and the copy in your Google Drive folder.</p>
    <p class="small">Your D2R folder needs to be connected, and the game saves on exit, so quit to the menu first for the freshest read.</p>""",
        """<p><b>Refreshes itself:</b> GLaDOS rescans a fresh backup of the saves each time the bot starts a session (every few hours) and sends the result here.</p>
    <p class="small">The game writes saves on exit, so items picked up in the current game show up after the next rescan.</p>""")

    page = f"""---
// Blizzaga's Armory: everything the D2R characters and shared stash hold, the Chronicle, cube recipes and goals.
// Ported from the claude.ai artifact by d2r-bot/armory/to_site.py; this file is now the template (GOALS, FARMS,
// WANT, MOVES, DITCH live in the script). Data: /api/bot/armory, uploaded by GLaDOS (worker/bot.js).
import Base from '../../layouts/Base.astro';
---
<Base title="Blizzaga's Armory" description="A Diablo II: Resurrected stash, Chronicle and cube planner, rebuilt from the save files." noindex>
<style is:global>
{PALETTE}
{scope(css)}
#aload {{ max-width: 72rem; margin: 0 auto; padding: 3rem 1rem; color: var(--muted); font-family: var(--sans); }}
</style>
{body.strip()}
<p id="aload">Loading the armory…</p>
<script is:inline>
(async () => {{
  let D;
  try {{
    const r = await fetch('/api/bot/armory');
    if (!r.ok) throw new Error(`HTTP ${{r.status}}`);
    D = await r.json();
  }} catch (e) {{
    document.getElementById('aload').textContent = `Couldn't load the armory data (${{e.message}}).`;
    return;
  }}
  document.getElementById('aload').remove();
{js}
}})();
</script>
</Base>
"""
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Path(dest).write_text(page)
    print(f"wrote {dest} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1])
