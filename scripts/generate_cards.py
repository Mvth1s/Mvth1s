#!/usr/bin/env python3
"""Genere les cartes SVG du README de profil (style terminal retro).

Stdlib uniquement. Variables d'environnement :
  GH_USER       login GitHub (defaut : Mvth1s)
  GITHUB_TOKEN  token pour l'API (obligatoire pour l'activite et le streak)
"""
import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "Mvth1s")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(__file__).resolve().parent.parent / "assets"

EXCLUDED_LANGS = {"HTML", "CSS", "SCSS", "Dockerfile", "Makefile"}
EXCLUDED_REPOS = {USER}
TOP_LANGS = 6
RECENT_COUNT = 5

BG, BORDER, BAR = "#0a0f0a", "#1f3a22", "#111a11"
GREEN, MID, DIM = "#7CFC8A", "#5fbf6b", "#3f7d47"
FONT = "'JetBrains Mono','Fira Code','DejaVu Sans Mono',Consolas,monospace"
W = 840
CHAR = 0.6


def api(url, data=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-cards"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_repos():
    repos, page = [], 1
    while True:
        batch = api(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner")
        repos += batch
        if len(batch) < 100:
            return [r for r in repos if not r["fork"] and r["name"] not in EXCLUDED_REPOS]
        page += 1


def fetch_languages(repos):
    totals = {}
    for r in repos:
        for lang, size in api(r["languages_url"]).items():
            if lang not in EXCLUDED_LANGS:
                totals[lang] = totals.get(lang, 0) + size
    grand = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:TOP_LANGS]
    return [(lang, size * 100 / grand) for lang, size in top]


def fetch_activity():
    if not TOKEN:
        return None
    q = """query($login:String!){user(login:$login){contributionsCollection{
      contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
    data = api("https://api.github.com/graphql", {"query": q, "variables": {"login": USER}})
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    tail = days[:-1] if days and days[-1]["contributionCount"] == 0 else days
    for d in reversed(tail):
        if not d["contributionCount"]:
            break
        current += 1
    return {"total": cal["totalContributions"], "current": current, "longest": longest}


def fmt_int(n):
    return f"{n:,}".replace(",", " ")


def frame(height, title, body, now):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-label="{escape(title)}">
<title>{escape(title)}</title>
<style>
text{{font-family:{FONT};}}
.l{{opacity:0;animation:in .4s ease-out forwards;}}
@keyframes in{{to{{opacity:1;}}}}
@media (prefers-reduced-motion:reduce){{.l{{animation:none;opacity:1;}}}}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
<path d="M0.5 10.5a10 10 0 0 1 10-10h{W - 21}a10 10 0 0 1 10 10v18h-{W - 1}z" fill="{BAR}"/>
<circle cx="20" cy="15" r="5" fill="{DIM}"/><circle cx="38" cy="15" r="5" fill="{DIM}"/><circle cx="56" cy="15" r="5" fill="{GREEN}"/>
<text x="{W / 2}" y="19" text-anchor="middle" font-size="12" fill="{DIM}">{escape(title)}</text>
{body}
<text x="{W - 20}" y="{height - 14}" text-anchor="end" font-size="11" fill="{DIM}"><!--ts-->updated {now}<!--/ts--></text>
</svg>
"""


def line(y, text, delay, size=14, color=GREEN):
    return (f'<text class="l" style="animation-delay:{delay:.2f}s" x="24" y="{y}" '
            f'font-size="{size}" fill="{color}" xml:space="preserve">{escape(text)}</text>')


def header_svg(now):
    cmd = f"{USER.lower()}@github:~$ whoami"
    name = f"> Mathis / {USER}"
    cmd_w = len(cmd) * 14 * CHAR
    name_w = len(name) * 28 * CHAR
    body = f"""<clipPath id="c1"><rect x="24" y="44" height="24" width="0"><animate attributeName="width" from="0" to="{cmd_w:.0f}" begin="0.3s" dur="1.2s" fill="freeze"/></rect></clipPath>
<clipPath id="c2"><rect x="24" y="74" height="40" width="0"><animate attributeName="width" from="0" to="{name_w:.0f}" begin="1.8s" dur="1.2s" fill="freeze"/></rect></clipPath>
<text x="24" y="62" font-size="14" fill="{DIM}" clip-path="url(#c1)" xml:space="preserve">{escape(cmd)}</text>
<text x="24" y="106" font-size="28" fill="{GREEN}" clip-path="url(#c2)" xml:space="preserve">{escape(name)}</text>
<rect x="24" y="82" width="15" height="28" fill="{GREEN}" opacity="0">
<animate attributeName="x" from="24" to="{24 + name_w + 4:.0f}" begin="1.8s" dur="1.2s" fill="freeze"/>
<animate attributeName="opacity" values="1;0;1" dur="1s" begin="1.8s" calcMode="discrete" repeatCount="indefinite"/>
</rect>
{line(140, "Cloud & DevOps student (MSc) - France", 3.2, 15, MID)}
{line(164, "automation | open-source | reliable systems", 3.5, 15, MID)}"""
    return frame(200, "~/whoami", body, now)


def stats_svg(repos, activity, now):
    stars = sum(r["stargazers_count"] for r in repos)
    active = [r for r in repos if not r["archived"]]
    rows = [
        ("public repos", fmt_int(len(repos))),
        ("active projects", fmt_int(len(active))),
        ("stars", fmt_int(stars)),
    ]
    if activity:
        rows += [
            ("contributions (1y)", fmt_int(activity["total"])),
            ("current streak", f"{activity['current']} d"),
            ("longest streak", f"{activity['longest']} d"),
        ]
    else:
        rows.append(("activity", "n/a (no token)"))
    body = [line(56, "$ stats --live", 0.2, 14, DIM)]
    for i, (k, v) in enumerate(rows):
        dots = "." * (28 - len(k))
        body.append(line(84 + i * 24, f"{k} {dots} {v}", 0.5 + i * 0.15))
    h = 84 + len(rows) * 24 + 30
    return frame(h, "~/stats", "\n".join(body), now)


def langs_svg(langs, now):
    body = [line(56, f"$ langs --top {TOP_LANGS}", 0.2, 14, DIM)]
    width_name = max((len(l) for l, _ in langs), default=6) + 1
    for i, (lang, pct) in enumerate(langs):
        y = 84 + i * 24
        filled = max(1, round(pct / 5))
        bar = "#" * filled + "." * (20 - filled)
        body.append(line(y, f"{lang.ljust(width_name)} [{bar}] {pct:5.1f}%", 0.5 + i * 0.15))
    h = 84 + len(langs) * 24 + 30
    return frame(h, "~/langs", "\n".join(body), now)


def recent_svg(repos, now):
    active = sorted((r for r in repos if not r["archived"]), key=lambda r: r["pushed_at"], reverse=True)
    body = [line(56, f"$ ls -lt ~/repos | head -{RECENT_COUNT}", 0.2, 14, DIM)]
    for i, r in enumerate(active[:RECENT_COUNT]):
        y = 84 + i * 24
        date = dt.datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")).strftime("%d/%m/%Y")
        desc = (r["description"] or "").strip()
        desc = desc[:44] + "..." if len(desc) > 47 else desc
        body.append(line(y, f"{date}  {r['name'][:22].ljust(22)} {desc}", 0.5 + i * 0.15, 13))
    h = 84 + min(len(active), RECENT_COUNT) * 24 + 30
    return frame(h, "~/repos", "\n".join(body), now)


STACK = [
    ("</>", "languages", "Python, TypeScript, Bash, Rust"),
    ("[#]", "frontend", "Vue 3, PrimeVue, Nuxt"),
    ("{~}", "devops", "Docker, Kubernetes (K3s), Ansible, GitHub Actions"),
    ("   ", "", "Semantic Release"),
    ("/|\\", "monitoring", "Prometheus, Grafana"),
    (">_ ", "os", "EndeavourOS, Fedora, Debian, openSUSE"),
]

CONTACTS = [("linkedin", "in/mathis-aguado"), ("portfolio", "mathisaguado"), ("email", "mag.d3v")]


def stack_svg(now):
    body = [line(56, "$ cat stack.txt", 0.2, 14, DIM)]
    for i, (glyph, cat, items) in enumerate(STACK):
        y = 84 + i * 24
        d = 0.5 + i * 0.15
        body.append(f'<text class="l" style="animation-delay:{d:.2f}s" x="24" y="{y}" font-size="14" xml:space="preserve">'
                    f'<tspan fill="{MID}">{escape(glyph)}</tspan>'
                    f'<tspan fill="{DIM}">  {escape(cat.ljust(11))}</tspan>'
                    f'<tspan fill="{GREEN}">{escape(items)}</tspan></text>')
    h = 84 + len(STACK) * 24 + 30
    return frame(h, "~/stack", "\n".join(body), now)


def button_svg(label, hint):
    text = f"> {label}"
    w = 260
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="52" viewBox="0 0 {w} 52" role="img" aria-label="{label}">
<title>{label}</title>
<style>text{{font-family:{FONT};}}</style>
<rect x="0.5" y="0.5" width="{w - 1}" height="51" rx="8" fill="{BG}" stroke="{MID}"/>
<text x="18" y="24" font-size="16" fill="{GREEN}" xml:space="preserve">{escape(text)}<tspan fill="{GREEN}"><animate attributeName="opacity" values="1;0;1" dur="1s" calcMode="discrete" repeatCount="indefinite"/>_</tspan></text>
<text x="18" y="42" font-size="11" fill="{DIM}">{escape(hint)}</text>
</svg>
"""


TS = re.compile(r"<!--ts-->.*?<!--/ts-->")


def write_if_changed(path, content):
    if path.exists() and TS.sub("", path.read_text()) == TS.sub("", content):
        print(f"unchanged  {path.name}")
        return
    path.write_text(content)
    print(f"written    {path.name}")


def main():
    OUT.mkdir(exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    repos = fetch_repos()
    write_if_changed(OUT / "header.svg", header_svg(now))
    write_if_changed(OUT / "stats.svg", stats_svg(repos, fetch_activity(), now))
    active = [r for r in repos if not r["archived"]]
    write_if_changed(OUT / "langs.svg", langs_svg(fetch_languages(active), now))
    write_if_changed(OUT / "recent.svg", recent_svg(repos, now))
    write_if_changed(OUT / "stack.svg", stack_svg(now))
    for label, hint in CONTACTS:
        write_if_changed(OUT / f"contact-{label}.svg", button_svg(label, hint))


if __name__ == "__main__":
    main()
