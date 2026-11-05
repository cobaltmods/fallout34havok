# f34havok - Havok packfile / FO4 animation helper for the Fallout 34 converter.
# Copyright (C) 2026 Cobalt Mods. GPL-3.0-or-later (see LICENSE).
"""f34havok command line.

    f34havok --serve                     read requests (one JSON line each) on stdin, answer on stdout, until EOF
    f34havok <jobs.jsonl> <out.jsonl>    batch: run every request of a job file, write one response line per job
    f34havok --version

Request / response format: protocol.py (and README.md)."""
from __future__ import annotations
import os
import sys
import traceback

if __package__ in (None, ""):                         # run as a plain script / frozen exe
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "f34havok"

from f34havok import ops, protocol                   # noqa: E402


def handle(line):
    req = protocol.loads(line)
    rid = req.get("id")
    try:
        args = protocol.decode(req.get("a", []), ops.make_record)
        kw = protocol.decode(req.get("k", {"$d": []}), ops.make_record)
        res = ops.call(req["op"], args, kw)
        return protocol.dumps({"id": rid, "ok": True, "r": protocol.encode(res, ops.record_fields)})
    except Exception as e:  # noqa: BLE001
        return protocol.dumps({"id": rid, "ok": False, "err": f"{type(e).__name__}: {e}",
                               "tb": traceback.format_exc()[-2000:]})


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--version"]:
        print(f"f34havok {ops.VERSION} (python {sys.version_info[0]}.{sys.version_info[1]})")
        return 0
    if argv[:1] == ["--serve"]:
        out = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8", newline="\n")
        sys.stdout = sys.stderr                       # anything the vendored code prints must not break the stream
        for line in sys.stdin:
            if line.strip():
                out.write(handle(line) + "\n")
                out.flush()
        return 0
    if len(argv) == 2:
        with open(argv[0], encoding="utf-8") as f, open(argv[1], "w", encoding="utf-8", newline="\n") as o:
            for line in f:
                if line.strip():
                    o.write(handle(line) + "\n")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
