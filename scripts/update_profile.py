"""Generate public GitHub profile visuals using only the Python standard library."""
import argparse, collections, datetime as dt, html, json, math, pathlib, re, urllib.request
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DATA = ASSETS / "profile-data.json"
C = {"bg":"#0b1222","panel":"#111d33","line":"#263c58","text":"#eaf3ff","muted":"#8fa7c3","mint":"#7af5cf","cyan":"#5cd8ff","purple":"#b59aff","pink":"#f5a2dc"}
def text(x,y,s,size=20,fill=None,weight=400,extra=""):
    return f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}" fill="{fill or C["text"]}" font-weight="{weight}" {extra}>{html.escape(str(s))}</text>'
def svg(w,h,title,body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title,quote=True)}"><title>{html.escape(title)}</title><rect width="{w}" height="{h}" rx="20" fill="{C["bg"]}"/><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="19" fill="none" stroke="{C["line"]}"/>{body}</svg>\n'
def save(name,value):
    ASSETS.mkdir(exist_ok=True)
    (ASSETS/name).write_text(value,encoding="utf-8")
def days_from(data):
    active={d["date"]:d for d in data["calendar"]["active"]}
    first=dt.date.fromisoformat(data["calendar"]["first"])
    last=dt.date.fromisoformat(data["calendar"]["last"])
    return [active.get((first+dt.timedelta(days=i)).isoformat(),{"date":(first+dt.timedelta(days=i)).isoformat(),"count":0,"level":0}) for i in range((last-first).days+1)]
class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.cells=[]; self.tips={}; self.current=None; self.parts=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="td" and a.get("data-date"):
            self.cells.append({"date":a["data-date"],"level":int(a.get("data-level","0")),"id":a.get("id")})
        if tag=="tool-tip" and a.get("for"):
            self.current=a["for"]; self.parts=[]
    def handle_data(self,data):
        if self.current is not None: self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="tool-tip" and self.current is not None:
            self.tips[self.current]="".join(self.parts).strip(); self.current=None
def request(url):
    req=urllib.request.Request(url,headers={"User-Agent":"blight7z-profile-visuals","Accept":"application/vnd.github+json" if "api.github.com" in url else "text/html"})
    with urllib.request.urlopen(req,timeout=35) as response: return response.read().decode("utf-8")
