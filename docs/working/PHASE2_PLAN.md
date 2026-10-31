[Docs index](../en/README.md)

# Phase 2 plan: timing of the lyrics

Status: approved by the owner on 2026-10-31 with the recommended options (A1, B1, C1); the answers to the questions
are recorded in the last section. The keys and the feel of the page are settled with a mock-up first (milestone 1).

## Goal

Give every caption of a song its time, with as little work as possible, so the backdrop of Phase 1 shows the right
caption at the right moment:

1. A timed lyrics file next to the lyrics: when each caption starts and, where the song pauses, when it ends.
2. A tapping page: play the song, press a key at the start of each line, then correct the times while listening and
   looking at the waveform and at exact stills of the video.
3. Captions placed by time in the backdrop, with fades between consecutive lines and around pauses.
4. An architecture document in English with a Japanese twin (proposed in the Phase 1 acceptance report).

Not in this phase: whole videos (Phase 3), MusicXML drafts and automatic alignment (Phase 4).

Inputs: [Handoff](HANDOFF.md) §4 (timing), [Phase 1 acceptance](PHASE1_ACCEPTANCE.md), [Decisions](DECISIONS.md)
ADR-001 to ADR-004, and audio-spectrum-app's ADR-012 (its local web page).

## How captions follow the time

