import unicodedata
from collections import defaultdict


def norm(s):
    return " ".join(unicodedata.normalize("NFKC", s or "").casefold().split())


def tally(listens):
    """Collapse a listen stream into {(artist, title): (count, last_timestamp)}."""
    cnt, last = defaultdict(int), defaultdict(int)
    for ts, artist, _album, title in listens:
        k = (norm(artist), norm(title))
        if not k[1]:
            continue
        cnt[k] += 1
        last[k] = max(last[k], ts)
    return {k: (cnt[k], last[k]) for k in cnt}


def plan(rows, tallied, mode="max"):
    """rows: (rowid, artist, albumartist, title, playcount, lastplayed).

    Returns (updates, matched_keys); updates are (playcount, lastplayed, rowid).
    """
    updates, matched = [], set()
    for rowid, artist, albumartist, title, playcount, lastplayed in rows:
        t = norm(title)
        if not t:
            continue
        key = next((k for k in ((norm(artist), t), (norm(albumartist), t)) if k in tallied), None)
        if key is None:
            continue
        count, last = tallied[key]
        playcount = playcount or 0
        if mode == "max":
            new_pc = max(playcount, count)
            new_lp = max(lastplayed or 0, last)
        else:
            new_pc, new_lp = count, last
        if (new_pc, new_lp) != (playcount, lastplayed):
            updates.append((new_pc, new_lp, rowid))
        matched.add(key)
    return updates, matched
