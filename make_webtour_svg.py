"""Generate docs/webtour.svg — an animated guided tour of the Lumen Web UI.

Draws a stylized Lumen Web window, then walks a highlight + caption through
every feature, one step at a time, on a loop. Self-contained animated SVG
(CSS keyframes only); renders in browsers + GitHub READMEs.
Run:  python3 make_webtour_svg.py
"""

INK="#14110C"; CHROME="#1E1A13"; S2="#241F16"; LINE="#332B20"; PANEL="#0C0A07"
FG="#F1E9D8"; MUT="#A99C82"; M2="#7C7159"; GOLD="#F4B740"; HI="#FFD980"; SAFE="#4FD1C5"; RED="#E8806B"; GRN="#93D07E"
MONO="ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,monospace"
SANS="system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
W=1000; H=716


def esc(s): return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def rr(x,y,w,h,rx,fill,stroke=None,sw=1):
    s=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"'
    if stroke: s+=f' stroke="{stroke}" stroke-width="{sw}"'
    return s+"/>"

def tx(x,y,s,size,fill,font=MONO,weight="400",anchor="start",ls=0):
    a=f' text-anchor="{anchor}"' if anchor!="start" else ""
    l=f' letter-spacing="{ls}"' if ls else ""
    return f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}" font-weight="{weight}"{a}{l}>{esc(s)}</text>'


ui=[]
# window + header
ui.append(rr(6,6,W-12,616,14,INK,LINE,1))
ui.append(rr(6,6,W-12,46,14,CHROME))
ui.append(f'<rect x="6" y="30" width="{W-12}" height="22" fill="{CHROME}"/>')
ui.append(f'<line x1="6" y1="52" x2="{W-6}" y2="52" stroke="{LINE}"/>')
ui.append(f'<circle cx="30" cy="30" r="6" fill="{GOLD}"/>')
ui.append(tx(44,34,"lumen",14,FG,MONO,"700"))
ui.append(tx(92,34,"web",13,MUT))
# mode pill
ui.append(rr(150,17,206,26,13,"none",LINE))
ui.append(f'<circle cx="164" cy="30" r="4" fill="{GOLD}"/>')
ui.append(tx(176,34,"live · gpt-4o-mini",12.5,GOLD))
# header buttons
ui.append(rr(686,17,126,26,8,"none",LINE)); ui.append(tx(700,34,"🔒 airgap: off",12,MUT))
ui.append(rr(820,17,116,26,8,"none",LINE)); ui.append(tx(832,34,"⚙ connected",12,MUT))
ui.append(rr(944,17,50,26,8,"none",LINE)); ui.append(tx(958,34,"GH",12,MUT))
# left/right divider
ui.append(f'<line x1="452" y1="52" x2="452" y2="622" stroke="{LINE}"/>')
# tabs + run
ui.append(tx(28,80,"Files",12.5,FG,MONO,"700")); ui.append(tx(88,80,"Preview",12.5,MUT))
ui.append(rr(336,62,106,24,7,GOLD)); ui.append(tx(350,79,"▶ Run / Preview",11,INK,MONO,"700"))
# tree
ui.append(rr(14,94,152,222,8,S2))
files=[(".env",MUT),("README.md",MUT),("app.js",FG),("index.html",MUT),("style.css",MUT)]
for i,(f,c) in enumerate(files):
    y=112+i*26
    if f=="app.js": ui.append(rr(20,y-14,140,22,5,"rgba(244,183,64,0.12)"))
    ui.append(tx(30,y,("◦ " if "." in f else "▸ ")+f,12.5,c))
# editor
ui.append(rr(172,94,272,522,0,PANEL))
code=["var count = 0;",
      "var el = document.getElementById('cou…",
      "function render(){ el.textContent = c…",
      "document.getElementById('inc').oncl…",
      "document.getElementById('dec').oncl…",
      "render();"]
for i,l in enumerate(code):
    ui.append(tx(184,118+i*22,l,12,FG,MONO))
