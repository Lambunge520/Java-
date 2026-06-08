Bundled tray dependencies for LJM.

The application loads the matching platform directory at startup:

- windows-amd64
- windows-arm64
- windows-x86
- linux-x86_64
- linux-aarch64
- macos-x86_64
- macos-arm64

These folders contain Python 3.14 wheels extracted for direct import.
If a dependency is missing on the current platform, LJM will try to install it into the matching platform directory automatically with pip.
Linux i686 was not bundled because Pillow does not currently provide a Python 3.14 manylinux i686 wheel.
