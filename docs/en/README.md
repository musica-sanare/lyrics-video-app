English | [日本語](../ja/README.md) · [Repository README](../../README.md)

# lyrics-video-app documentation

Every doc of lyrics-video-app, the offline lyrics video maker, with one line on each. To make captions and stills
for a song, start with the [User guide](USER_GUIDE.md). To work on the code, start with
[Development](DEVELOPMENT.md). The working docs record decisions and each phase.

## Guides

| Document | Description |
|---|---|
| [User guide](USER_GUIDE.md) | Setup, the `captions`, `compare` and `still` commands, timing the captions with the `sync` page, rendering the whole video with `render`, designs, the song file, moving from the old lyrics image script. |
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