# right panel: agent
ui.append(tx(476,80,"agent",13,FG,MONO,"700"))
ui.append(rr(858,64,126,26,8,SAFE)); ui.append(tx(870,81,"✓ auto-approve",11,INK,MONO,"700"))
ui.append(tx(476,118,"lumen",12,GOLD,MONO,"700"))
ui.append(tx(476,138,"I’m an AI coding agent running entirely in your browser —",13.5,FG,SANS))
ui.append(tx(476,158,"your code and key never touch a server. Try a task below.",13.5,MUT,SANS))
# chips
chips=[("add a reset button",474,150),("make the counter step by 5",632,196),("read .env …",836,150)]
for t,x,w in chips:
    ui.append(rr(x,548,w,28,14,"none",LINE)); ui.append(tx(x+14,566,t,11.5,MUT))
# input + send
ui.append(rr(474,584,430,30,9,PANEL,LINE)); ui.append(tx(486,603,"Ask Lumen to build or change something…",12.5,M2,SANS))
ui.append(rr(912,584,74,30,9,GOLD)); ui.append(tx(933,603,"Send",12,INK,MONO,"700"))

# caption band bg
ui.append(rr(6,630,W-12,74,12,CHROME,LINE,1))

# ---- steps: (title, desc, (x,y,w,h)) ----
steps=[
 ("Mode","Live uses your OpenRouter key + any model. Demo mode needs no key at all.",(148,15,210,30)),
 ("Your key","Bring your own key — stored only in your browser, sent only to OpenRouter. Never to us.",(818,15,120,30)),
 ("Airgap","One click hard-blocks ALL network — your code physically cannot leave the machine.",(684,15,130,30)),
 ("Project files","A real in-browser project — the agent reads and edits these files directly.",(12,92,156,226)),
 ("Editor","See the code the agent writes, live, as it changes each file.",(170,92,276,222)),
 ("Run / Preview","Runs what you built live, right here in the browser — instant feedback.",(334,60,110,28)),
 ("The agent","Ask in plain English; it streams its reply and calls tools to read, edit and run.",(460,96,530,300)),
 ("Demo tasks","Zero-setup examples — click one and watch it work, no key needed.",(472,546,520,32)),
 ("Diff-approve","Every change shows as a diff — approve it, or let auto-approve apply it.",(856,62,130,30)),
 ("🛡 Secret Guard","Try “read .env” — Lumen blocks API keys from ever reaching the cloud.",(834,546,158,32)),
]

lead=1.1; dur=3.0; tail=1.6; total=lead+dur*len(steps)+tail
css=["@keyframes prog{0%{transform:scaleX(0)}100%{transform:scaleX(1)}}"]
ov=[]
for i,(title,desc,rect) in enumerate(steps):
    start=lead+i*dur; end=start+dur
    a=100*start/total; a2=min(a+0.7,99.5); b=100*end/total; b0=max(b-0.7,a2+0.1)
    nm=f"s{i}"
    css.append(f"@keyframes {nm}{{0%,{a:.2f}%{{opacity:0}}{a2:.2f}%,{b0:.2f}%{{opacity:1}}{b:.2f}%,100%{{opacity:0}}}}")
    x,y,w,h=rect
    ring=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="rgba(244,183,64,0.08)" stroke="{GOLD}" stroke-width="2.5" style="animation:{nm} {total}s linear infinite"/>'
    # caption group
    cap=(f'<g style="animation:{nm} {total}s linear infinite">'
         f'<circle cx="40" cy="668" r="16" fill="{GOLD}"/>'
         f'{tx(40,673,str(i+1),15,INK,MONO,"800","middle")}'
         f'{tx(68,662,f"STEP {i+1}/{len(steps)}  ·  {title}",13,GOLD,MONO,"700",0.4)}'
         f'{tx(68,687,desc,13.5,MUT,SANS)}'
         f'</g>')
    ov.append(ring); ov.append(cap)

svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<style>
{chr(10).join('  '+c for c in css)}
</style>
<rect width="{W}" height="{H}" fill="#0B0906"/>
{chr(10).join(ui)}
{chr(10).join(ov)}
<rect x="6" y="{H-6}" width="{W-12}" height="4" rx="2" fill="{LINE}"/>
<rect x="6" y="{H-6}" width="{W-12}" height="4" rx="2" fill="{GOLD}" style="transform-box:fill-box;transform-origin:left;animation:prog {total}s linear infinite"/>
</svg>'''

if __name__=="__main__":
    import os
    os.makedirs("docs",exist_ok=True)
    open("docs/webtour.svg","w",encoding="utf-8").write(svg)
    print(f"wrote docs/webtour.svg — {len(steps)} steps, {total:.1f}s loop, {len(svg)} bytes")
