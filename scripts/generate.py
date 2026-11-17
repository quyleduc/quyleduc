#!/usr/bin/env python3
"""Render a self-contained GitHub profile from public GitHub GraphQL data."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "quyleduc"
GRAPHQL = "https://api.github.com/graphql"
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!, $after: String) {
  user(login: $login) {
    followers { totalCount }
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER, first: 100, after: $after) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount forkCount primaryLanguage { name } }
    }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""
THEMES = {
    "dark": {"bg":"#0d1117","panel":"#161b22","border":"#30363d","text":"#e6edf3","muted":"#8b949e","accent":"#58a6ff","green":"#3fb950","art":"#c9d1d9","heat":["#161b22","#0e4429","#006d32","#26a641","#39d353"]},
    "light": {"bg":"#ffffff","panel":"#f6f8fa","border":"#d0d7de","text":"#24292f","muted":"#57606a","accent":"#0969da","green":"#1a7f37","art":"#30363d","heat":["#ebedf0","#9be9a8","#40c463","#30a14e","#216e39"]},
}

def load_github(token, now):
    if not token:
        raise RuntimeError("GITHUB_TOKEN required for live profile data")
    start = (now - dt.timedelta(days=364)).isoformat().replace("+00:00", "Z")
    end = now.isoformat().replace("+00:00", "Z")
    after = None
    stars, forks, languages = 0, 0, {}
    while True:
        payload = json.dumps({"query": QUERY, "variables": {"login": USERNAME, "from": start, "to": end, "after": after}}).encode()
        req = Request(GRAPHQL, data=payload, headers={"Authorization": f"Bearer {token}","Content-Type":"application/json","User-Agent":"quyleduc-profile-generator","Accept":"application/vnd.github+json"})
        with urlopen(req, timeout=25) as response:
            body = json.load(response)
        if body.get("errors"):
            raise RuntimeError("GraphQL error: " + json.dumps(body["errors"]))
        user = body.get("data", {}).get("user")
        if user is None:
            raise RuntimeError("GitHub user not found")
        repos = user["repositories"]
        for repo in repos["nodes"]:
            stars += repo["stargazerCount"]
            forks += repo["forkCount"]
            lang = (repo.get("primaryLanguage") or {}).get("name")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
        if not repos["pageInfo"]["hasNextPage"]:
            break
        next_after = repos["pageInfo"]["endCursor"]
        if not next_after or next_after == after:
            raise RuntimeError("Invalid GitHub pagination cursor")
        after = next_after
    contrib = user["contributionsCollection"]
    return {
        "repos": repos["totalCount"], "stars": stars, "forks": forks,
        "followers": user["followers"]["totalCount"],
        "commits": contrib["totalCommitContributions"],
        "contribs": contrib["contributionCalendar"]["totalContributions"],
        "calendar": contrib["contributionCalendar"]["weeks"],
        "top_language": max(languages, key=languages.get) if languages else "—",
    }

def txt(x, y, value, color, size=17, weight=400, extra=""):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" {extra}>{escape(str(value))}</text>'

def render_card(stats, art, theme, updated):
    c = THEMES[theme]
    chunks = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1040 570" role="img" aria-label="ASCII portrait and GitHub profile of Quy, embedded software engineer">',
      f'<rect width="1040" height="570" rx="18" fill="{c["bg"]}"/>',
      f'<rect x="1" y="1" width="1038" height="568" rx="17" fill="none" stroke="{c["border"]}" stroke-width="2"/>',
      f'<rect x="2" y="2" width="1036" height="57" rx="16" fill="{c["panel"]}"/>',
      f'<path d="M2,43 L1038,43 L1038,60 L2,60" fill="{c["panel"]}"/>']
    for i, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        chunks.append(f'<circle cx="{30+i*24}" cy="30" r="7" fill="{color}"/>')
    chunks += [txt(520, 37, "quyleduc@github: ~", c["muted"], 15, 500, 'text-anchor="middle"')]
    # A precomputed portrait is committed as text; no avatar service or remote image needed.
    for i, line in enumerate(art.splitlines()):
        chunks.append(txt(44, 87+i*9.65, line, c["art"], 8.7, 600, 'xml:space="preserve"'))
    chunks.append(f'<path d="M445,84 V523" stroke="{c["border"]}" stroke-width="1"/>')
    chunks += [txt(479, 111, "quyleduc", c["accent"], 31, 700),txt(637, 110, "@github",c["muted"],19,500),
        f'<path d="M479 129 H1002" stroke="{c["accent"]}" stroke-width="2"/>']
    rows = [
        ("Name", "Quy"),
        ("Role", "Senior Embedded Software Engineer"),
        ("Focus", "AUTOSAR Classic · OS · RTE · MCAL"),
        ("Languages", "C / C++ · Python · Rust · Go"),
        ("Targets", "TriCore · PowerPC · ARM"),
        ("Tooling", "TRACE32 · CANoe · GCC · VS Code"),
    ]
    for i, (key, value) in enumerate(rows):
        y=166+i*38
        chunks += [txt(479,y,key+":",c["green"],17,600),txt(603,y,value,c["text"],16)]
    chunks += [f'<path d="M479 407 H1002" stroke="{c["border"]}" stroke-width="1"/>',txt(479,439,"GITHUB / LAST 365 DAYS",c["accent"],15,700)]
    metrics=[("Public repos",stats.get("repos","—")),("Stars",stats.get("stars","—")),("Commits",stats.get("commits","—")),("Contributions",stats.get("contribs","—"))]
    for i, (key, val) in enumerate(metrics):
        x = 479 if i%2==0 else 748
        y = 471+(i//2)*39
        chunks += [txt(x,y,key+":",c["muted"],15),txt(x+141,y,f"{val:,}" if isinstance(val,int) else val,c["green"],17,700)]
    chunks += [txt(1003,553,"updated "+updated+" UTC",c["muted"],13,400,'text-anchor="end"'),'</svg>']
    return '\n'.join(chunks)+'\n'

def heat_level(count):
    return 0 if count == 0 else 1 if count <= 2 else 2 if count <= 5 else 3 if count <= 9 else 4

def render_heatmap(stats, theme, updated):
    c = THEMES[theme]
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 192" role="img" aria-label="GitHub contribution heatmap for the last 365 days">',f'<rect x="1" y="1" width="1038" height="190" rx="16" fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="2"/>',txt(24,35,"$ git log --since=365.days --oneline",c["accent"],17,600),txt(1015,35,f"{stats.get('contribs','—')} contributions",c["green"],15,600,'text-anchor="end"')]
    weeks = stats.get("calendar", [])[-53:]
    start_x, start_y, step, cell=44, 61, 17.9, 13
    for x in range(53):
        days = weeks[x].get("contributionDays",[]) if x < len(weeks) else []
        by_weekday = {}
        for d in days:
            weekday = dt.date.fromisoformat(d["date"]).weekday()  # Monday=0
            by_weekday[weekday] = d.get("contributionCount",0)
        for day in range(7):
            level=heat_level(by_weekday.get(day,0))
            lines.append(f'<rect x="{start_x+x*step:.1f}" y="{start_y+day*15}" width="{cell}" height="{cell}" rx="2.5" fill="{c["heat"][level]}"/>')
    lines += [txt(44,181,"Mon",c["muted"],12),txt(112,181,"Last 365 days · Public contribution activity",c["muted"],12),txt(1015,181,updated+" UTC",c["muted"],12,400,'text-anchor="end"'),'</svg>']
    return '\n'.join(lines)+'\n'

def write_assets(stats, updated):
    art=(ROOT/'assets'/'portrait.txt').read_text(encoding='utf-8')
    if len(art.splitlines()) < 10:
        raise RuntimeError("Portrait ASCII source missing or truncated")
    for theme in THEMES:
        (ROOT/'assets'/f'neofetch-{theme}.svg').write_text(render_card(stats,art,theme,updated),encoding='utf-8')
        (ROOT/'assets'/f'heatmap-{theme}.svg').write_text(render_heatmap(stats,theme,updated),encoding='utf-8')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strict',action='store_true',help='Fail if GitHub API data is unavailable')
    args=parser.parse_args()
    now=dt.datetime.now(dt.timezone.utc)
    try:
        stats=load_github(os.environ.get('GITHUB_TOKEN'),now)
    except Exception as error:
        if args.strict:
            raise
        print(f'Preview with unavailable stats (not live): {error}')
        stats={}
    write_assets(stats,now.strftime('%Y-%m-%d') if stats else 'preview')
    print('Generated four SVG assets. Live data:',bool(stats))

if __name__=='__main__':
    main()
