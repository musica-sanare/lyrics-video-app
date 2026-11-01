[Docs index](../en/README.md)

# Phase 7 plan: an app icon and preparing the repository to go public

Status: approved by the owner on 2026-11-01 with every recommended option (A1 and A3, B chosen from three
candidates in milestone 1, C2, D, refs `main` and `dev`).

## Goal

1. **An icon for Lyrics Video.app.** The Dock shows the app with its own icon instead of the default one. The icon
   is drawn by this repository's code, so no image file and no third-party artwork enters the repository.
2. **The repository ready to go public.** Every item of `docs/working/PUBLIC_RELEASE.md` is done, deferred with a
   reason, or not applicable, so the owner can switch the visibility whenever they decide to. The switch and the
   GitHub settings right after it are the owner's steps; this phase writes them down and does not perform them.

Not in this phase: MusicXML draft timing and automatic alignment, line clips, a measured render time with a heavier
spectrum (open items of the [Phase 6 acceptance](PHASE6_ACCEPTANCE.md)); continuous integration on GitHub; publishing
to PyPI or any other registry.

Inputs: [Phase 6 acceptance](PHASE6_ACCEPTANCE.md), [Decisions](DECISIONS.md) ADR-012, `app_bundle.py`, the
`claude-shared-rules` repository's `docs/en/PUBLIC_RELEASE.md`, its checklist template and its preparation prompt.

## Today

- `install-app` writes `Info.plist` and one shell script. Without `CFBundleIconFile` the Dock shows the generic app
  icon.
- Measured on this Mac: an icon set of PNGs drawn with Pillow (16 px to 1024 px) turns into an `.icns` file with
  macOS's own `iconutil -c icns` in well under a second. Pillow is already a dependency; `iconutil` comes with macOS.
- `.gitignore` excludes PNG, JPEG and other images and every font file, so the icon's PNGs can never be committed by
  accident (`.icns` is not listed; the bundle is written outside the repository).
- The repository is private on GitHub with `main` and `dev`; there is no CI and no `.github/`. `LICENSE` is MIT and
  `pyproject.toml` says so. A gitleaks scan of the current history found nothing (Phase 6).
- Files ever committed outside `src/`, `tests/` and `docs/`: `.gitignore`, `CLAUDE.md`, `LICENSE`, the READMEs (and
  a removed `README.es.md`), the two examples, `pyproject.toml`, two scripts in `tools/`, `uv.lock`.
- audio-spectrum-app is a path dependency (`../audio-spectrum-app`, editable). A public clone of this repository
  installs only if audio-spectrum-app is checked out next to it. audio-spectrum-app has the tag `v0.5.0`; since then
  its `dev` changed only its docs and its own page's French locale, nothing this app uses.

## Options

### A. Where the icon comes from

| Option | For | Against | Recommendation |
|---|---|---|---|
| A1. Drawn by code (`app_icon.py`, Pillow) when `install-app` runs, turned into `AppIcon.icns` with `iconutil` | No image in the repository; no license question; the drawing is reviewable code; sizes are always sharp | A simple, geometric look only | **Recommended** |
| A2. An image file committed to the repository | Any look | A binary in Git; its license and origin must be clear; needs a `.gitignore` exception | Not recommended |
| A3. `install-app --icon IMAGE`: the owner's own square image, converted the same way, never committed | The owner can use their own artwork | Kept only on this Mac; installing again needs the option again | **Recommended as an addition to A1** |

### B. What the icon shows (A1)

All candidates use only shapes and the app's own colors (the page's dark background and accent blue), no text and
no fonts, inside macOS's rounded-square outline with the usual margin.

| Option | Picture |
|---|---|
| B1. Spectrum and caption | Spectrum bars rising from the bottom, with one light, rounded caption line above them |
| B2. Waveform and tap marks | A waveform with a green start mark and an orange end mark, like the sync page |
| B3. Caption only | Two stacked caption lines on a gradient, like a lyrics frame |

Recommendation: draw all three in milestone 1 into the ignored `work/icons/` folder and let the owner choose (Q2).

### C. audio-spectrum-app in a public repository

