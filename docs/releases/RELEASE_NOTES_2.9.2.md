# LJM Java Manager 2.9.2

## Download

- Desktop: choose the Windows, Linux, or macOS package without `nogui`.
- No desktop: choose the package with `nogui`.
- Linux packages include `.run` launchers; macOS desktop uses `.app`, and macOS nogui includes `.command`.

## Changes

- Java downloads now default to mirror-first sources for a smoother China network experience.
- Mirror-first mode keeps official and GitHub direct fallbacks, so overseas links can still be used when mirrors fail.
- Multi-source downloads try the next URL before spending time on slower route fallbacks.
- Download resume files are now isolated per source URL to avoid cross-source partial-file corruption.
