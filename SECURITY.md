# Security policy

Report a security problem privately through GitHub, not in a public issue. This page says how, and which parts of
lyrics-video-app matter most.

## Reporting a vulnerability

1. Open the repository's **Security** tab on GitHub.
2. Choose **Report a vulnerability** and describe the problem, the version or commit, and the steps to reproduce it.

The report stays private between you and the maintainer until a fix is published. This is a personal project, so
there is no fixed response time; reports are answered as soon as possible.

## Supported versions

Only the latest commit on `main` gets fixes.

## What is in scope

lyrics-video-app runs fully offline on the user's own Mac. The parts that face other programs are:

- The local web server of `lyrics-video start` and `lyrics-video sync`. It listens on `127.0.0.1` only, refuses
  requests with a foreign `Host` header, and requires a per-session token for its API.
- The app's files: `server.json` (port and token, readable by the owner only), recent songs and settings in
  `~/Library/Application Support/lyrics-video/`, and the log in `~/Library/Logs/lyrics-video.log`.
- Song files and design files (TOML) and the paths they name, which the app reads and writes.
- The Finder dialogs the server opens with `osascript`.

Out of scope: problems in ffmpeg, uv, Python or the operating system themselves, and attacks that already need full
control of the user's account.