| Option | For | Against | Recommendation |
|---|---|---|---|
| C1. Keep the path dependency; the quick start says to clone both repositories side by side | Both repositories keep changing together, as today | A clone alone does not install; audio-spectrum-app must be public too | Fine while both change |
| C2. Depend on audio-spectrum-app's Git tag `v0.5.0` on GitHub; a local override keeps the editable sibling for development | `git clone` and `uv sync` work alone; the version this app needs is fixed | audio-spectrum-app must be public too; changing both together needs the override (documented) | **Recommended**, if audio-spectrum-app goes public first or at the same time |
| C3. Publish audio-spectrum-app to PyPI | Simplest install | A registry release is the owner's step and a new commitment; out of scope | Not now |

If audio-spectrum-app stays private, this repository can still go public, but its quick start cannot work for
others; the README then says so (Q3).

### D. What else becomes public

| Item | Recommendation | Reason |
|---|---|---|
| `CLAUDE.md`, `docs/working/` (plans, acceptance reports, ADRs, `HANDOFF.md`) | Keep | Written for a public repository from the start; they explain the design. Each file is read again in milestone 2 for anything private |
| `SECURITY.md` | Add a short one | The app runs a local web server (127.0.0.1, token, host checks); reports go to GitHub's private vulnerability reporting |
| `CONTRIBUTING.md`, issue and pull request templates | Not added | The owner has not asked for outside contributions |
| GitHub Actions | None; Actions disabled after the switch | The tests need macOS, ffmpeg, the sibling repository and system fonts; local tests are the check |

## Design

### The icon (A1, A3)

- `src/lyrics_video/app_icon.py`: `draw_icon(size) -> Image` draws the chosen design (B) at any size;
  `write_icns(path, source=None)` draws, or loads the owner's image (A3: cropped to a square, scaled down only),
  writes the ten PNGs of an `.iconset` into a temporary folder and runs `iconutil -c icns`.
- `install-app` writes `Contents/Resources/AppIcon.icns` and `CFBundleIconFile = AppIcon`. `--icon IMAGE` uses the
  owner's image instead. A missing `iconutil` (not macOS) leaves the default icon with a warning; the app still works.
- The Dock caches icons: after `install-app --overwrite` the owner removes the app from the Dock and drags it back
  once. The user guide says so.
- Tests: the drawing at several sizes (size, alpha corners transparent, deterministic pixels for the same size), the
  `.icns` written into a temporary bundle (skipped without `iconutil`), `--icon` with a generated image, and
  `Info.plist` naming the icon.

### Preparing the public release

Following the shared procedure, in this repository:

- `docs/working/PUBLIC_RELEASE.md` from the shared template, linked from both indexes, with each result and date.
- Scope: the owner runs or allows `git ls-remote origin` (it reaches GitHub); the owner decides which branches and
  tags are published (`main`, `dev`, tags).
- History: `gitleaks git --log-opts="--all" --redact .` and the manual checks (identities, co-author lines, every
  file ever committed, local paths, email addresses), over every ref to be published.
- Content: identifiers (none expected: no cloud resources), third-party material (system font names in docs and
  tests only; no fonts, songs, lyrics or images), internal notes (section D).
- Licenses: each runtime dependency's license against MIT (expected: Pillow, NumPy, FastAPI, uvicorn, pydantic,
  tomlkit, audio-spectrum-app; ffmpeg is an external tool the owner installs, not distributed).
- Dependency audit: a vulnerability check of the locked dependencies. The tool is chosen in milestone 2 from uv's
  current docs; if it needs a new tool (for example `pip-audit` through `uvx`, free, it queries a public advisory
  database), the owner approves it first.
- Presentation: README and README.ja status and a quick start that works from a fresh clone (checked in a temporary
  folder with C2), `SECURITY.md`.
- Owner steps written in the checklist: the switch, then GitHub settings for this repository (private vulnerability
  reporting, push protection, Dependabot alerts, a ruleset on the default branch, Actions disabled, unused features
  off), with setting names checked against GitHub Docs and the date.

### Documentation

