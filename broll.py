"""
BROLL - double click, paste script, get 100 b-roll clips.
Needs Python (python.org) and a free Pexels API key (pexels.com/api).
No pip installs. Key is asked once and saved next to this file.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from collections import Counter

TOTAL = 100
HERE = os.path.dirname(os.path.abspath(__file__))
KEYFILE = os.path.join(HERE, "pexels_key.txt")
UA = {"User-Agent": "Mozilla/5.0"}
STOP = set("""a about above after again all also am an and any are as at be because been before being below between both
but by can could did do does doing down during each few for from further had has have having he her here hers him his how
i if in into is it its just me more most my no nor not now of off on once only or other our out over own same she should so
some such than that the their them then there these they this those through to too under until up very was we were what
when where which while who whom why will with would you your like even still really much many one two thing things way get
got make made says said""".split())


def get_key():
    if os.path.exists(KEYFILE):
        k = open(KEYFILE).read().strip()
        if k:
            return k
    k = input("Paste your Pexels API key (asked once): ").strip()
    open(KEYFILE, "w").write(k)
    return k


def read_script():
    print("\nPaste your script, then press Enter twice:\n")
    lines, blank = [], 0
    while True:
        try:
            l = input()
        except EOFError:
            break
        if l.strip() == "":
            blank += 1
            if blank >= 2:
                break
            lines.append("")
        else:
            blank = 0
            lines.append(l)
    return "\n".join(lines).strip()


def split_parts(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) >= 3:
        return paras
    s = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [" ".join(s[i:i + 3]) for i in range(0, len(s), 3)]


def queries(part):
    w = [x for x in re.findall(r"[a-z']{4,}", part.lower()) if x not in STOP]
    top = [x for x, _ in Counter(w).most_common(5)]
    qs = [" ".join(top[:2])] if len(top) > 1 else []
    qs += top[:4]
    return list(dict.fromkeys(qs)) or ["cinematic background"]


def get(url, key=None):
    h = dict(UA)
    if key:
        h["Authorization"] = key
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60)


def search(key, q, page):
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
        {"query": q, "per_page": 15, "page": page, "orientation": "landscape"})
    try:
        vids = json.load(get(url, key)).get("videos", [])
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("  rate limit, waiting 60s...")
            time.sleep(60)
            return search(key, q, page)
        if e.code in (401, 403):
            os.remove(KEYFILE)
            sys.exit("Bad API key. Deleted it, run again and paste a good one.")
        return []
    return [v for v in vids if 4 <= v.get("duration", 0) <= 30]


def best(v):
    f = [x for x in v["video_files"] if x.get("file_type") == "video/mp4" and x.get("width")]
    return min(f, key=lambda x: abs(x["width"] - 1920)) if f else None


def main():
    key = get_key()
    global TOTAL
    text = read_script()
    if not text:
        sys.exit("No script pasted.")
    ans = input("\nHow many clips in TOTAL? (Enter = 100): ").strip()
    TOTAL = int(ans) if ans.isdigit() and int(ans) > 0 else 100
    parts = split_parts(text)
    n = len(parts)
    qs = [queries(p) for p in parts]
    # split TOTAL across parts by how long each part is (longer part = more clips)
    words = [max(1, len(p.split())) for p in parts]
    raw = [TOTAL * w / sum(words) for w in words]
    need = [int(r) for r in raw]
    order = sorted(range(n), key=lambda i: raw[i] - need[i], reverse=True)
    for i in order[:TOTAL - sum(need)]:
        need[i] += 1
    out = os.path.join(HERE, "broll_" + time.strftime("%H%M%S"))
    dirs = []
    for i, q in enumerate(qs, 1):
        d = os.path.join(out, f"part_{i:02d}_{re.sub('[^a-z0-9]+', '-', q[0])[:25]}")
        if need[i - 1] > 0:
            os.makedirs(d, exist_ok=True)
        dirs.append(d)
    print(f"\n{n} parts, {sum(need)} clips total. Plan: {need}")
    print(f"Saving to {out}\n")

    used, count, total = set(), [0] * n, 0
    for page in range(1, 7):
        if total >= TOTAL:
            break
        for i in range(n):
            for q in qs[i]:
                if count[i] >= need[i] or total >= TOTAL:
                    break
                for v in search(key, q, page):
                    if v["id"] in used or count[i] >= need[i] or total >= TOTAL:
                        continue
                    f = best(v)
                    if not f:
                        continue
                    dest = os.path.join(dirs[i], f"{count[i] + 1:02d}_{v['id']}.mp4")
                    try:
                        with get(f["link"]) as r, open(dest, "wb") as o:
                            while True:
                                c = r.read(1 << 20)
                                if not c:
                                    break
                                o.write(c)
                    except Exception as e:
                        print("  skip:", e)
                        continue
                    used.add(v["id"])
                    count[i] += 1
                    total += 1
                    print(f"[{total:>3}/{TOTAL}] part {i + 1} '{q}'")
                time.sleep(0.3)
    print(f"\nDone: {total} clips in {out}")
    os.startfile(out) if os.name == "nt" else None


try:
    main()
except SystemExit as e:
    print(e)
except Exception as e:
    print("Error:", e)
input("\nPress Enter to close...")