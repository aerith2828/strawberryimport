# strawberryimport

Import play counts and last-played dates into the [Strawberry](https://www.strawberrymusicplayer.org/)
music player from your ListenBrainz or Last.fm listening history.

Strawberry has no plugin system and no longer imports statistics from Last.fm,
so this is a small standalone command line tool that edits Strawberry's
SQLite database (`songs.playcount`, `songs.lastplayed`) directly. Python 3.9+,
standard library only.

## Usage

Close Strawberry first, otherwise it overwrites the changes on exit.

```
# dry run (default): shows what would change, writes nothing
strawberryimport listenbrainz YOUR_USER

# write it; a timestamped backup of strawberry.db is made next to it
strawberryimport listenbrainz YOUR_USER --apply

# Last.fm needs an API key (https://www.last.fm/api/account/create)
strawberryimport lastfm YOUR_USER --api-key KEY --apply
```

Run without installing: `python3 -m strawberryimport ...` from a clone, or
`pip install .` (use a venv or pipx).

| option | meaning |
|---|---|
| `--db PATH` | database, default `~/.local/share/strawberry/strawberry/strawberry.db` |
| `--mode max` | (default) keep the higher of local and remote count |
| `--mode overwrite` | replace local counts with the remote ones |
| `--cache FILE` | save the downloaded history as JSONL and reuse it on later runs |
| `--refresh` | download again even if `--cache` exists |
| `--token` | ListenBrainz token, only for private profiles (or `LISTENBRAINZ_TOKEN`) |
| `--no-backup`, `--force` | skip the backup / write even if Strawberry is running |

## How matching works

Listens are grouped by normalised (artist, title): Unicode NFKC, case-folded,
whitespace collapsed. Each local song (`url` starting with `file://`) is
matched on its `artist` tag, falling back to `albumartist`. Songs with the same
tags in several files each get the full count. Album names and MusicBrainz IDs
are not used yet, so differing tags between your files and the service mean no
match.

Strawberry's own "write play counts to file tags" setting is separate; this
tool only touches the database.

## Status

The ListenBrainz source is tested against a real 290k-listen history. The
Last.fm source follows the documented `user.getRecentTracks` API but has not
been run against a live account yet.

## Tests

```
PYTHONPATH=. python3 -m pytest tests
```

MIT licensed.
