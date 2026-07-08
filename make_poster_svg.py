"""Generate docs/poster.svg — a one-panel announcement poster for Lumen.

Static, self-contained SVG (open in a browser and screenshot to PNG for Slack).
Run:  python3 make_poster_svg.py
"""

import math
INK="#14110C"; PANEL="#1E1A13"; S2="#241F16"; LINE="#332B20"
GOLD="#F4B740"; HI="#FFD980"; TEAL="#4FD1C5"; FG="#F1E9D8"; MUT="#A99C82"; M2="#7C7159"; RED="#E8806B"; GRN="#93D07E"
MAG="#E01E8B"
MONO="ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,monospace"
SANS="'Helvetica Neue',Helvetica,Arial,sans-serif"
W=1000; H=1250


def esc(s): return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def rr(x,y,w,h,rx,fill,stroke=None,sw=1.5):
    s=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"'
    if stroke: s+=f' stroke="{stroke}" stroke-width="{sw}"'
    return s+"/>"

def tx(x,y,s,size,fill,font=SANS,weight="400",anchor="start",ls=0):
    a=f' text-anchor="{anchor}"' if anchor!="start" else ""
    l=f' letter-spacing="{ls}"' if ls else ""
    return f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}" font-weight="{weight}"{a}{l}>{esc(s)}</text>'

E=[]
# background + ambient glow
E.append(f'<rect width="{W}" height="{H}" fill="{INK}"/>')
E.append(f'<defs><radialGradient id="g" cx="82%" cy="0%" r="70%"><stop offset="0%" stop-color="{GOLD}" stop-opacity="0.16"/><stop offset="60%" stop-color="{GOLD}" stop-opacity="0"/></radialGradient></defs>')
E.append(f'<rect width="{W}" height="{H}" fill="url(#g)"/>')

# ---- header ----
E.append(rr(40,40,920,232,20,PANEL,LINE,1.5))
# meesho m badge
E.append(f'<circle cx="898" cy="82" r="22" fill="{MAG}"/>')
E.append(tx(898,90,"m",26,"#fff",SANS,"800","middle"))
E.append(tx(898,124,"BUILDATHON ’26",10,M2,MONO,"700","middle",1.5))
# logomark — a glowing aperture (lumen = a unit of light)
lx,ly=84,102
E.append(rr(58,76,52,52,14,S2,GOLD,1.5))
for k in range(8):
    a=math.radians(k*45)
    E.append(f'<line x1="{lx+15*math.cos(a):.1f}" y1="{ly+15*math.sin(a):.1f}" x2="{lx+21*math.cos(a):.1f}" y2="{ly+21*math.sin(a):.1f}" stroke="{GOLD}" stroke-width="2" stroke-linecap="round"/>')
E.append(f'<circle cx="{lx}" cy="{ly}" r="12" fill="none" stroke="{GOLD}" stroke-width="2.5"/>')
E.append(f'<circle cx="{lx}" cy="{ly}" r="5" fill="{HI}"/>')
# wordmark
E.append(tx(128,114,"lumen",46,GOLD,SANS,"800"))
E.append(tx(130,142,"privacy-first AI coding agent",16,MUT,MONO))
# tagline
E.append(tx(72,205,"Your code. Your machine.",38,FG,SANS,"800"))
E.append(tx(72,205+46,"Your rules.",38,GOLD,SANS,"800"))
# sub
E.append(tx(72,268,"Runs local & offline, or on your own OpenRouter key — nothing leaves your machine.",17,MUT,SANS))
# try-live pill (below header)
E.append(rr(40,292,640,50,12,GOLD))
E.append(tx(62,324,"▶  Try it live:  jaydip-meesho.github.io/lumen",21,INK,MONO,"700"))

# ---- problem row ----
E.append(tx(40,392,"THE PROBLEM IT KILLS  →",14,GOLD,MONO,"700",1.6))
def chip(x,w,text,color):
    E.append(rr(x,406,w,46,23,S2,LINE,1))
    E.append(rr(x,406,4,46,2,color))
    E.append(tx(x+22,435,text,16,FG,MONO))
