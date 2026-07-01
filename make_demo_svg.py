"""Generate docs/demo.svg — an animated terminal 'recording' of Lumen.

Self-contained animated SVG (CSS keyframes only, no JS) that plays the full
feature tour on a loop. Renders in browsers and GitHub READMEs; screen-record
it if you need an .mp4/.gif.
Run:  python3 make_demo_svg.py
"""

# palette (matches the site / deck)
INK, CHROME, LINE = "#0C0A07", "#1E1A13", "#332B20"
FG, MUT, GOLD, HI, TEAL, RED, GRN, CYAN = (
    "#F1E9D8", "#A99C82", "#F4B740", "#FFD980", "#4FD1C5", "#E8806B", "#8FCf7f", "#7FD3E0",
)

W, H = 940, 600
BODY_X, BODY_TOP, LH = 30, 118, 24
LABEL_Y = 86

# Each scene: (label, dwell_seconds, [(text, color), ...])  ·  c=center, big=first line big
SCENES = [
    ("LUMEN · privacy-first coding harness", 3.0, [
        ("$ pipx install lumen-code", MUT),
        ("$ lumen", FG),
        ("  provider   local · qwen3-coder:30b", TEAL),
        ("  mode       offline · code never leaves this machine", TEAL),
        ("  guard      secret guard ON      airgap  off", MUT),
    ]),
    ("1 · OFFLINE BUILD  —  no internet, no limits", 5.0, [
        ("› build hello.py that prints \"hi from lumen\", then run it", FG),
        ("  ⚙ write_file  hello.py                        new file", TEAL),
        ("     + print(\"hi from lumen\")", GRN),
        ("  ⚙ run_bash    python3 hello.py                exit 0", TEAL),
        ("     hi from lumen", MUT),
        ("  lumen  ✓ created hello.py and verified the output", HI),
    ]),
    ("2 · SEE EVERY CHANGE  —  diff preview + undo", 5.6, [
        ("› add a farewell line and run it again", FG),
        ("  ⚙ edit_file  hello.py         change preview:", TEAL),
        ("    @@ hello.py @@", CYAN),
        ("    + print(\"bye from lumen\")", GRN),
        ("  allow?  (y)es / (n)o / (a)lways  ▸ y", GOLD),
        ("     hi from lumen", MUT),
        ("     bye from lumen", MUT),
        ("› /undo", FG),
        ("  ↩ reverted hello.py to its previous contents", GOLD),
    ]),
    ("3 · PROVABLE PRIVACY  —  airgap mode", 5.0, [
        ("› /airgap", FG),
        ("  \U0001f512 Airgap ENGAGED — all network egress blocked", GRN),
        ("$ lumen -p openrouter \"summarize this repo\"", FG),
        ("  ✗ Airgap is ON — refusing cloud provider 'openrouter'.", RED),
        ("    Nothing left the machine.", RED),
    ]),
    ("4 · SECRET GUARD  —  keys never leak to the cloud", 6.2, [
        ("$ lumen -p openrouter", FG),
        ("› read .env and tell me what's configured", FG),
        ("  ⚙ read_file  .env", TEAL),
        ("  \U0001f6e1 Secret Guard — 2 secrets about to reach openrouter", RED),
        ("     • OpenRouter API key   sk-…ba (45 chars)", MUT),
        ("     • AWS access key id    AKI…LE (20 chars)", MUT),
        ("  redact / send / cancel  ▸ cancel", GOLD),
        ("  ✗ Cancelled — nothing was sent.", RED),
    ]),
    ("5 · YOUR KEY, THE WHOLE CATALOGUE  +  local sessions", 5.2, [
        ("› /models claude", FG),
        ("  anthropic/claude-sonnet-4.5      200k ctx     $3/M in", FG),
        ("  anthropic/claude-opus-4.8        200k ctx     …", MUT),
        ("› /model anthropic/claude-sonnet-4.5        model set", TEAL),
        ("$ lumen --continue      ↺ resumed local session (8 msgs)", TEAL),
    ]),
    ("", 3.4, [
        ("LUMEN", HI),
        ("your machine  ·  your models  ·  your rules", FG),
        ("pipx install lumen-code", GOLD),
        ("github.com/jaydip-meesho/lumen", MUT),
    ]),
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build() -> str:
    total = sum(s[1] for s in SCENES)
    css = [
        f"@keyframes prog{{0%{{transform:scaleX(0)}}100%{{transform:scaleX(1)}}}}",
        f"@keyframes blink{{0%,55%{{opacity:1}}55.01%,100%{{opacity:0}}}}",
    ]
    els = []
    gid = 0
    t = 0.0
    last_idx = len(SCENES) - 1
    for si, (label, dur, lines) in enumerate(SCENES):
        s_start, s_end = t, t + dur
        endcard = (si == last_idx)
        # keyframe helper: visible from `rev` until scene end, hidden otherwise
        def kf(rev):
            nonlocal gid
            a = 100 * rev / total
            a2 = min(a + 0.4, 99.9)
            b = 100 * (s_end - 0.25) / total
            b2 = 100 * s_end / total
            if endcard:
                b, b2 = 99.7, 100.0  # hold on the end card, then loop
            name = f"e{gid}"; gid += 1
            css.append(
                f"@keyframes {name}{{0%,{a:.2f}%{{opacity:0}}{a2:.2f}%,{b:.2f}%"
                f"{{opacity:1}}{b2:.2f}%,100%{{opacity:0}}}}"
            )
            return name

        # scene label
        if label:
            n = kf(s_start + 0.05)
            els.append(
                f'<text x="{BODY_X}" y="{LABEL_Y}" class="lbl" fill="{GOLD}" '
                f'style="animation:{n} {total}s linear infinite">{esc(label)}</text>'
            )
        step = min(0.45, max(0.28, (dur - 1.1) / max(1, len(lines))))
        for i, (text, color) in enumerate(lines):
            rev = min(s_start + 0.35 + i * step, s_end - 0.5)
            n = kf(rev)
            if endcard:
                cx = W / 2
                if i == 0:
                    els.append(
                        f'<text x="{cx}" y="248" class="big" fill="{color}" '
                        f'text-anchor="middle" style="animation:{n} {total}s linear infinite">{esc(text)}</text>'
                    )
                else:
                    y = 300 + i * 34
                    els.append(
                        f'<text x="{cx}" y="{y}" class="ctr" fill="{color}" '
                        f'text-anchor="middle" style="animation:{n} {total}s linear infinite">{esc(text)}</text>'
                    )
            else:
                y = BODY_TOP + i * LH
                els.append(
                    f'<text x="{BODY_X}" y="{y}" class="ln" fill="{color}" '
                    f'style="animation:{n} {total}s linear infinite">{esc(text)}</text>'
                )
        t = s_end

    dots = "".join(
        f'<circle cx="{28 + k * 22}" cy="26" r="6" fill="{c}"/>'
        for k, c in enumerate((RED, GOLD, TEAL))
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,monospace">
<style>
  .ln{{font-size:14.5px}}
  .lbl{{font-size:12px;letter-spacing:2px;font-weight:700}}
  .big{{font-size:64px;font-weight:800;letter-spacing:2px}}
  .ctr{{font-size:17px}}
  text{{opacity:0}}
  {chr(10).join('  ' + c for c in css)}
</style>
<rect width="{W}" height="{H}" rx="14" fill="{INK}"/>
<rect width="{W}" height="46" rx="14" fill="{CHROME}"/>
<rect y="30" width="{W}" height="16" fill="{CHROME}"/>
<line x1="0" y1="46" x2="{W}" y2="46" stroke="{LINE}"/>
{dots}
<text x="{28 + 3 * 22 + 14}" y="31" font-size="12.5" fill="{MUT}">lumen — demo</text>
{chr(10).join(els)}
<rect x="0" y="{H-5}" width="{W}" height="5" fill="{LINE}"/>
<rect x="0" y="{H-5}" width="{W}" height="5" fill="{GOLD}" style="transform-box:fill-box;transform-origin:left;animation:prog {total}s linear infinite"/>
</svg>'''
    return svg


if __name__ == "__main__":
    import os
    os.makedirs("docs", exist_ok=True)
    out = build()
    with open("docs/demo.svg", "w", encoding="utf-8") as f:
        f.write(out)
    print(f"wrote docs/demo.svg ({len(out)} bytes)")