def fetch(username):
    repos=[]; page=1
    while True:
        batch=json.loads(request(f"https://api.github.com/users/{username}/repos?per_page=100&type=owner&page={page}"))
        if not isinstance(batch,list): raise ValueError("Repository response is not a list")
        repos.extend({"name":r["name"],"stars":r["stargazers_count"],"forks":r["forks_count"],"language":r["language"],"pushed_at":r["pushed_at"],"private":False} for r in batch if r.get("private") is False)
        if len(batch)<100: break
        page+=1
    parser=CalendarParser(); parser.feed(request(f"https://github.com/users/{username}/contributions"))
    cells=sorted(parser.cells,key=lambda d:d["date"])
    if len(cells)<300: raise ValueError("Incomplete public contribution calendar")
    active=[]
    for cell in cells:
        label=parser.tips.get(cell["id"],"")
        match=re.match(r"(\d+) contributions?\b",label)
        if cell["level"] and not match: raise ValueError("Missing contribution count for "+cell["date"])
        if match and int(match.group(1)):
            active.append({"date":cell["date"],"count":int(match.group(1)),"level":cell["level"]})
    return {"username":username,"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"repos":repos,"calendar":{"first":cells[0]["date"],"last":cells[-1]["date"],"active":active}}
def generate(data):
    days=days_from(data); repos=data["repos"]; stamp=data["generated_at"][:10]
    total=sum(d["count"] for d in days); active=sum(d["count"]>0 for d in days)
    peak=max((d["count"] for d in days),default=0)
    body=text(38,48,"GITHUB / PUBLIC SIGNAL",17,C["mint"],650)+text(1160,48,"AS OF "+stamp,14,C["muted"],extra='text-anchor="end"')
    items=[(str(len(repos)),"PUBLIC REPOSITORIES",C["cyan"]),(str(total),"YEARLY CONTRIBUTIONS",C["mint"]),(str(active),"ACTIVE DAYS",C["purple"]),(str(peak),"BEST DAY / CONTRIBUTIONS",C["pink"])]
    for i,(value,label,color) in enumerate(items):
        x=38+290*i
        body+=f'<rect x="{x}" y="79" width="254" height="141" rx="14" fill="{C["panel"]}" stroke="{C["line"]}"/>'
        body+=text(x+22,148,value,54,color,700)+text(x+22,186,label,12,C["muted"],650)
    save("github-pulse.svg",svg(1200,252,"Public GitHub statistics; snapshot "+stamp,body))
    mix=collections.Counter(r["language"] for r in repos if r.get("language"))
    colors=[C["cyan"],C["purple"],C["mint"],C["pink"]]
    body=text(30,43,"REPOSITORY DNA",18,C["purple"],650)+text(30,70,"Primary language per public repository",14,C["muted"])
    count=sum(mix.values()); offset=0
    for i,(lang,n) in enumerate(mix.most_common()):
        size=n/max(count,1)*100; color=colors[i%len(colors)]
        body+=f'<circle cx="112" cy="165" r="57" fill="none" stroke="{color}" stroke-width="18" pathLength="100" stroke-dasharray="{size:.4f} {100-size:.4f}" stroke-dashoffset="{-offset:.4f}" transform="rotate(-90 112 165)"/>'
        body+=f'<circle cx="230" cy="{132+i*39}" r="5" fill="{color}"/>'
        body+=text(248,138+i*39,lang,20,weight=600)+text(544,138+i*39,str(n)+" repos",17,C["muted"],extra='text-anchor="end"')
        offset+=size
    body+=text(112,175,str(count),34,weight=700,extra='text-anchor="middle"')
    body+=text(30,248,"Repository counts, not skill ratings",12,C["muted"])
    save("repo-dna.svg",svg(590,270,"Primary languages across public repositories",body))
    recent=days[-90:]; max_count=max(1,max(d["count"] for d in recent)); total90=sum(d["count"] for d in recent)
    points=[(34+i*522/max(len(recent)-1,1),206-d["count"]*104/max_count) for i,d in enumerate(recent)]
    coords=" ".join(f"{x:.2f},{y:.2f}" for x,y in points)
    area=f"M34,206 L"+" L".join(f"{x:.2f},{y:.2f}" for x,y in points)+" L556,206 Z"
    body=text(30,43,"90-DAY ACTIVITY",18,C["cyan"],650)+text(30,72,f"{total90} public contributions",15,C["muted"])
    body+='<defs><linearGradient id="area" x2="0" y2="1"><stop stop-color="#5cd8ff" stop-opacity=".35"/><stop offset="1" stop-color="#5cd8ff" stop-opacity="0"/></linearGradient></defs>'
    for y in (102,154,206): body+=f'<path d="M34 {y}H556" stroke="{C["line"]}" stroke-dasharray="4 6"/>'
    body+=f'<path d="{area}" fill="url(#area)"/><polyline points="{coords}" fill="none" stroke="{C["cyan"]}" stroke-width="3" stroke-linejoin="round"/>'
    for (x,y),day in zip(points,recent):
        if day["count"]: body+=f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{C["mint"]}"><title>{day["date"]}: {day["count"]} contributions</title></circle>'
    body+=text(34,246,recent[0]["date"],12,C["muted"])+text(556,246,recent[-1]["date"],12,C["muted"],extra='text-anchor="end"')
    save("activity.svg",svg(590,270,"Last ninety days of public GitHub contribution activity",body))
    # A decorative snake traverses the real, dated calendar in a serpentine path.
    body='<style>@media(prefers-reduced-motion:reduce){.snake{display:none}.heat{opacity:1!important}}</style>'
    body+=text(38,44,"CONTRIBUTION SNAKE",19,C["mint"],650)+text(1160,44,"PUBLIC CALENDAR / "+stamp,13,C["muted"],extra='text-anchor="end"')
    body+=text(38,73,"A little motion, powered by real contributions.",15,C["muted"])
    bydate={d["date"]:d for d in days}; first=dt.date.fromisoformat(days[0]["date"])
    columns=math.ceil(len(days)/7); order=[]
    for col in range(columns):
        for row in (range(7) if col%2==0 else range(6,-1,-1)):
            index=col*7+row
            if index<len(days): order.append(index)
    phase={index:(step+.5)/len(order) for step,index in enumerate(order)}
    palette=["#17243b","#164a4b","#21806e","#43bfa0","#8dfbd5"]
    for i,day in enumerate(days):
        col,row=divmod(i,7); x=64+col*20; y=101+row*18
        body+=f'<rect class="heat" x="{x}" y="{y}" width="13" height="13" rx="3" fill="{palette[day["level"]]}"><title>{day["date"]}: {day["count"]} contributions</title>'
        if day["count"]:
            p=min(phase[i],.96)
            body+=f'<animate attributeName="opacity" values="1;1;0.18;0.18;1" keyTimes="0;{p:.5f};{p+.002:.5f};0.99;1" dur="36s" repeatCount="indefinite"/>'
        body+="</rect>"
    route="M"+" L".join(f"{64+(index//7)*20+6.5},{101+(index%7)*18+6.5}" for index in order)
    body+=f'<defs><path id="route" d="{route}"/></defs><g class="snake">'
    for i in reversed(range(5)):
        color=C["mint"] if i else C["purple"]
        body+=f'<circle r="{6.8-i*.6}" fill="{color}" opacity="{1-i*.12}"><animateMotion dur="36s" begin="{-i*.11}s" repeatCount="indefinite"><mpath href="#route"/></animateMotion></circle>'
    body+="</g>"+text(64,259,days[0]["date"],12,C["muted"])+text(1116,259,days[-1]["date"],12,C["muted"],extra='text-anchor="end"')
    save("contribution-snake.svg",svg(1200,286,"Animated snake over the actual public contribution calendar, snapshot "+stamp,body))

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--fetch",action="store_true"); args=parser.parse_args()
    data=fetch("blight7z") if args.fetch else json.loads(DATA.read_text(encoding="utf-8"))
    if not data["repos"] or any(r.get("private") for r in data["repos"]): raise ValueError("Only public repository data is accepted")
    generate(data)
    if args.fetch: DATA.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print("Generated public profile statistics, activity chart, repository mix, and contribution snake.")
