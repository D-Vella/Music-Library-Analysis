# Music Library Analyser — Project Roadmap

> A read-only Python tool that scans the music library on the NAS, extracts file and tag metadata into a local DuckDB database, and produces console reports on library size, artist coverage, lyrics availability and metadata health.
> Designed for spare-time development — each phase delivers something working and useful on its own.

*Started: 14 Nov 2026*

---

## How To Use This Roadmap

Each phase is designed to be self-contained and completable in one to three sessions of 30–90 minutes. A phase should always leave the project in a working state. Before starting a new phase, check the exit criteria of the current one: if you cannot tick every item, the phase isn't done yet.

Log discoveries in the **Field Notes** section at the bottom as you go.

---

## Concepts Primer — How Music Metadata Actually Works

Read this before Phase 1. It is the "why" behind most of the design decisions below.

### Tags live inside the audio file

An audio file is a container with two parts: the audio stream and a block of metadata ("tags"). Media servers and players (Plex, Jellyfin, phone apps, MusicBrainz Picard) read that block to build their libraries. They mostly ignore folder and file names, so if the tags are wrong or missing, the library looks wrong, however tidy the folders are.

### Each format has its own tag system

This is the main complication. The same piece of information has a different name and shape depending on the file type:

| Concept | MP3 (ID3v2 frames) | FLAC / OGG (Vorbis comments) | M4A / AAC (MP4 atoms) |
|---|---|---|---|
| Title | `TIT2` | `TITLE` | `©nam` |
| Artist | `TPE1` | `ARTIST` | `©ART` |
| Album artist | `TPE2` | `ALBUMARTIST` | `aART` |
| Album | `TALB` | `ALBUM` | `©alb` |
| Track number | `TRCK` → `"3/12"` (one string) | `TRACKNUMBER` + `TRACKTOTAL` (two fields) | `trkn` → `[(3, 12)]` (a tuple) |
| Year / date | `TDRC` (v2.4) or `TYER` (v2.3) | `DATE` | `©day` |
| Genre | `TCON` | `GENRE` | `©gen` |
| Unsynced lyrics | `USLT` | `LYRICS` or `UNSYNCEDLYRICS` | `©lyr` |
| Cover art | `APIC` frame | **not in the tags**: separate picture blocks (`audio.pictures`) | `covr` |
| MusicBrainz IDs | `TXXX:MusicBrainz Album Id`, `UFID` | `MUSICBRAINZ_ALBUMID` etc. | `----:com.apple.iTunes:MusicBrainz Album Id` |

Other things to know:
- **mutagen lower-cases Vorbis keys** when you read them (`ALBUMARTIST` comes back as `albumartist`).
- **Vorbis comments can repeat a key.** A FLAC file can have two `ARTIST` entries or three `GENRE` entries, so values come back as **lists**, not strings.
- **ID3 has versions.** v2.3 and v2.4 use different date frames, and some old files also carry an ID3v1 tag (a fixed 128-byte block at the *end* of the file).
- **Album artist matters more than artist.** Media servers usually group albums by album artist. A compilation or a "feat." track with no album artist is the classic cause of albums splitting into fragments.

### Lyrics come in two places and two flavours

- **Embedded:** inside the tags (`USLT` / `LYRICS` / `©lyr`).
- **Sidecar file:** a file next to the track with the same name, e.g. `01 - Song.flac` + `01 - Song.lrc`.
- **Synced vs unsynced:** `.lrc` content has timestamps (`[01:23.45] line of lyrics`) so players can scroll it in time. Plain text has none. Some tools write synced LRC text *into* the embedded lyrics tag, so you detect "synced" by looking for the timestamp pattern, not by where the lyrics live.

### The library: `mutagen`