- User guide (English and Japanese): the icon, `--icon`, and refreshing the Dock.
- Architecture (English and Japanese): `app_icon.py` in the bundle.
- ADR-014: the icon drawn by code (A1, A3, B). ADR-015: audio-spectrum-app by Git tag (C), if chosen.
- `CLAUDE.md`: the dependency line, if C2 is chosen.

## Milestones and commits

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `docs: add Phase 7 plan` | This plan |
| 1. Icon | `feat: draw an icon for the app` | Three candidates drawn into `work/icons/` for the owner; the chosen one in `app_icon.py`; `install-app` writes the `.icns`; `--icon`; docs |
| 2. Release checklist | `docs: add public release checklist` | `PUBLIC_RELEASE.md` with the scope, history, content and license results; `SECURITY.md`; items marked `要確認` for the owner |
| 3. Dependency and quick start | `build: depend on audio-spectrum-app by tag` | C2 (if chosen): Git tag dependency, local override for development, README quick start checked from a fresh clone |
| 4. Owner's check | none | The owner installs the app again and sees the icon in the Dock; answers the checklist's `要確認` items |
| 5. Acceptance | `docs: accept Phase 7` | ADR-014 (and ADR-015), `PHASE7_ACCEPTANCE.md`, the final scan on the commit to publish, version 0.6.0 |

The switch to public and the settings right after it come after this phase, when the owner decides; the checklist's
last sections are filled in then, in their own commit.

## Acceptance criteria

| Criterion | How it is checked |
|---|---|
| Lyrics Video.app shows its own icon in the Dock and Finder | The owner tries it |
| No image, icon or font file is committed; the icon comes from code or the owner's local image | File review; `.gitignore` unchanged for images |
| `install-app` still works without `iconutil` (default icon, a warning) | Tests |
| Every item of `PUBLIC_RELEASE.md` is done, deferred with a reason, or not applicable, with dates | Review of the checklist |
| The secret scan covers every ref to be published and finds nothing, also on the final commit | `gitleaks` output recorded |
| The README quick start works from a fresh clone without access to private resources (C2 with a public audio-spectrum-app), or the README says why not | A clone into a temporary folder |
| The owner has numbered steps for the switch and the GitHub settings right after it | The checklist |
| Docs in English and Japanese | Hash check |

## Carried over

- The Mermaid diagrams changed in Phases 3 to 6 need a look on GitHub after the next push. This also belongs to the
  public release check.

## Questions for the owner

Answers (2026-11-01): the owner accepted every recommendation.

- Q1: A1 with A3; `CLAUDE.md` and `docs/working/` stay public; `SECURITY.md` is added; no contribution guide and no
  CI (D).
- Q2: the three candidates (B1, B2, B3) are drawn into `work/icons/` in milestone 1 and the owner chooses one.
- Q3: audio-spectrum-app goes public before or with this repository; this repository depends on its Git tag
  `v0.5.0`, with a local override for development (C2).
- Q4: `main` and `dev` are published, after the owner merges `dev` into `main`.
- Q5: milestone 2 may run `git ls-remote origin`. If uv has no built-in dependency audit, the tool is asked for
  again with its name and source.

The questions as asked:

- Q1. Options A and D: an icon drawn by code (A1) with `--icon` for your own image (A3); keep `CLAUDE.md` and
  `docs/working/` public, add `SECURITY.md`, no contribution guide, no CI (D). Fine (recommended)?
- Q2. The icon's picture: choose after seeing the three candidates of milestone 1 (recommended), or decide one now
  (B1 spectrum and caption, B2 waveform and tap marks, B3 caption only)?
- Q3. audio-spectrum-app: will it go public before or with this repository? If yes, depend on its tag `v0.5.0` (C2,
  recommended); if not, keep the path dependency (C1) and say in the README that the quick start needs it.
- Q4. Which refs go public: `main` and `dev` (recommended, after `dev` is merged into `main` by you), or `main` only?
- Q5. May milestone 2 run `git ls-remote origin` (read-only, over your SSH key), and use a dependency audit tool if
  uv has none built in (asked again with its name and source)?
