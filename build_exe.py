#!/usr/bin/env python3
# f34havok - Havok packfile / FO4 animation helper for the Fallout 34 converter.
# Copyright (C) 2026 Cobalt Mods. GPL-3.0-or-later (see LICENSE).
r"""Build f34havok.exe (a Nuitka standalone folder, no Python needed on the target PC).

    python -m venv .buildenv310                # Python 3.10: the vendored code's float sums differ on 3.12+ (README)
    .buildenv310\Scripts\python -m pip install nuitka numpy==2.2.6   # once; Visual Studio 2022 C++ build tools for the compiler
    .buildenv310\Scripts\python build_exe.py   # -> dist\f34havok\f34havok.exe  (+ runtime DLLs next to it)

The whole dist\f34havok folder is the program; copy it as it is (the Fallout 34 installer ships it under
thirdparty\f34havok together with LICENSE and the link to this source)."""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
DIST = os.path.join(HERE, "dist", "f34havok")


def main():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(BUILD, exist_ok=True)
    cmd = [sys.executable, "-m", "nuitka", "--standalone", "--assume-yes-for-downloads", f"--output-dir={BUILD}",
           "--output-filename=f34havok.exe", "--windows-console-mode=force", "--msvc=latest", "--lto=no",
           "--include-package=f34havok", "--nofollow-import-to=tests", "--nofollow-import-to=pytest",
           "--nofollow-import-to=numpy.tests", "--noinclude-unittest-mode=nofollow",
           "--noinclude-setuptools-mode=nofollow", "--noinclude-pytest-mode=nofollow",
           "--company-name=Cobalt Mods", "--product-name=f34havok", "--file-description=f34havok (GPL-3.0)",
           "--file-version=1.0.0.0", "--product-version=1.0.0.0", "--copyright=GPL-3.0-or-later, Cobalt Mods",
           os.path.join(HERE, "launcher.py")]
    # Nuitka's caches stay inside the build folder (not in %LOCALAPPDATA%)
    env = dict(os.environ, NUITKA_CACHE_DIR=os.path.join(BUILD, "nuitka_cache"))
    r = subprocess.run(cmd, cwd=BUILD, env=env)
    out = os.path.join(BUILD, "launcher.dist")
    if r.returncode or not os.path.exists(os.path.join(out, "f34havok.exe")):
        sys.exit(f"nuitka failed (exit {r.returncode})")
    os.makedirs(os.path.dirname(DIST), exist_ok=True)
    shutil.copytree(out, DIST)
    for f in ("LICENSE", "README.md"):
        shutil.copy(os.path.join(HERE, f), DIST)
    print("built", os.path.join(DIST, "f34havok.exe"))


if __name__ == "__main__":
    main()