[`mutagen`](https://mutagen.readthedocs.io/) is the standard Python library for reading (and writing) tags across all of these formats. `mutagen.File(path)` looks at the file, works out what it is, and returns the right object:
- `audio.info` → technical stream info: duration, bitrate, sample rate, channels
- `audio.tags` → the raw tag block in that format's own naming (or `None` if the file has no tags)

It also has an "easy" mode (`mutagen.File(path, easy=True)`) that maps MP3/M4A keys to friendly names like `artist`. It's handy, but it hides things (lyrics, many custom fields), so we start with **raw** tags to see what's really there and write our own mapping later.

### The architecture in one sentence

**Scan the NAS once (slow, I/O-bound) into a local DuckDB file, then run every report against DuckDB (fast, repeatable).** That's the same idea as the API caching in earlier projects: keep the expensive, slow source separate from the analysis layer. It also means a future graphical front end (e.g. Streamlit) just reads the same DuckDB file, with no rework.

```
NAS (read-only) ──scan──▶ data/library.duckdb ──SQL──▶ console reports
                                              └──────▶ (later) Streamlit
```

---

## Phase 1 — Environment & First Contact
**Goal:** Get tooling in place and read the tags of real files from the NAS with your own eyes.
**Estimated effort:** 1 session

### Tasks
- [X] Create the folder structure
  ```
  music-library-analyser/
  ├── src/
  │   ├── __init__.py
  │   ├── scanner.py     # walks the NAS → file inventory        (Phase 2)
  │   ├── tags.py        # mutagen → standardised dict          (Phase 4)
  │   ├── lyrics.py      # sidecar + embedded lyrics detection  (Phase 6)
  │   ├── store.py       # DuckDB read/write helpers            (Phase 2)
  │   └── reports.py     # runs report SQL, prints tables       (Phase 7)
  ├── sql/reports/       # one .sql file per report             (Phase 7)
  ├── notebooks/         # exploration
  ├── tests/
  ├── data/              # library.duckdb lives here (gitignored)
  ├── spikes/            # throwaway experiments
  ├── main.py            # CLI entry point: scan / report
  ├── config.py          # loads settings from .env
  ├── requirements.txt
  └── .env               # LIBRARY_ROOT=\\NAS\music  (machine-specific, never commit)
  ```
- [X] Create a virtual environment and `pip install mutagen python-dotenv`
- [X] Add `.env`, `data/`, `.venv/` and `__pycache__/` to `.gitignore`
- [X] Confirm Python can see the NAS. On Windows a UNC path works directly with `pathlib`, no mapped drive needed: `Path(r"\\NAS-NAME\music").exists()`
- [X] Write `spikes/read_one_file.py` and run it against one MP3, one FLAC and one M4A (whichever formats you have):
  ```python
  import sys
  import mutagen

  path = sys.argv[1]
  audio = mutagen.File(path)  # returns None if mutagen doesn't recognise the file
  if audio is None:
      sys.exit("Not a recognised audio file")

  print(f"Container : {type(audio).__name__}")
  print(f"Duration  : {audio.info.length:.1f}s")
  print(f"Bitrate   : {getattr(audio.info, 'bitrate', 'n/a')}")
  print(f"Tag format: {type(audio.tags).__name__ if audio.tags else 'NO TAGS'}")
  print("-" * 60)
  for key, value in (audio.tags or {}).items():
      print(f"{key:<35} {str(value)[:80]}")  # truncate: cover art is binary

  # FLAC keeps artwork outside the tags
  if hasattr(audio, "pictures"):
      print(f"\nEmbedded pictures: {len(audio.pictures)}")
  ```
- [X] Note in Field Notes what surprised you: key names, list-wrapped values, anything missing
- [X] First commit: skeleton + spike

### Exit Criteria
You have printed the raw tags of at least one file of each format in your library, straight off the NAS, and the skeleton is committed.

---

## Phase 2 — File Inventory
**Goal:** Know what's physically in the library before reading any tags. This answers "how big is it?" and "what formats?" on its own.
**Estimated effort:** 1 session

### Tasks
- [X] `pip install duckdb pyarrow`
- [X] Write `src/scanner.py` with `walk_library(root) -> Iterator[dict]` that yields one record per file (**every** file, not just audio: it'll surface `.lrc`, `.jpg`, `.cue`, `.log` and stray junk)
- [X] Record per file: `path`, `relative_path`, `parent_folder`, `stem` (filename without extension), `extension` (lower-cased), `size_bytes`, `modified_at`
- [X] Use `os.scandir` (or `Path.rglob`) and read size/mtime from the `stat` result. Don't open the files at all yet, so this stays fast
- [X] Write `src/store.py` with a helper that takes a list of dicts and does `CREATE OR REPLACE TABLE files AS ...` in `data/library.duckdb` (build a `pyarrow.Table.from_pylist(records)` and DuckDB can select from it directly)
- [X] First throwaway report, straight in the DuckDB CLI or a notebook: total size in GB, file count by extension, number of top-level (artist) folders

### Exit Criteria
`files` table exists with every file in the library. You know the total size and the format breakdown, and you've noted any surprises (unexpected extensions, oddly placed files) in Field Notes.

---

### Pre-task — Make the project installable (~30 min)
**Why:** A script or notebook looks for imports starting from *its own* folder, not the project root, so `notebooks/` can't see your code without `sys.path` hacks. (Databricks hides this by putting the repo root on the path for you.) Installing the project as an editable package fixes it everywhere, once.

- [ ] Move the code into a named package: `src/scanner.py` → `src/music_analyser/scanner.py` (same for `store.py` etc.), with `src/music_analyser/__init__.py`
- [ ] Add `pyproject.toml` at the repo root:
  ```toml
  [project]
  name = "music-analyser"
  version = "0.1.0"
  requires-python = ">=3.12"
  dependencies = ["mutagen", "duckdb", "pyarrow", "python-dotenv"]

  [project.optional-dependencies]
  dev = ["pytest", "ipykernel"]

  [build-system]
  requires = ["setuptools>=61"]
  build-backend = "setuptools.build_meta"
  ```
- [ ] With the venv active: `pip install -e ".[dev]"` (`-e` = editable: Python links to your source folder, so code changes apply immediately without reinstalling)
- [ ] Replace imports with `from music_analyser.scanner import walk_library` and delete every `sys.path` line
- [ ] Delete `requirements.txt`, since `pyproject.toml` is now the single list of dependencies
- [ ] In VS Code, check the notebook kernel (top right) is the project's `.venv`, not the global Python
- [ ] Commit, then confirm a fresh terminal and a notebook can both import the package

**Done when:** imports work from scripts, notebooks and tests with no `sys.path` lines anywhere.

---

## Phase 3 — Tag Exploration
**Goal:** Understand the tag landscape of *your* library before deciding what to normalise. Explore first, design second.
**Estimated effort:** 1–2 sessions

### Tasks
- [ ] In `notebooks/01_tag_exploration.ipynb`, take a sample from the `files` table: ~200 audio files, spread across extensions and artists (`USING SAMPLE` in DuckDB, or stratify by extension)
- [ ] Read raw tags for the sample into a **long table**: one row per `(path, tag_format, tag_key, tag_value)`. This shape copes with any key from any format without knowing them in advance
- [ ] Query it: which keys exist per format, and in what % of files? Which keys appear more than once per file (multi-value)?
- [ ] Look specifically for: album artist coverage, MusicBrainz IDs, lyrics keys, track/disc number formats, date formats
- [ ] Decide your **normalised field list** and write the per-format mapping table into Field Notes (start from the primer table above and adjust to what you found)

### Exit Criteria
You have a written list of the fields you'll normalise and the per-format source key for each, based on evidence from your own files rather than guesswork.

---

## Phase 4 — Normalised Tag Reader
**Goal:** One function that turns any supported audio file into the same predictable dict.
**Estimated effort:** 2 sessions

### Tasks
- [ ] Write `src/tags.py` with `read_track(path) -> dict`
- [ ] Use a mapping dict per format (from Phase 3) instead of `if/elif` chains, e.g. `FIELD_MAP = {"album_artist": {"ID3": "TPE2", "VComment": "albumartist", "MP4Tags": "aART"}, ...}`
- [ ] Small helpers: `parse_number_pair("3/12") -> (3, 12)`, `first_or_join(values)` for multi-value fields (decide: keep first, or join with `"; "`, and note the decision)
- [ ] **Never raise.** Wrap the read so a corrupt file returns the dict with `read_error` populated instead of killing a 20,000-file scan
- [ ] Also return the raw `(key, value)` pairs so Phase 5 can keep the long table too
- [ ] Tests: `pip install pytest`. Make tiny fixture files (`ffmpeg -f lavfi -i anullsrc -t 1 silence.flac`, likewise `.mp3` and `.m4a`), tag a *temporary copy* in a pytest fixture, then assert `read_track` returns what you wrote. Cover a file with no tags too

### Standardised Output Shape
```python
{
    # identity / file facts (from Phase 2)
    "path": str,                 # unique key
    "relative_path": str,
    "extension": str,
    "size_bytes": int,
    # container / stream
    "container": str,            # "MP3", "FLAC", "MP4"
    "tag_format": str | None,    # "ID3", "VComment", "MP4Tags", None = untagged
    "duration_s": float | None,
    "bitrate": int | None,
    "sample_rate": int | None,
    "bits_per_sample": int | None,  # None for lossy formats
    "channels": int | None,
    # core tags
    "title": str | None,
    "artist": str | None,
    "album_artist": str | None,
    "album": str | None,
    "track_number": int | None,
    "track_total": int | None,
    "disc_number": int | None,
    "disc_total": int | None,
    "date": str | None,          # keep raw; parse a year column in SQL later
    "genre": str | None,
    "mb_track_id": str | None,
    "mb_album_id": str | None,
    "mb_artist_id": str | None,
    # presence flags
    "has_embedded_art": bool,
    "embedded_lyrics": str | None,  # filled properly in Phase 6
    # housekeeping
    "read_error": str | None,
}
```

### Exit Criteria
`read_track` returns the same shape for MP3, FLAC and M4A, returns a populated `read_error` instead of crashing on a bad file, and the pytest suite passes.

---

## Phase 5 — Full Library Scan
**Goal:** Run the reader across the whole library and land it in DuckDB.
**Estimated effort:** 1–2 sessions

### Tasks
- [ ] `main.py scan` (use `argparse` subcommands, which gives you room for `report` later)
- [ ] Pipeline: inventory (Phase 2) → filter to audio extensions → `read_track` each → write `tracks` (wide, one row per file) and `raw_tags` (long) tables, full refresh (`CREATE OR REPLACE`)
- [ ] `--limit N` flag so development runs take seconds, not minutes
- [ ] Progress output (a counter every 500 files is enough; `tqdm` if you fancy it)
- [ ] End-of-run summary: files read, files failed, elapsed time, files/second
- [ ] Record the run in a small `scan_runs` table (started_at, finished_at, root, counts). Cheap to add now, and useful later

### Exit Criteria
A full scan completes end to end. Every audio file is either in `tracks` with tags or listed with a `read_error`. You know roughly how long a full scan takes (note it in Field Notes).

---

## Phase 6 — Lyrics Coverage
**Goal:** Know, per track, whether lyrics exist, where, and whether they're synced.
**Estimated effort:** 1 session

### Tasks
- [ ] Sidecar detection in SQL, no extra I/O: join `tracks` to `files` on same `parent_folder` + same `stem` where extension is `.lrc` or `.txt`
- [ ] Embedded detection: you already captured `embedded_lyrics` in Phase 4. Make sure it covers `USLT` (any language, e.g. `USLT::eng`), `LYRICS`, `UNSYNCEDLYRICS`, `©lyr`
- [ ] Classify synced vs plain with a regex for LRC timestamps: `\[\d{1,2}:\d{2}(\.\d{1,3})?\]`. For sidecars this means reading the small `.lrc`/`.txt` files, so do it during the scan, not in reports
- [ ] Derive a single `lyrics_status` per track: `synced_sidecar`, `plain_sidecar`, `synced_embedded`, `plain_embedded`, `none` (decide precedence if a track has several, and note it)

### Exit Criteria
Every track has a `lyrics_status`, and you can say what % of the library has lyrics of each kind.

---

## Phase 7 — Console Reports
**Goal:** Turn the database into readable reports. **Reports never touch the NAS.**
**Estimated effort:** 1–2 sessions

### Tasks
- [ ] One `.sql` file per report in `sql/reports/`, so the SQL stays readable and testable in DBeaver/DuckDB CLI
- [ ] `main.py report <name>` loads the SQL, runs it, prints a table (`pip install rich` for nice tables, or plain `print` first)
- [ ] Reports:
  - `summary`: total tracks, albums, artists, size (GB), total duration (days/hours), last scan time
  - `artists`: tracks and albums per album artist, sortable, with `--top N`
  - `formats`: count and size by format; lossless vs lossy; sample rate / bit depth spread
  - `completeness`: % of tracks with each normalised field populated
  - `lyrics`: coverage by `lyrics_status`, plus per-artist coverage
- [ ] `main.py report all` prints them one after another

### Exit Criteria
Every report runs in a couple of seconds from the local database and prints a readable table.

---

## Phase 8 — Metadata Health Checks
**Goal:** Find the specific problems that make media servers show your library badly. This is the core "understand my metadata" payoff.
**Estimated effort:** 1–2 sessions

### Tasks
- [ ] Each check is a SQL query returning offending rows, with a count-only summary view. Candidates:
  - Missing album artist
  - **Album consistency:** within one album (folder), more than one album artist, album title, date or disc total
  - **Artist name variants:** names that match after lower-casing, trimming and stripping a leading "The" (`Ghost` vs `ghost` vs `Ghost `)
  - Track number gaps or duplicates within an album/disc
  - Missing MusicBrainz IDs (album- and track-level)
  - No embedded art *and* no `cover.jpg`/`folder.jpg` in the folder
  - Mixed formats within one album folder
  - Untagged files (`tag_format` is null) and files with `read_error`
- [ ] `main.py report health` prints the summary; `main.py report health --check album_consistency` lists the offending albums
- [ ] Optional: point your `dqcheck` library at the `tracks` table (as a DataFrame) to see whether it catches anything your SQL checks miss. Good dogfooding for both projects

### Exit Criteria
A single command tells you how many problems of each type exist, and you can drill into any one to get a fix list.

---

## Phase 9 — Stretch Goals
**Goal:** Only once Phases 1–8 are done and the reports have shown their value.
**Estimated effort:** 1–2 sessions per item

### Candidates
- [ ] **Incremental scan:** skip files whose `size_bytes` + `modified_at` haven't changed since the last scan
- [ ] **Scan history:** keep each scan's results (or Parquet snapshots) so you can see whether the library is getting healthier over time
- [ ] **Streamlit dashboard** reading the same DuckDB file (the graphical step)
- [ ] **Artwork quality:** embedded/folder art dimensions via Pillow, flag anything under e.g. 500×500
- [ ] **Export fix lists** to CSV for working through in MusicBrainz Picard
- [ ] Cross-reference artists against the Bands & Artists Notion database *(scope creep alert: a separate project's worth of work)*

### Notes
Add stretch goals one at a time. Be honest about which are worth automating. Fixing 15 albums by hand in Picard beats a three-session auto-fixer.

---

## Field Notes
*Running log of discoveries and decisions: honest and practical, not polished.*

- 2026-11-14 — Project started. Decision: **the tool is strictly read-only.** Nothing in this codebase calls mutagen's `.save()` against library files (test fixtures use temporary copies only). Consider a read-only NAS user/share for the scanner as belt-and-braces.
- 2026-11-14 — Decision: DuckDB as the local store (`data/library.duckdb`), full refresh per scan. Scan once, query many.
- 2026-11-14 — Decision: keep both a wide `tracks` table (for reports) and a long `raw_tags` table (for exploration) so normalising never loses information.
- [Date] — Formats found in library: …
- [Date] — Full scan time / files per second over SMB: …

---

## Dependencies Reference

| Library | Purpose | Phase | Install |
|---------|---------|-------|---------|
| `mutagen` | Read audio tags & stream info | 1 | `pip install mutagen` |
| `python-dotenv` | Load `LIBRARY_ROOT` from `.env` | 1 | `pip install python-dotenv` |
| `duckdb` | Local analytical store + SQL reports | 2 | `pip install duckdb` |
| `pyarrow` | Build tables from lists of dicts for DuckDB | 2 | `pip install pyarrow` |
| `ipykernel` | Notebook kernel for exploration | 3 | `pip install ipykernel` |
| `pytest` | Tests for the tag reader | 4 | `pip install pytest` |
| `rich` | Pretty console tables (optional) | 7 | `pip install rich` |
| `ffmpeg` (CLI) | Generate tiny test fixture files | 4 | system install |

---

## Principles To Keep In Mind

**Read-only, always.** This tool inspects the library; it never edits it. Fixes happen in a tagger (e.g. Picard) where you can see what you're changing.

**Scan once, query many.** The NAS is the slow, fragile part. Touch it in one place (`scan`) and let everything else read DuckDB.

**Raw before normalised.** Look at what's really in the files (Phase 3) before deciding the shape (Phase 4). Normalising too early bakes in assumptions.

**One bad file must not kill the run.** Per-file `try/except`, errors recorded as data, summary at the end.

**Each phase should leave the project working.** If you run out of time, commit what works and leave a note in Field Notes.

**Prefer manual over fragile automation.** Time is the scarce resource on a spare-time project.