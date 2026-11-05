# f34havok - Havok packfile / FO4 animation helper for the Fallout 34 converter.
# Copyright (C) 2026 Cobalt Mods. GPL-3.0-or-later (see LICENSE).
"""Entry point of the compiled program (f34havok.exe): the same as `python -m f34havok`."""
import sys

from f34havok.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