- A caption starts when its line is sung and ends when the singing pauses or the next caption starts. Where nothing
  is sung, no caption is shown (Q2: common in the owner's songs), so tapping records ends as easily as starts.
- **Lead:** captions appear a little before the singing, so the eye is ready (Q3; default 0.2 s). Stored times are
  the sung times; the lead is a design setting, so it can change without tapping again.
- **Transitions** (Q4): the fade length is a setting (default 0.3 s; today's videos used about 0.2 s to 0.5 s), and
  the change between captions sung back to back is a choice: `crossfade` (the old caption fades out while the new
  one fades in) or `sequential` (the old one fades out, then the new one fades in). Stills of both are compared
  before choosing the default.

The backdrop therefore blends up to two captions at a time during a crossfade (each a cached layer, so about twice
the per-frame cost of Phase 1 for those frames only).

## Options

### A. The tapping tool

| Option | For | Against | Recommendation |
|---|---|---|---|
| A1. A local web page (`lyrics-video sync`), like audio-spectrum-app's GUI: the browser plays the song and records each key press at the audio's own clock | Accurate times (the browser's audio clock, independent of key handling delays); a waveform and previews in one place; the start of the Phase 3 GUI | A small web server and a page to build and maintain | **Recommended** |
| A2. A terminal tool: play the song with an external player and time key presses | No web code | The player's start delay is unknown (tens to hundreds of ms); no waveform; corrections by editing numbers | Not recommended |
| A3. Write the times by hand in an editor while listening in a player | Nothing to build | Slow and error-prone; exactly the manual work to remove | Not recommended |

### B. The timed lyrics file

| Option | For | Against | Recommendation |
|---|---|---|---|
| B1. LRC next to the lyrics (`lyrics.lrc`): `[mm:ss.xx]` before each line, `;` still splits rows, a line with a time and no text ends the caption before it | A common, readable format; text and time stay together, so editing one line cannot shift others; other tools can read it | The text exists twice (lyrics.txt and the LRC) once a song is timed | **Recommended** |
| B2. A JSON or TOML file with times by line index of `lyrics.txt` | The text exists once | Adding or removing a line shifts every later time; unreadable on its own | Not recommended |
| B3. Times written into `lyrics.txt` itself | One file | Breaks the old format that `captions` reads | Not recommended |

With B1: the song file gains `timing = "lyrics.lrc"`. The page starts from `lyrics.txt` the first time and from the
LRC afterwards; when `lyrics.txt` changed since, the page lists the differences and keeps the times of lines whose
text is unchanged (matched in order). `captions` keeps reading `lyrics.txt`.

```text
[00:12.40]first row;second row
[00:17.85]the next caption
[00:23.10]
[00:41.00]after an instrumental part
```

### C. Dependencies for the page

| Option | For | Against | Recommendation |
|---|---|---|---|
| C1. FastAPI and uvicorn as normal dependencies | `uv sync` is enough; this app is a tool, not a library others embed | Larger install for the CLI alone | **Recommended** |
| C2. An optional `gui` extra, as in audio-spectrum-app | The CLI stays smaller | One more thing to remember when installing; little gain for one user | Not recommended |

## Design

### The page (`lyrics-video sync work/my-song/song.toml`)

Opens in the browser like audio-spectrum-app's GUI, with the same local protections, written for this app: the
server listens on `127.0.0.1` only, refuses foreign `Host` headers and API requests without the session token, and
sends no cross-origin headers. The song is streamed to the page with range requests so it can seek; because an
`<audio>` element cannot send headers, the token is accepted as a query parameter for that one route. Page texts in
Japanese, English, Spanish and French (Q6). Plain HTML, CSS and JavaScript without a build step.

- **Tap mode:** the lines are listed; play at normal speed (Q5) and mark the start and the end of each line. Two
  ways are tried in the mock-up: `Space` for a start and `Enter` for an end, or holding `Space` while a line is sung
  (press at its start, release at its end). `Backspace` undoes the last mark. Times come from the audio element's
  current time, minus a reaction offset (default 0, adjustable after a first try).
- **Adjust mode:** a waveform of the whole song (decoded in the browser) with a marker per time, a zoomed view
  around the selected line, buttons to move a time by ±0.05 s and ±0.5 s or to drag it, "play from 2 s before this
  line", and a still of the video at the selected moment (`render_stills` through the backdrop, so it is the exact
  frame).
- **Save** writes the LRC safely (temporary file and rename, a `.bak` copy of the previous one). Nothing is written
  without pressing Save; leaving with unsaved changes asks first.

### Captions by time

| Module | Content |
|---|---|
| `timing.py` | Reading and writing LRC (validated: times increasing, inside the song, rows at most two); merging with `lyrics.txt` |
| `backdrop.py` | `TimedCaption` list from the timing; the caption opacities at a time (lead, crossfade, fades at pauses) |
| `design.py` | Caption `lead_seconds`, `fade_seconds`, `transition` (`"crossfade"` or `"sequential"`) |
| `still.py` | With timing, `--time` shows the caption of that moment; `--caption` stays for songs without timing |
| `web/` | The server, the page, its messages in four languages |

### Tests

Generated text, signals and images only.

- LRC: reading, writing, round trip, ends, invalid files with line numbers, the merge with a changed `lyrics.txt`.
- Opacities: lead, crossfade between consecutive captions, fades around pauses, the first and the last caption,
  captions shorter than their fades.
- Backdrop: two captions blended during a crossfade; stills at chosen times show the expected caption.
- Server (FastAPI's test client): token and host checks, the token in the audio URL only for audio, range requests,
  loading and saving timing (safe write, backup), previews; message files complete in four languages. The page
  itself is checked by hand in a browser.

### Architecture document

`docs/{en,ja,es}/ARCHITECTURE.md`: the layers (song file and designs; layers and backdrop; audio-spectrum-app;
commands and the page), the data flow from song file to still, the invariants (frame `n` at `n / fps`, backdrop
picklable and pure, nothing written without an explicit command or Save), performance notes (ADR-004) and extension
points (new caption styles, alignments, designs).

## Milestones and commits

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `docs: add Phase 2 plan` | This plan (approved) |
| 1. Mock-up | none | A page with the planned layout and both ways of tapping, in `work/mock/` (not committed), working on any song chosen in the browser; the owner tries it and the keys and layout are settled before the real page is built (Q5) |
| 2. Captions by time | `feat: place captions by time from an LRC file` | `timing.py`, opacities with lead and crossfades, `still` by time, tests, user guide |
| 3. Tapping page | `feat: add the sync page for tapping and adjusting times` | Server, page (tap and adjust), safe save, tests, user guide |
| 4. Architecture and acceptance | `docs: accept Phase 2` | `ARCHITECTURE.md` in English and Japanese, a song timed by the owner, `PHASE2_ACCEPTANCE.md` |

## Acceptance criteria

| Criterion | How it is checked |
|---|---|
| The owner times a whole song with the page in about the song's length plus a few minutes of corrections | The owner tries it; the time spent is recorded |
| Stills at chosen moments show the right caption, entering and leaving as wished | Stills around a few line changes and a pause, with both transitions, checked by the owner |
| Times survive a round trip (page → LRC → page) unchanged, and a changed `lyrics.txt` keeps the times of unchanged lines | Tests |
| Frames with a crossfade stay under 20 ms at 1080p (others as in Phase 1) | `tools/time_backdrop.py` |
| The page cannot be driven by other web pages, and nothing is written without Save | Server tests (token, host); by hand |
| Docs (including the architecture) in English and Japanese, nothing private committed | Hash check, file review, `gitleaks` |

## Questions for the owner

Answers (2026-10-31):

- Q1: the recommended options A1, B1 and C1.
- Q2: pauses are common; where nothing is sung, captions are off.
- Q3: captions appear a little before the singing.
- Q4: the fade length is adjustable (today's videos used about 0.2 s to 0.5 s, not 2 s), and crossfade or
  fading out then in is a choice.
- Q5: normal speed is enough; the keys and the feel are checked with a mock-up first.
- Q6: the page speaks Japanese, English and Spanish. Amended 2026-11-01: French is added (four UI languages); docs
  are English and Japanese only.
- Q7: the matching lyrics for the song in `work/design/` are in place.
- Q8: caption PNGs alone will no longer be needed once whole videos are made; `captions` and `compare` stay until
  Phase 3 delivers videos, and their removal is planned there.

The questions as asked:


- Q1. Options A to C: are the recommendations (A1 a local web page, B1 an LRC file, C1 FastAPI as a normal
  dependency) fine?
- Q2. Pauses: do your songs often have instrumental parts where no caption should show, or should a caption usually
  stay until the next one starts?
- Q3. Lead: should captions appear a little before the singing (for example 0.2 s), exactly on it, or later?
- Q4. Transitions: between lines sung back to back, a short crossfade (for example 0.5 s), or today's 2 s fade out
  and in? Around pauses, today's 2 s?
- Q5. Keys: are `Space` for "next line starts", `Enter` for "caption ends here" and `Backspace` for undo fine? Would
  slower playback (0.75×) help while tapping?
- Q6. Should the page speak Japanese, English and Spanish like audio-spectrum-app's, or Japanese only for now?
- Q7. For the acceptance, which song and lyrics should be timed? The lyrics in `work/design/` belong to another song
  than its audio; please put the matching `lyrics.txt` for the song in `work/design/` (or another song's audio and
  lyrics in a new folder).
- Q8. After timing, should the page also offer making the caption PNGs, or is that no longer needed once whole videos
  come in Phase 3?
