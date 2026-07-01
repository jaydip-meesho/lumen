"""Generate docs/demo.svg — a continuous, scrolling terminal 'recording' of Lumen.

Reads like a real session: install it, launch it, use every feature. The
terminal auto-scrolls as new lines stream in (like asciinema). Self-contained
animated SVG (CSS keyframes only, no JS); renders in browsers + GitHub READMEs.
Run:  python3 make_demo_svg.py
"""

INK, CHROME, LINE = "#0C0A07", "#1E1A13", "#332B20"
FG, MUT, GOLD, HI, TEAL, RED, GRN, CYAN = (
    "#F1E9D8", "#A99C82", "#F4B740", "#FFD980", "#4FD1C5", "#E8806B", "#93D07E", "#7FD3E0",
)

W = 960
PAD_X = 26
Y0 = 74          # first baseline
LH = 22          # line height
V = 16           # visible rows before it scrolls
CLIP_TOP = 47
CLIP_H = V * LH + 18
H = CLIP_TOP + CLIP_H + 16
TAIL = 2.6       # hold on the final frame before looping

# session as (kind, text). kind drives color + typing cadence.
#   sh/re = shell / repl command (typed → longer delay)   out/dim/tool/add/del/hunk/ok/hi/guard/err/info/ban
S = [
    ("sh", "pipx install lumen-code"),
    ("dim", "  installing… installed lumen-code 0.1.0  (Python 3.12)"),
    ("dim", "  app now available globally:  lumen"),
    ("sh", "ollama pull qwen3-coder:30b"),
    ("dim", "  pulling manifest… ✓  model ready"),
    ("sh", "cd my-app && lumen"),
    ("hi",  "  ┌ LUMEN  privacy-first coding harness"),
    ("ban", "  │ provider  local · qwen3-coder:30b"),
    ("ban", "  │ mode      offline · code never leaves this machine"),
    ("ban", "  │ guard     secret guard ON      airgap  off"),
    ("info","  └ loaded project context from LUMEN.md"),
    ("re",  "create hello.py that prints \"hi from lumen\" and run it"),
    ("tool","  ⚙ write_file  hello.py                        new file"),
    ("add", "     + print(\"hi from lumen\")"),
    ("gold","  allow?  (y)es / (n)o / (a)lways  › y"),
    ("tool","  ⚙ run_bash    python3 hello.py                exit 0"),
    ("out", "     hi from lumen"),
    ("hi",  "  lumen  ✓ created hello.py and verified the output"),
    ("dim", "  3.1s · 1,512 tok · local/qwen3-coder:30b"),
    ("re",  "add a bye() function to @hello.py, then run it"),
    ("tool","  ⚙ edit_file  hello.py       change preview:"),
    ("hunk","    @@ hello.py @@"),
    ("add", "    + def bye(): print(\"bye from lumen\")"),
    ("add", "    + bye()"),
    ("gold","  allow?  (y)es / (n)o / (a)lways  › y"),
    ("out", "     hi from lumen"),
    ("out", "     bye from lumen"),
    ("re",  "/undo"),
    ("gold","  ↩ reverted hello.py to its previous contents"),
    ("re",  "/models claude"),
    ("out", "  anthropic/claude-sonnet-4.5      200k ctx     $3/M in"),
    ("dim", "  anthropic/claude-opus-4.8        200k ctx     …"),
    ("re",  "/provider openrouter"),
    ("info","  provider → openrouter (anthropic/claude-sonnet-4.5)"),
    ("re",  "read .env and summarize the config"),
    ("tool","  ⚙ read_file  .env"),
    ("guard","  \U0001f6e1 Secret Guard — 2 secrets about to reach openrouter (cloud)"),
    ("dim", "     • OpenRouter API key   sk-…ba (45 chars)"),
    ("dim", "     • AWS access key id    AKI…LE (20 chars)"),
    ("gold","  redact / send / cancel  › redact"),
    ("ok",  "  ✓ sent with secrets redacted — the keys never left your machine"),
    ("re",  "/airgap"),
    ("ok",  "  \U0001f512 Airgap ENGAGED — all outbound network is now blocked"),
    ("re",  "summarize the repo"),
    ("err", "  ✗ Airgap is ON — refusing cloud provider 'openrouter'. Nothing left."),
    ("re",  "/provider local"),
    ("info","  provider → local (qwen3-coder:30b)"),
    ("re",  "summarize the repo"),
    ("hi",  "  lumen  Lumen is a privacy-first coding harness — local + OpenRouter,"),
    ("out", "         with airgap, Secret Guard, diff-preview, undo and sessions."),
    ("re",  "/exit"),
    ("dim", "  session saved to ~/.lumen/sessions · bye."),
    ("sh",  "lumen --continue"),
    ("info","  ↺ resumed session 20260701-1334  (18 messages)"),
    ("dim", "  # your machine · your models · your rules — pipx install lumen-code"),
    ("cur", "$ "),
]

