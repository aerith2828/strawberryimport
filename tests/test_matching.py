from strawberryimport.matching import plan, tally

LISTENS = [
    (100, "Artist", "A", "Song"),
    (300, "ARTIST ", "A", "song"),
    (200, "Other", "B", "Track"),
    (50, "x", "y", ""),
]


def test_tally_normalises_and_skips_empty_titles():
    t = tally(LISTENS)
    assert t[("artist", "song")] == (2, 300)
    assert ("x", "") not in t


def test_plan_max_keeps_higher_local_count():
    rows = [(1, "Artist", "", "Song", 5, 400), (2, "Other", "", "Track", 0, None)]
    updates, matched = plan(rows, tally(LISTENS), "max")
    assert updates == [(1, 200, 2)]
    assert (5, 400, 1) not in updates
    assert len(matched) == 2


def test_plan_overwrite_replaces_count():
    rows = [(1, "Artist", "", "Song", 99, 400)]
    updates, _ = plan(rows, tally(LISTENS), "overwrite")
    assert updates == [(2, 300, 1)]


def test_plan_falls_back_to_albumartist():
    rows = [(1, "", "Other", "Track", 0, None)]
    updates, _ = plan(rows, tally(LISTENS))
    assert updates == [(1, 200, 1)]
