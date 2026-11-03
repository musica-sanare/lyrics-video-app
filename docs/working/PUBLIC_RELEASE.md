[Docs index](../en/README.md)

# Public release checklist

The repository is private. Making it public is the owner's decision and action. Every item below covers all refs that
will be visible on GitHub, not only the current tree. The procedure behind each item is the `claude-shared-rules`
repository's `docs/en/PUBLIC_RELEASE.md`; the decisions are in the [Phase 7 plan](PHASE7_PLAN.md) (Q1 to Q5).

Items marked `要確認` wait for the owner. Results are recorded with their date (all checks so far: 2026-11-01, on
`dev` at `8dd64da`).

## 1. Scope

- [x] `git ls-remote origin` listed (2026-11-01): `refs/heads/main` (`4f5e399`), `refs/heads/dev` (`69efe47`), `HEAD`
  pointing to `main`. No tags, no other branches. The owner decided to publish `main` and `dev` (Q4).
- [x] `refs/pull/*`: none; no pull request was ever opened.
- [ ] Local branches to publish are pushed. Local `dev` is 10 commits ahead of `origin/dev`; `main` is at Phase 2
  (`4f5e399`). Owner step: push `dev`, merge `dev` into `main` and push `main` (Q4). The final scan (section 5) runs
  after that.

## 2. History

- [x] Secret scan over all history (2026-11-01): gitleaks 8.30.1,
  `gitleaks git --log-opts="--all" --redact .`, 49 commits, no leaks found. `gitleaks dir --redact .` over the working
  tree, including the ignored `work/`: no leaks found.
- [x] Every finding reviewed and resolved: there were none.
- [x] Commit identities: author and committer of every commit are `musica-sanare` with its GitHub `noreply` address.
- [x] No AI co-author or "Generated with" lines in any commit message.
- [x] No `.env*`, local settings, build output, or logs ever committed. Files ever committed outside `src/`, `tests/`
  and `docs/`: `.gitignore`, `CLAUDE.md`, `LICENSE`, `README.md`, `README.ja.md`, a removed `README.es.md`,
  `examples/lyrics.example.txt`, `examples/song.example.toml`, `pyproject.toml`, `tools/compare_images.py`,
  `tools/time_backdrop.py`, `uv.lock`. No image, audio, video, font or LRC file was ever committed.
- [x] No local absolute paths under a home folder, no user name, no email address other than the `noreply` one in
  the history.

## 3. Content

- [x] Identifiers: none. The project uses no cloud resources, hosts or accounts. The only names are the GitHub
  account `musica-sanare` and the link to audio-spectrum-app's repository.
- [x] Third-party material:
  - No fonts, songs, lyrics, images or videos are in the tree or the history (`.gitignore` excludes them).
  - macOS system fonts (Hiragino) are named by path in docs, tests and `contact_sheet.py`; the files are not
    distributed.
  - The app icon is drawn by `app_icon.py` from shapes; no image is committed.
  - The example lyrics (`examples/lyrics.example.txt`) and the test texts were written for this repository.
    `要確認`: confirm that none of them is a line of your own songs.
- [x] Internal notes: `CLAUDE.md` and `docs/working/` (plans, acceptance reports, ADRs, `HANDOFF.md`) stay public
  (Q1). They were written for a public repository; a search found no local paths, personal data or song names.
  `CLAUDE.local.md` and `.claude/` are ignored and were never committed.
- [ ] GitHub-side data. `要確認` (owner, on GitHub): there are no pull requests and no workflows; check that the
  repository also has no issues, releases or wiki pages that should not be public.

## 4. Presentation

- [x] `LICENSE`: MIT, chosen by the owner. Runtime dependencies (from `uv.lock`, 2026-11-01) are under permissive
  licenses compatible with MIT: audio-spectrum-app (MIT), FastAPI (MIT), Starlette (BSD-3-Clause), uvicorn
  (BSD-3-Clause), pydantic (MIT), tomlkit (MIT), Pillow (MIT-CMU), NumPy (BSD-3-Clause and others), skia-python
  (BSD), soundfile (BSD-3-Clause). The repository distributes source only, no wheels or binaries. ffmpeg is installed
  by the user and not distributed.
