"""Build a distributable executable with PyInstaller."""

import subprocess
import sys


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--name=Anitrack",
        "--hidden-import=PyQt6.sip",
        "--collect-all=qfluentwidgets",
        "--noconfirm",
        "--clean",
        "main.py",
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
