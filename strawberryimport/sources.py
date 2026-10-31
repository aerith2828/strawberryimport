"""Fetch listening history. Every source yields (timestamp, artist, album, title)."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "strawberryimport/0.1 (+https://github.com/aerith2828/strawberryimport)"


def _get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                wait = int(e.headers.get("Retry-After", 5 * (attempt + 1)))
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("request failed after retries: " + url)


def listenbrainz(user, token=None, progress=None):
    headers = {"Authorization": "Token " + token} if token else {}
    max_ts = int(time.time()) + 1000
    n = 0
    while True:
        url = "https://api.listenbrainz.org/1/user/%s/listens?count=1000&max_ts=%d" % (
            urllib.parse.quote(user), max_ts)
        listens = _get(url, headers)["payload"]["listens"]
        if not listens:
            return
        for l in listens:
            m = l["track_metadata"]
            yield l["listened_at"], m.get("artist_name"), m.get("release_name"), m.get("track_name")
        n += len(listens)
        max_ts = listens[-1]["listened_at"]
        if progress:
            progress(n)
        time.sleep(0.3)


def lastfm(user, api_key, progress=None):
    page, total_pages, n = 1, 1, 0
    while page <= total_pages:
        url = ("https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&format=json"
               "&limit=200&user=%s&api_key=%s&page=%d" % (
                   urllib.parse.quote(user), urllib.parse.quote(api_key), page))
        data = _get(url)["recenttracks"]
        total_pages = int(data["@attr"]["totalPages"])
        for t in data["track"]:
            if t.get("@attr", {}).get("nowplaying"):
                continue
            yield int(t["date"]["uts"]), t["artist"]["#text"], t.get("album", {}).get("#text"), t["name"]
            n += 1
        if progress:
            progress(n)
        page += 1
        time.sleep(0.25)
