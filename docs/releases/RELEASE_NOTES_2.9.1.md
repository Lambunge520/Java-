# LJM Java Manager 2.9.1 Hotfix

## Download

- Desktop: choose the Windows, Linux, or macOS package without `nogui`.
- No desktop: choose the package with `nogui`.
- Linux packages include `.run` launchers; macOS desktop uses `.app`, and macOS nogui includes `.command`.

## Fixes

- Fixed legacy JRE 8 detection that could fall back to Java 17.
- Existing standalone JRE updates now request JRE packages.
- Embedded JRE folders inside vendor JDKs, such as Dragonwell 8 `jre/`, now update and register through the parent vendor JDK.