- [x] README quick start (English and Japanese), 2026-11-03: audio-spectrum-app is public and a Git dependency on
  its tag `v0.5.0`. A clone of this repository was made into an empty folder with no audio-spectrum-app next to it,
  an empty uv cache and Git credentials turned off. There `uv sync`, `uv run pytest` (309 passed) and
  `uv run lyrics-video install-app` (into a temporary folder) worked. The README status is updated at the Phase 7
  acceptance.
- [x] `SECURITY.md` added: reports go to GitHub's private vulnerability reporting; it names the local web server and
  the app's files as the parts in scope.
- [x] `CONTRIBUTING.md` and templates: not wanted (Q1).

## 5. Final checks

- [x] Tests on `8dd64da` (2026-11-01): `uv run pytest`, 309 passed. There is no lint configuration and no build step;
  there is no CI (Q1).
- [x] Dependency audit (2026-11-01): `uv audit --frozen` (uv 0.13.5, built in, experimental; it looks up the locked
  versions in the OSV database): no known vulnerabilities in 33 packages.
- [ ] Secret scan and audit repeated on the final commit: at the Phase 7 acceptance, and again after the owner's
  pushes (section 1).
- [ ] Mermaid diagrams changed in Phases 3 to 6 render on GitHub: `要確認` (owner), after the next push. They are in
  `docs/en/ARCHITECTURE.md`, `docs/en/USER_GUIDE.md` and their Japanese twins.

## 6. Switch (owner)

audio-spectrum-app goes public before or together with this repository (Q3), with its own checklist.

1. Push `dev`, merge `dev` into `main`, and push `main`. No branch deploys anything.
2. Check that `git ls-remote origin` shows only `main` and `dev`.
3. **Settings → General → Danger Zone → Change repository visibility → Make public.**

- [ ] Visibility changed to public on: date.

## 7. GitHub settings right after (owner)

Setting names checked against GitHub Docs on 2026-11-01. Everything here is free for a public repository.

1. **Settings → Security and quality → Advanced Security**:
   - **Private vulnerability reporting → Enable** (`SECURITY.md` points to it).
   - **Secret Protection → Enable** if it is not on yet, then **Push protection → Enable**.
   - **Dependabot alerts → Enable** (Python dependencies in `uv.lock`). Leave Dependabot security and version
     updates off: they open pull requests, and there is no CI to check them.
2. **Settings → Rules → Rulesets → New ruleset → New branch ruleset**: name it, set enforcement to **Active**, add
   the target **Include default branch** (and `dev` by name if wanted), and turn on **Restrict deletions** and
   **Block force pushes**. Leave the bypass list empty. No required status checks: there is no CI.
3. **Settings → Actions → General → Actions permissions**: disable actions for this repository (there are no
   workflows), then **Save**.
4. **Settings → General → Features**: turn off Wiki, Projects and Discussions. Issues: off unless you want reports in
   public (security reports go through private vulnerability reporting either way).

- [ ] Private vulnerability reporting.
- [ ] Secret scanning push protection.
- [ ] Dependabot alerts.
- [ ] Ruleset on the default branch: no force push, no deletion.
- [ ] Actions disabled.
- [ ] Unused features turned off.
- [x] Setting names checked against GitHub Docs on: 2026-11-01. The rule names "Restrict deletions" and "Block force
  pushes" and the label of the option that disables Actions were not shown on the pages read; check them on the
  settings page.

## 8. Verification

- [ ] A signed-out browser shows only `main` and `dev` and the expected files.
- [ ] The README quick start works from a clean directory without credentials (after milestone 3 and audio-spectrum-app
  is public).
- [ ] No secret scanning alerts under **Security → Secret scanning**.
- [ ] README status updated.