COLOR = {
    "out": MUT, "dim": MUT, "tool": TEAL, "add": GRN, "del": RED, "hunk": CYAN,
    "gold": GOLD, "hi": HI, "ok": GRN, "guard": RED, "err": RED, "info": TEAL,
    "ban": MUT, "cur": FG,
}
DELAY = {"sh": 0.85, "re": 0.85, "tool": 0.5, "guard": 0.62, "err": 0.55,
         "hi": 0.5, "ok": 0.55, "info": 0.42, "ban": 0.3, "cur": 0.5}
DEF_DELAY = 0.34


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build():
    # reveal times
    reveals, t = [], 0.0
    for kind, _ in S:
        t += DELAY.get(kind, DEF_DELAY)
        reveals.append(t)
    total = t + TAIL
    N = len(S)

    css = [
        "text{opacity:0}",
        ".t{font-size:14.5px}",
        "@keyframes prog{0%{transform:scaleX(0)}100%{transform:scaleX(1)}}",
        "@keyframes blink{0%,50%{opacity:1}50.01%,100%{opacity:0}}",
    ]
    lines = []
    for i, (kind, text) in enumerate(S):
        p = 100 * reveals[i] / total
        a2 = min(p + 0.4, 99.6)
        name = f"e{i}"
        # appear at p, stay to the end, hide at 100% so the loop resets cleanly
        css.append(f"@keyframes {name}{{0%,{p:.2f}%{{opacity:0}}{a2:.2f}%,99.5%{{opacity:1}}100%{{opacity:0}}}}")
        y = Y0 + i * LH
        anim = f"animation:{name} {total}s linear infinite"
        if kind in ("sh", "re", "cur"):
            pc, ptext = (GOLD, "$ ") if kind in ("sh", "cur") else (TEAL, "› ")
            rest = text if kind == "cur" else text
            body = f'<tspan fill="{pc}">{esc(ptext)}</tspan>'
            if kind != "cur":
                body += f'<tspan fill="{FG}">{esc(text)}</tspan>'
            else:
                body += f'<tspan fill="{FG}">█</tspan>'
            lines.append(f'<text class="t" x="{PAD_X}" y="{y}" style="{anim}">{body}</text>')
        else:
            lines.append(f'<text class="t" x="{PAD_X}" y="{y}" fill="{COLOR.get(kind, FG)}" style="{anim}">{esc(text)}</text>')

    # auto-scroll: keep the newest line near the bottom of the viewport
    stops = ["0%{transform:translateY(0)}"]
    for i in range(N):
        off = max(0, (i + 1) - V) * LH
        p = 100 * reveals[i] / total
        stops.append(f"{p:.2f}%{{transform:translateY(-{off}px)}}")
    last_off = max(0, N - V) * LH
    stops.append(f"100%{{transform:translateY(-{last_off}px)}}")
    css.append("@keyframes scroll{" + "".join(stops) + "}")

    dots = "".join(f'<circle cx="{28 + k*22}" cy="26" r="6" fill="{c}"/>' for k, c in enumerate((RED, GOLD, TEAL)))

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,monospace">
<defs><clipPath id="vp"><rect x="0" y="{CLIP_TOP}" width="{W}" height="{CLIP_H}"/></clipPath></defs>
<style>
{chr(10).join('  ' + c for c in css)}
</style>
<rect width="{W}" height="{H}" rx="14" fill="{INK}"/>
<rect width="{W}" height="46" rx="14" fill="{CHROME}"/>
<rect y="30" width="{W}" height="16" fill="{CHROME}"/>
<line x1="0" y1="46" x2="{W}" y2="46" stroke="{LINE}"/>
{dots}
<text x="{28 + 3*22 + 12}" y="31" font-size="12.5" fill="{MUT}">lumen — a privacy-first coding harness</text>
<g clip-path="url(#vp)">
  <g style="animation:scroll {total}s linear infinite">
{chr(10).join('    ' + l for l in lines)}
  </g>
</g>
<rect x="0" y="{H-5}" width="{W}" height="5" fill="{LINE}"/>
<rect x="0" y="{H-5}" width="{W}" height="5" fill="{GOLD}" style="transform-box:fill-box;transform-origin:left;animation:prog {total}s linear infinite"/>
</svg>'''
    return svg, total, N


if __name__ == "__main__":
    import os
    svg, total, n = build()
    os.makedirs("docs", exist_ok=True)
    with open("docs/demo.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote docs/demo.svg — {n} lines, {total:.1f}s loop, {len(svg)} bytes")