chip(40,232,"⏳  daily lockouts",RED)
chip(288,352,"☁  your code uploaded to a vendor",GOLD)
chip(656,304,"🔒  one-vendor lock-in",TEAL)

# ---- how it works (3 steps) ----
E.append(tx(40,512,"HOW IT WORKS",14,GOLD,MONO,"700",1.6))
steps=[
  ("1","Pick your model",["Local (Ollama) — $0, offline.","Or OpenRouter: 300+ models,","your own key, no daily cap."],TEAL),
  ("2","It codes for you",["Reads, edits & runs your files.","Shows a diff before every change.","Approve, or /undo anytime."],GOLD),
  ("3","Prove it's private",["Flip Airgap → all network blocked.","Secret Guard stops keys leaking.","The egress meter stays at 0."],GRN),
]
sx=[40,353,666]; sw=294; sy=530; sh=232
for i,(n,title,lines,c) in enumerate(steps):
    x=sx[i]
    E.append(rr(x,sy,sw,sh,16,PANEL,LINE,1))
    E.append(rr(x,sy,sw,5,3,c))
    E.append(f'<circle cx="{x+40}" cy="{sy+52}" r="20" fill="{S2}" stroke="{c}" stroke-width="1.5"/>')
    E.append(tx(x+40,sy+59,n,20,c,MONO,"800","middle"))
    E.append(tx(x+72,sy+59,title,21,FG,SANS,"700"))
    for j,ln in enumerate(lines):
        E.append(tx(x+26,sy+108+j*30,ln,15,MUT,SANS))

# ---- why it wins (unique, provable points) ----
E.append(tx(40,806,"WHY IT WINS",14,GOLD,MONO,"700",1.6))
E.append(tx(40,838,"Same frontier brains as Claude Code & Codex — none of the walls.",21,FG,SANS,"700"))
feats=[
  ("🔒","Privacy you can prove","A live 0-byte egress meter + OS-level airgap. Cloud tools literally can't show this.",TEAL),
  ("♾","$0 and truly unlimited","The only one with a real offline mode — local runs free, forever, no daily cap.",GRN),
  ("🔀","One key → 300+ models","Never vendor-locked: frontier via OpenRouter, or a private local model, mid-session.",GOLD),
  ("🛡","Nothing changes unseen","Secret Guard blocks keys before any request; every edit is a diff you approve + undo.",HI),
]
fx=[40,490]; fy=[860,998]; fw=470; fh=132
for i,(ic,title,desc,c) in enumerate(feats):
    x=fx[i%2]; y=fy[i//2]
    E.append(rr(x,y,fw,fh,16,PANEL,LINE,1))
    E.append(rr(x,y,5,fh,3,c))
    E.append(tx(x+28,y+56,ic,30,c))
    E.append(tx(x+76,y+52,title,22,FG,SANS,"700"))
    # wrap desc to <= ~46 chars/line
    words=desc.split(" "); ln=""; rows=[]
    for wd in words:
        if len(ln+" "+wd)>46: rows.append(ln); ln=wd
        else: ln=(ln+" "+wd).strip()
    rows.append(ln)
    for j,r in enumerate(rows[:2]):
        E.append(tx(x+76,y+84+j*24,r,15,MUT,SANS))

# ---- footer ----
E.append(f'<line x1="40" y1="1150" x2="960" y2="1150" stroke="{LINE}"/>')
E.append(tx(40,1188,"pip install lumen-code",16,GOLD,MONO,"700"))
E.append(tx(40,1214,"open source (MIT) · github.com/jaydip-meesho/lumen",14,MUT,MONO))
E.append(tx(960,1188,"private · unlimited · yours",16,FG,SANS,"700","end"))
E.append(tx(960,1214,"built at Buildathon by Jaydip",13,M2,MONO,"400","end"))

svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">\n'+"\n".join(E)+"\n</svg>\n"

if __name__=="__main__":
    import os
    os.makedirs("docs",exist_ok=True)
    open("docs/poster.svg","w",encoding="utf-8").write(svg)
    print(f"wrote docs/poster.svg ({len(svg)} bytes)")
