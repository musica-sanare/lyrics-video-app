English | [日本語](../ja/README.md) · [Repository README](../../README.md)

# lyrics-video-app documentation

Every doc of lyrics-video-app, the offline lyrics video maker, with one line on each. To time a song and render its
video, start with the [User guide](USER_GUIDE.md). To work on the code, start with
[Development](DEVELOPMENT.md). The working docs record decisions and each phase.

## Guides

| Document | Description |
|---|---|
| [User guide](USER_GUIDE.md) | Setup, everyday use from the Dock (new songs, the next song), timing the captions on the page, stills with `still`, rendering the whole video with `render` or from the page, designs, the song file. |
| [Development](DEVELOPMENT.md) | Setup, tests, conventions and the rules that keep the repository safe to publish. |
| [Architecture](ARCHITECTURE.md) | The layers, the way from a song file to a still and a video, the sync page, rules every change keeps, performance and where new features fit. |

## Working docs (English only)

| Document | Description |
|---|---|
| [Handoff](../working/HANDOFF.md) | Why this repository exists, the owner's answers, decisions and proposed phases. |
| [Decisions](../working/DECISIONS.md) | Architecture decision log (ADRs). |
| [Phase 0 plan](../working/PHASE0_PLAN.md) | Repository foundation and the caption images as a CLI. |
| [Phase 0 acceptance](../working/PHASE0_ACCEPTANCE.md) | Phase 0 acceptance report: criteria, comparison with the old caption images, repository safety, open items. |
| [Phase 1 plan](../working/PHASE1_PLAN.md) | The design of a lyrics video as configurable parts: frame model, backdrop, designs to compare, `still` command. |
| [Phase 1 acceptance](../working/PHASE1_ACCEPTANCE.md) | Phase 1 acceptance report: the owner's choice of design, criteria, measured backdrop time, repository safety, open items. |
| [Phase 2 plan](../working/PHASE2_PLAN.md) | Timing of the lyrics: an LRC file, a tapping and adjusting page, captions by time with lead and crossfades, the architecture document. |
| [Phase 2 acceptance](../working/PHASE2_ACCEPTANCE.md) | Phase 2 acceptance report: the owner's choice of transition, criteria, measured backdrop time, repository safety, open items. |
| [Phase 3 plan](../working/PHASE3_PLAN.md) | The whole lyrics video in one step: a `render` command on audio-spectrum-app's `render_video`, rendering from the `sync` page, the removal of the caption image commands. |
| [Phase 3 acceptance](../working/PHASE3_ACCEPTANCE.md) | Phase 3 acceptance report: the owner's first whole video, criteria, measured render times, repository safety, open items. |
| [Phase 4 plan](../working/PHASE4_PLAN.md) | A preview of the video and design settings on the `sync` page: a low-resolution preview video, bold, italic and a title box, a Design mode that saves to the song file. |
| [Phase 4 acceptance](../working/PHASE4_ACCEPTANCE.md) | Phase 4 acceptance report: the owner's check, criteria, measured preview and still times, repository safety, open items. |
| [Phase 5 plan](../working/PHASE5_PLAN.md) | Spectrum settings on the `sync` page and named designs: the spectrum as part of the design, a chosen set of spectrum settings, designs saved by name in a user folder. |
| [Phase 5 acceptance](../working/PHASE5_ACCEPTANCE.md) | Phase 5 acceptance report: the owner's check, criteria, measured still times, repository safety, open items. |
| [Phase 6 plan](../working/PHASE6_PLAN.md) | Everyday use: starting the app from the Dock, a start page with recent songs, new songs from files in any folder, song settings on the page. |
| [Phase 6 acceptance](../working/PHASE6_ACCEPTANCE.md) | Phase 6 acceptance report: the owner's check and its two fixes, criteria, measured start times, repository safety, open items. |
| [Phase 7 plan](../working/PHASE7_PLAN.md) | An app icon drawn by code and preparing the repository to go public: the icon, the public release checklist, audio-spectrum-app by tag, `SECURITY.md`. |
