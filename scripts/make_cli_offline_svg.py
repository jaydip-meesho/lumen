"""Generate docs/cli-offline.svg — a scrolling terminal recording of the Lumen
CLI running fully offline, with airgap blocking real network at the socket layer.

This is the one capability the browser app structurally cannot run (a browser
can't host a local LLM or patch sockets), so it's shown as a clearly-labeled
recording. Self-contained animated SVG (CSS keyframes only).
Run:  python3 make_cli_offline_svg.py
"""

INK, CHROME, LINE, PANEL = "#0C0A07", "#1E1A13", "#332B20", "#0B0906"
FG, MUT, GOLD, HI, TEAL, RED, GRN = "#F1E9D8", "#A99C82", "#F4B740", "#FFD980", "#4FD1C5", "#E8806B", "#93D07E"
MONO = "ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,monospace"

W = 960
PAD_X = 26
Y0 = 74
LH = 22
V = 16
CLIP_TOP = 47
CLIP_H = V * LH + 18
H = CLIP_TOP + CLIP_H + 16
TAIL = 2.6

S = [
    ("sh",  "pipx install lumen-code"),
    ("dim", "  installed lumen-code 0.1.0 · the coding agent that runs on your machine"),
    ("sh",  "lumen"),
    ("hi",  "  ┌ LUMEN   local · qwen3-coder:30b · offline"),
    ("dim", "  └ your code never leaves this machine"),
    ("re",  "write fib.py that prints the first 10 Fibonacci numbers, then run it"),
    ("tool","  ⚙ write_file  fib.py                          new file"),
    ("add", "     + def fib(n):"),
    ("add", "     +     a, b = 0, 1"),
    ("add", "     +     for _ in range(n): print(a, end=' '); a, b = b, a+b"),
    ("tool","  ⚙ run_bash    python3 -c 'import fib; fib.fib(10)'   exit 0"),
    ("out", "     0 1 1 2 3 5 8 13 21 34"),
    ("hi",  "  lumen  ✓ done — fully offline, not one byte left this machine"),
    ("re",  "/airgap"),
    ("ok",  "  🔒 Airgap ENGAGED — socket layer now blocks every non-loopback connection"),
    ("re",  "/provider openrouter"),
    ("re",  "summarize this repository"),
    ("err", "  ✗ airgap: blocked outbound connection to ('openrouter.ai', 443)"),
    ("err", "    nothing left the machine."),
    ("dim", "  # proof — even a raw socket call is refused at the OS layer:"),
    ("sh",  "python3 -c \"import socket; socket.create_connection(('1.1.1.1',443))\""),
    ("err", "  lumen.airgap.AirgapBlocked: blocked outbound connection to ('1.1.1.1', 443)"),
    ("dim", "  # local still works with airgap ON — it's on localhost, which is allowed:"),
    ("re",  "add a docstring to fib.py"),
    ("tool","  ⚙ edit_file  fib.py                           1 replaced"),
    ("hi",  "  lumen  ✓ done — offline, airgap ON, your code physically cannot leave"),
    ("cur", "$ "),
]

COLOR = {"out": MUT, "dim": MUT, "tool": TEAL, "add": GRN, "ok": GRN, "hi": HI, "err": RED, "cur": FG}
DELAY = {"sh": 0.85, "re": 0.85, "tool": 0.5, "ok": 0.6, "hi": 0.55, "err": 0.5, "cur": 0.5}
DEF_DELAY = 0.34


def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build():
    reveals, t = [], 0.0
    for kind, _ in S:
        t += DELAY.get(kind, DEF_DELAY); reveals.append(t)
    total = t + TAIL
    N = len(S)
    css = ["text{opacity:0}", ".t{font-size:14.5px}",
           "@keyframes prog{0%{transform:scaleX(0)}100%{transform:scaleX(1)}}"]
    lines = []
    for i, (kind, text) in enumerate(S):
        p = 100 * reveals[i] / total
        a2 = min(p + 0.4, 99.6)
        nm = f"e{i}"
        css.append(f"@keyframes {nm}{{0%,{p:.2f}%{{opacity:0}}{a2:.2f}%,99.5%{{opacity:1}}100%{{opacity:0}}}}")
        y = Y0 + i * LH
        anim = f"animation:{nm} {total}s linear infinite"
        if kind in ("sh", "re", "cur"):
            pc, pt = (GOLD, "$ ") if kind in ("sh", "cur") else (TEAL, "› ")
            body = f'<tspan fill="{pc}">{esc(pt)}</tspan>'
            body += f'<tspan fill="{FG}">{"█" if kind=="cur" else esc(text)}</tspan>'
            lines.append(f'<text class="t" x="{PAD_X}" y="{y}" style="{anim}">{body}</text>')
        else:
            lines.append(f'<text class="t" x="{PAD_X}" y="{y}" fill="{COLOR.get(kind, FG)}" style="{anim}">{esc(text)}</text>')

    stops = ["0%{transform:translateY(0)}"]
    for i in range(N):
        off = max(0, (i + 1) - V) * LH
        stops.append(f"{100*reveals[i]/total:.2f}%{{transform:translateY(-{off}px)}}")
    stops.append(f"100%{{transform:translateY(-{max(0,N-V)*LH}px)}}")
    css.append("@keyframes scroll{" + "".join(stops) + "}")

    dots = "".join(f'<circle cx="{28+k*22}" cy="26" r="6" fill="{c}"/>' for k, c in enumerate((RED, GOLD, TEAL)))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{MONO}">
<defs><clipPath id="vp"><rect x="0" y="{CLIP_TOP}" width="{W}" height="{CLIP_H}"/></clipPath></defs>
<style>
{chr(10).join('  '+c for c in css)}
</style>
<rect width="{W}" height="{H}" rx="14" fill="{PANEL}"/>
<rect width="{W}" height="46" rx="14" fill="{CHROME}"/>
<rect y="30" width="{W}" height="16" fill="{CHROME}"/>
<line x1="0" y1="46" x2="{W}" y2="46" stroke="{LINE}"/>
{dots}
<text x="{28+3*22+12}" y="31" font-size="12.5" fill="{MUT}">lumen — local · offline · airgap (recording)</text>
<g clip-path="url(#vp)">
  <g style="animation:scroll {total}s linear infinite">
{chr(10).join('    '+l for l in lines)}
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
    open("docs/cli-offline.svg", "w", encoding="utf-8").write(svg)
    print(f"wrote docs/cli-offline.svg — {n} lines, {total:.1f}s loop, {len(svg)} bytes")
