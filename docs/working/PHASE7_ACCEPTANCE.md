[Docs index](../en/README.md)

# Phase 7 acceptance: an app icon and preparing the repository to go public

Status: accepted by the owner on 2026-11-03. Version 0.6.0.

Plan: [PHASE7_PLAN.md](PHASE7_PLAN.md). Machine: Apple M1 (8 cores), Python 3.13, Pillow 13.0.0,
audio-spectrum-app 0.5.0 (tag `v0.5.0`), uv 0.13.5, gitleaks 8.30.1.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `83e12c3`, `7d2d3e1` | Plan; approved with every recommendation (A1 with A3, C2, D, `main` and `dev` published) |
| 1. Icon | `8dd64da` | Three candidates drawn into the ignored `work/icons/`; the owner chose B2. `app_icon.py`, `AppIcon.icns` in the bundle, `install-app --icon` |
| 2. Release checklist | `ad3e310` | [Public release checklist](PUBLIC_RELEASE.md) with the scope, history, content, license and audit results; `SECURITY.md` |
| 3. Dependency and quick start | `6a9f5e5` | audio-spectrum-app by its Git tag `v0.5.0`; development against the sibling with `--with-editable`; the quick start checked from a fresh clone |
| 4. Owner's check | none | The owner installed the app again and answered the checklist's two `要確認` items (section 2) |
| 5. Acceptance | this commit | ADR-014, ADR-015, this report, the final scans, version 0.6.0 |

## 2. The owner's results

- **The icon works.** The owner installed the app again with `--overwrite`, dragged it back to the Dock and reported
  no problem.
- **Nothing private in the examples or on GitHub.** The example lyrics and the test texts contain no line of the
  owner's songs, and the repository has no issues, releases or wiki pages that should stay private.
- **audio-spectrum-app went public first** (Q3), prepared in its own session with its own checklist, and its tag
  `v0.5.0` is on GitHub.

## 3. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Lyrics Video.app shows its own icon in the Dock and Finder | Met | The owner's check (section 2) |
| No image, icon or font file is committed; the icon comes from code or the owner's local image | Met | Commit file lists reviewed; `.gitignore` unchanged for images; the candidates stay in the ignored `work/icons/` |
| `install-app` still works without `iconutil` (default icon, a warning) | Met | `test_without_iconutil_the_app_has_the_default_icon`, `test_without_iconutil_an_icon_image_stops_the_install` |
| Every item of `PUBLIC_RELEASE.md` is done, deferred with a reason, or not applicable, with dates | Met for everything before the switch | The checklist; the remaining items follow the owner's pushes and the switch (section 7) |
| The secret scan covers every ref to be published and finds nothing, also on the final commit | Met locally; repeated after the pushes | gitleaks over all 51 local commits (every ref to be published is local) and the working tree; section 5 |
| The README quick start works from a fresh clone without access to private resources | Met | A clone with no sibling, an empty uv cache and Git credentials off: `uv sync`, 309 tests, `install-app` |
| The owner has numbered steps for the switch and the GitHub settings right after it | Met | Checklist sections 6 and 7 |
| Docs in English and Japanese | Met | Translation hashes match |

Test suite: 309 tests, all passing (296 at the end of Phase 6). The icon was checked by eye at every size of the
icon set; below 128 px the waveform has fewer, wider bars and both marks stay visible at 16 px.

## 4. Measurements

On the 8-core M1, with other work running.

| Step | Time |
|---|---|
| Drawing the ten images of the icon set | 0.16 s |
| `write_icns`: drawing and `iconutil -c icns` (167 KB file) | 0.23 s |
| `uv run lyrics-video install-app --overwrite` | 0.6 s |
| `uv sync` in a fresh clone with an empty cache (all packages downloaded) | 4.4 s |

## 5. Repository safety

- `gitleaks git --log-opts="--all" --redact .` over 51 commits before this commit: no leaks found.
  `gitleaks dir --redact .` over the working tree with this commit's changes, including the ignored `work/`: no leaks
  found.
- The only author and committer is the owner's GitHub `noreply` address; no AI co-author lines; no home paths in the
  history.
- `uv audit --frozen`: no known vulnerabilities in the 33 locked packages.
- The candidates and size sheets of the icon are PNG files in the ignored `work/icons/`; the bundle and its `.icns`
  are made on the owner's Mac and never committed.

## 6. Findings

- **Small icons need their own drawing.** Scaling the 1024 px waveform down to 16 px blurs its bars into a gray
  block; drawing fewer, wider bars below 128 px keeps the picture readable.
- **uv has a dependency audit built in.** `uv audit` (experimental in uv 0.13.5) checks `uv.lock` against the OSV
  database, so no extra tool was needed.
- **A layered editable install keeps the lock clean.** `uv run --with-editable ../audio-spectrum-app` tests against
  the sibling checkout without touching `uv.lock` or the project's environment, so the tag dependency costs nothing
  when both repositories change.
- **The billing guard can stop a plain doc edit.** A shell command that rewrote docs mentioning `uv sync` was blocked
  as a package install; the same edits went through the editor tool. Worth a look in `claude-shared-rules`.

## 7. Open items

- The owner's steps of the [checklist](PUBLIC_RELEASE.md) sections 1, 6 and 7: push `dev`, push `dev` to `main`, check
  the refs, switch the visibility, apply the GitHub settings.
- After the pushes: the secret scan over the refs on GitHub, and a look at the Mermaid diagrams changed in Phases 3
  to 6 on GitHub.
- After the switch: the verification of checklist section 8, recorded in its own commit.
- Carried over: MusicXML draft timing and automatic alignment, line clips, a measured render time with a heavier
  spectrum, only if the owner still wants them.
