import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from . import sources
from .matching import plan, tally

DEFAULT_DB = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "strawberry/strawberry/strawberry.db"


def strawberry_running():
    try:
        return subprocess.run(["pgrep", "-x", "strawberry"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def load_or_fetch(args):
    cache = Path(args.cache) if args.cache else None
    if cache and cache.exists() and not args.refresh:
        with cache.open() as f:
            return [tuple(json.loads(line)) for line in f]

    def progress(n):
        print("\rfetched %d listens" % n, end="", file=sys.stderr, flush=True)

    if args.source == "listenbrainz":
        it = sources.listenbrainz(args.user, args.token or os.environ.get("LISTENBRAINZ_TOKEN"), progress)
    else:
        key = args.api_key or os.environ.get("LASTFM_API_KEY")
        if not key:
            raise SystemExit("lastfm needs --api-key or LASTFM_API_KEY (https://www.last.fm/api/account/create)")
        it = sources.lastfm(args.user, key, progress)
    listens = list(it)
    print(file=sys.stderr)
    if cache:
        with cache.open("w") as f:
            for l in listens:
                f.write(json.dumps(l, ensure_ascii=False) + "\n")
    return listens


def main(argv=None):
    p = argparse.ArgumentParser(prog="strawberryimport",
                                description="Import play counts from ListenBrainz or Last.fm into Strawberry.")
    p.add_argument("source", choices=["listenbrainz", "lastfm"])
    p.add_argument("user", help="account name on the chosen service")
    p.add_argument("--db", default=str(DEFAULT_DB), help="path to strawberry.db (default: %(default)s)")
    p.add_argument("--apply", action="store_true", help="write to the database (default is a dry run)")
    p.add_argument("--mode", choices=["max", "overwrite"], default="max",
                   help="max: keep the higher of local and remote count; overwrite: use the remote count")
    p.add_argument("--token", help="ListenBrainz user token (only needed for private profiles)")
    p.add_argument("--api-key", help="Last.fm API key")
    p.add_argument("--cache", help="JSONL file to store/reuse the downloaded history")
    p.add_argument("--refresh", action="store_true", help="ignore an existing --cache file and download again")
    p.add_argument("--no-backup", action="store_true", help="do not copy the database before writing")
    p.add_argument("--force", action="store_true", help="write even if Strawberry seems to be running")
    args = p.parse_args(argv)

    db = Path(args.db)
    if not db.exists():
        raise SystemExit("database not found: %s" % db)
    if args.apply and strawberry_running() and not args.force:
        raise SystemExit("Strawberry is running; close it first (it would overwrite the changes) or pass --force")

    listens = load_or_fetch(args)
    tallied = tally(listens)

    con = sqlite3.connect(db if args.apply else "file:%s?mode=ro" % db, uri=not args.apply)
    rows = con.execute("select rowid, artist, albumartist, title, playcount, lastplayed "
                       "from songs where url like 'file://%'").fetchall()
    updates, matched = plan(rows, tallied, args.mode)
    total = sum(c for c, _ in tallied.values())
    print("history: %d listens, %d distinct tracks" % (total, len(tallied)))
    print("library: %d local songs, %d would change (%d distinct tracks matched, %d listens)" % (
        len(rows), len(updates), len(matched), sum(tallied[k][0] for k in matched)))

    if not args.apply:
        print("dry run; pass --apply to write")
        return 0
    if not args.no_backup:
        backup = db.with_name("%s.pre-import-%s" % (db.name, time.strftime("%Y%m%d-%H%M%S")))
        shutil.copy2(db, backup)
        print("backup:", backup)
    con.executemany("update songs set playcount=?, lastplayed=? where rowid=?", updates)
    con.commit()
    print("updated %d songs" % len(updates))
    return 0
