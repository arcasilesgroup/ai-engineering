"""Source of truth for the README user-facing diagrams (spec-177).

Renders branded HTML "figures" at README-native width (920px CSS, x2 for retina)
so labels stay legible at GitHub's ~880px column. Output PNGs land in
.github/assets/diagrams/. Re-render in CI on change (never on the hot path).

Render:  python docs/architecture/diagrams/build_diagrams.py  -> /tmp/diagrams/*.html
then screenshot each at --force-device-scale-factor=2 and trim.
Icons: Fluent UI System Icons (MIT, Microsoft), discovered via svgicons.com.
"""

import os

OUT = "/tmp/diagrams"
os.makedirs(OUT, exist_ok=True)

# Fluent shield-checkmark (MIT) recoloured to brand teal — the "governed approval" mark.
SHIELD = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" style="display:block;margin:0 auto 4px">'
    '<path d="M3 5.75C3 5.33579 3.33579 5 3.75 5C6.41341 5 9.00797 4.05652 11.55 2.15C11.8167 1.95 12.1833 1.95 12.45 2.15C14.992 4.05652 17.5866 5 20.25 5C20.6642 5 21 5.33579 21 5.75V11C21 11.3381 20.9865 11.6701 20.9595 11.9961C20.5062 11.7106 20.0152 11.4795 19.4955 11.3121C19.4985 11.2087 19.5 11.1047 19.5 11V6.47793C16.9227 6.32585 14.4192 5.38829 12 3.67782C9.58084 5.38829 7.07735 6.32585 4.5 6.47793V11C4.5 15.1488 6.83178 18.2214 11.625 20.2846C11.8882 20.839 12.2276 21.3503 12.6297 21.8048C12.5126 21.8531 12.3944 21.9007 12.2749 21.9478C12.0982 22.0174 11.9018 22.0174 11.7251 21.9478C5.95756 19.6757 3 16.0012 3 11V5.75ZM23 17.5C23 20.5376 20.5376 23 17.5 23C14.4624 23 12 20.5376 12 17.5C12 14.4624 14.4624 12 17.5 12C20.5376 12 23 14.4624 23 17.5ZM20.8536 15.1464C20.6583 14.9512 20.3417 14.9512 20.1464 15.1464L16.5 18.7929L14.8536 17.1464C14.6583 16.9512 14.3417 16.9512 14.1464 17.1464C13.9512 17.3417 13.9512 17.6583 14.1464 17.8536L16.1464 19.8536C16.3417 20.0488 16.6583 20.0488 16.8536 19.8536L20.8536 15.8536C21.0488 15.6583 21.0488 15.3417 20.8536 15.1464Z" fill="#00D4AA"/></svg>'
)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');
*{margin:0;padding:0;box-sizing:border-box}html,body{background:transparent}
.fig{width:920px;position:relative;background:linear-gradient(180deg,#0E1A30,#0A0F1C);
 border:1px solid #2EB39A;border-radius:18px;padding:42px 40px 38px;
 font-family:'JetBrains Mono','SF Mono',monospace;color:#F8FAFB;overflow:hidden}
.fig::before{content:"";position:absolute;inset:0;background:
 linear-gradient(rgba(255,255,255,.7) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.7) 1px,transparent 1px);
 background-size:92px 92px;opacity:.025;pointer-events:none}
.glow{position:absolute;border-radius:50%;filter:blur(60px);opacity:.18;background:#00D4AA;pointer-events:none}
.node{border:1px solid #2EB39A;background:rgba(255,255,255,.025);border-radius:13px;padding:16px 14px;text-align:center;flex:1}
.k{font-weight:600;font-size:17px}.s{color:#9DB2C9;font-size:12.5px;margin-top:6px;line-height:1.5}
.focal{border:1.5px solid #00D4AA;background:rgba(0,212,170,.10);box-shadow:0 0 55px rgba(0,212,170,.16)}
.arr{flex:0 0 auto;width:44px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#00D4AA}
.arr .ln{width:44px;height:2px;background:#00D4AA;opacity:.85;position:relative}
.arr .ln::after{content:"";position:absolute;right:-1px;top:-5px;border-left:9px solid #00D4AA;border-top:6px solid transparent;border-bottom:6px solid transparent}
.checks{margin-top:24px;border:1px solid #2EB39A;border-radius:13px;padding:15px 20px;display:flex;align-items:center;gap:16px;background:rgba(0,212,170,.045)}
.cap{color:#9DB2C9;font-size:13px;margin-top:18px;text-align:center}
.tag{color:#00D4AA;font-weight:700}.prompt{color:#00D4AA;font-weight:700;margin-right:10px}.cmd{font-size:17px}
.kick{color:#00D4AA;font-size:12px;letter-spacing:2.5px;font-weight:600;text-transform:uppercase}
"""


def page(name, inner):
    open(f"{OUT}/{name}.html", "w").write(
        f"""<!doctype html><meta charset=utf-8><style>{CSS}</style><div class="fig">{inner}</div>"""
    )
    print("wrote", name)


def node(k, s, focal=False):
    return f'<div class="node {"focal" if focal else ""}"><div class="k">{k}</div><div class="s">{s}</div></div>'


def arr(approve=False):
    return f'<div class="arr">{SHIELD if approve else ""}<div class="ln"></div></div>'


# ── workflow ──────────────────────────────────────────────────────────────
workflow = f"""
<div class="glow" style="width:320px;height:190px;left:50%;top:-40px;transform:translateX(-50%)"></div>
<div style="display:flex;align-items:center">
  {node("/ai-brainstorm", "agree the spec")}{arr(True)}
  {node("/ai-plan", "break it down")}{arr(True)}
  {node("/ai-build", "or /ai-autopilot", True)}{arr(False)}
  {node("/ai-pr", "reviewed &amp; merged")}
</div>
<div class="checks">
  <span class="tag" style="font-size:15px;flex:0 0 auto">[PASS]&nbsp;before merge</span>
  <span style="color:#9DB2C9;font-size:13.5px">every change is checked automatically &mdash; clean diff &middot; tests green &middot; docs updated &middot; reviewed</span>
</div>
<div class="cap">From your idea to a merged pull request &mdash; you approve every step, the checks catch the rest.</div>
"""
page("workflow", workflow)


# ── install ───────────────────────────────────────────────────────────────
def cmdrow(c, note=""):
    n = f'<span style="color:#5E7796;font-size:13px;margin-left:14px">{note}</span>' if note else ""
    return f'<div style="display:flex;align-items:center;padding:13px 0"><span class="prompt">$</span><span class="cmd">{c}</span>{n}</div>'


def get(t, s):
    return f'<div style="padding:9px 0"><div class="k" style="font-size:15.5px">{t}</div><div class="s" style="margin-top:3px">{s}</div></div>'


install = f"""
<div class="glow" style="width:300px;height:200px;left:60px;top:40px"></div>
<div style="display:flex;gap:40px">
  <div style="flex:1.25">
    <div class="kick" style="margin-bottom:6px">install in seconds</div>
    {cmdrow("pip install ai-engineering")}
    {cmdrow("ai-eng install .", "adds governance to your repo")}
    {cmdrow("ai-eng doctor", '&rarr; <b style="color:#00D4AA">[PASS]</b>')}
    <div class="s" style="margin-top:10px">then open your IDE and type <span class="tag">/ai-start</span></div>
  </div>
  <div style="flex:1;border-left:1px solid #1E3A4F;padding-left:34px">
    <div class="kick" style="margin-bottom:10px">what you get</div>
    {get("53 skills &middot; 9 agents", "run /ai-&lt;name&gt; in your editor")}
    {get("a governed workflow", "spec &rarr; plan &rarr; build &rarr; reviewed PR")}
    {get("automatic checks", "clean diffs, fresh docs, on every change")}
    {get("versioned local files", "no cloud, no lock-in, you own it all")}
  </div>
</div>
<div class="cap">One command turns any repository into a governed, AI-ready workspace.</div>
"""
page("install", install)


# ── toolkit ───────────────────────────────────────────────────────────────
def cap_card(t, s):
    return f'<div class="node" style="padding:15px 17px;text-align:left"><div class="k" style="font-size:16px">{t}</div><div class="s">{s}</div></div>'


chip = lambda s: (
    f'<div style="border:1px solid #2EB39A;border-radius:9px;padding:10px 0;text-align:center;font-size:14px;font-weight:500">{s}</div>'
)
toolkit = f"""
<div class="glow" style="width:280px;height:190px;left:60px;top:40px"></div>
<div style="display:flex;gap:36px;align-items:center">
  <div style="flex:0 0 250px">
    <div style="font-size:58px;font-weight:700;color:#00D4AA;line-height:.95">53</div>
    <div class="k" style="font-size:19px;margin-top:2px">skills</div>
    <div style="font-size:40px;font-weight:700;color:#00D4AA;line-height:1;margin-top:16px">9</div>
    <div class="k" style="font-size:19px;margin-top:2px">agents</div>
    <div class="s" style="margin-top:14px">invoke any with <span class="tag">/ai-&lt;name&gt;</span></div>
  </div>
  <div style="flex:1;display:grid;grid-template-columns:repeat(2,1fr);gap:12px">
    {cap_card("Plan &amp; build", "brainstorm &middot; plan &middot; build &middot; autopilot")}
    {cap_card("Ship safely", "review &middot; verify &middot; test &middot; security")}
    {cap_card("Design &amp; docs", "design &middot; visual &middot; slides &middot; docs")}
    {cap_card("Research &amp; learn", "research &middot; explore &middot; explain &middot; note")}
  </div>
</div>
<div style="margin-top:20px"><div class="kick" style="margin-bottom:10px">same commands in every editor</div>
<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px">
{chip("Claude Code")}{chip("Copilot")}{chip("Codex")}{chip("Antigravity")}{chip("OpenCode")}{chip("Cursor")}</div></div>
"""
page("toolkit", toolkit)
print("done")
