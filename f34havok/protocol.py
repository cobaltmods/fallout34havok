# f34havok - Havok packfile / FO4 animation helper for the Fallout 34 converter.
# Copyright (C) 2026 Cobalt Mods. GPL-3.0-or-later (see LICENSE).
"""Wire format shared by f34havok and its callers: one JSON object per line.

Request:  {"id": <int>, "op": "<name>", "a": [<args>], "k": {<kwargs>}}
Response: {"id": <int>, "ok": true, "r": <result>}   or   {"id": <int>, "ok": false, "err": "<message>"}

Values are JSON with tagged objects for what JSON can't carry exactly, so a result is bit-identical to calling the
function in-process:
  {"$b": "<base64>"}                     bytes            {"$ba": "<base64>"}  bytearray
  {"$t": [...]}                          tuple            {"$d": [[k, v], ...]} dict (any key type)
  {"$nd": "<dtype>", "s": [...], "b": "<base64>"}         numpy array (exact dtype + shape)
  {"$ns": "<dtype>", "b": "<base64>"}    numpy scalar     {"$f": "<hex>"} non-finite / exact float (float.hex)
  {"$dc": "<ClassName>", "f": {<field>: <value>, ...}}  a record object (dataclass fields + extra attributes)
Floats are always sent as {"$f": float.hex()} so no decimal round trip can change a bit."""
from __future__ import annotations
import base64
import json

_B64 = base64.b64encode
_UNB64 = base64.b64decode


def encode(v, record_fields):
    """record_fields(obj) -> (class name, {attr: value}) for record objects, else None."""
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, int) and not hasattr(v, "dtype"):
        return v
    if isinstance(v, float) and not hasattr(v, "dtype"):
        return {"$f": v.hex()}
    if isinstance(v, bytearray):
        return {"$ba": _B64(bytes(v)).decode()}
    if isinstance(v, bytes):
        return {"$b": _B64(v).decode()}
    if isinstance(v, tuple):
        return _fast(v, True) or {"$t": [encode(x, record_fields) for x in v]}
    if isinstance(v, list):
        return _fast(v, False) or [encode(x, record_fields) for x in v]
    if isinstance(v, dict):
        return {"$d": [[encode(k, record_fields), encode(x, record_fields)] for k, x in v.items()]}
    if hasattr(v, "dtype") and hasattr(v, "shape"):
        import numpy as np
        if isinstance(v, np.ndarray):
            a = np.ascontiguousarray(v)
            if a.dtype == object:
                return {"$ndo": [encode(x, record_fields) for x in a.ravel().tolist()], "s": list(a.shape)}
            return {"$nd": a.dtype.str, "s": list(a.shape), "b": _B64(a.tobytes()).decode()}
        return {"$ns": v.dtype.str, "b": _B64(v.tobytes()).decode()}
    rf = record_fields(v)
    if rf is not None:
        name, fields = rf
        return {"$dc": name, "f": {k: encode(x, record_fields) for k, x in fields.items()}}
    raise TypeError(f"f34havok protocol: can't encode {type(v).__name__}")


def _fast(v, tup):
    """Lists of same-length tuples of plain floats / ints (vertices, faces): one packed array instead of tagged items."""
    if not v or not isinstance(v[0], tuple) or not v[0]:
        return None
    n = len(v[0])
    kind = float if type(v[0][0]) is float else int if type(v[0][0]) is int else None
    if kind is None:
        return None
    for t in v:
        if type(t) is not tuple or len(t) != n:
            return None
        for x in t:
            if type(x) is not kind:
                return None
    import struct
    flat = [x for t in v for x in t]
    if kind is int and any(x < -2 ** 63 or x >= 2 ** 63 for x in flat):
        return None
    b = struct.pack(("<%dd" if kind is float else "<%dq") % len(flat), *flat)
    return {"$tl": "d" if kind is float else "q", "n": n, "b": _B64(b).decode(), "tup": tup}


def decode(v, make_record):
    """make_record(class name, {attr: value}) -> object."""
    if isinstance(v, list):
        return [decode(x, make_record) for x in v]
    if not isinstance(v, dict):
        return v
    if "$tl" in v:
        import struct
        raw = _UNB64(v["b"])
        w = 8
        flat = struct.unpack("<%d%s" % (len(raw) // w, v["$tl"]), raw)
        n = v["n"]
        out = [tuple(flat[i:i + n]) for i in range(0, len(flat), n)]
        return tuple(out) if v["tup"] else out
    if "$f" in v:
        return float.fromhex(v["$f"])
    if "$b" in v:
        return _UNB64(v["$b"])
    if "$ba" in v:
        return bytearray(_UNB64(v["$ba"]))
    if "$t" in v:
        return tuple(decode(x, make_record) for x in v["$t"])
    if "$d" in v:
        return {_hashable(decode(k, make_record)): decode(x, make_record) for k, x in v["$d"]}
    if "$nd" in v:
        import numpy as np
        return np.frombuffer(_UNB64(v["b"]), dtype=np.dtype(v["$nd"])).reshape(v["s"]).copy()
    if "$ndo" in v:
        import numpy as np
        a = np.empty(len(v["$ndo"]), dtype=object)
        a[:] = [decode(x, make_record) for x in v["$ndo"]]
        return a.reshape(v["s"])
    if "$ns" in v:
        import numpy as np
        return np.frombuffer(_UNB64(v["b"]), dtype=np.dtype(v["$ns"]))[0]
    if "$dc" in v:
        return make_record(v["$dc"], {k: decode(x, make_record) for k, x in v["f"].items()})
    raise ValueError(f"f34havok protocol: unknown object {list(v)[:3]}")


def _hashable(k):
    return tuple(_hashable(x) for x in k) if isinstance(k, list) else k


def dumps(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), allow_nan=False)


def loads(line: str):
    return json.loads(line)
