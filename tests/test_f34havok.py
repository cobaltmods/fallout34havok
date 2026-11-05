# f34havok - tests. Copyright (C) 2026 Cobalt Mods. GPL-3.0-or-later (see LICENSE).
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from f34havok import ops, protocol                       # noqa: E402


def _roundtrip(v):
    wire = protocol.dumps(protocol.encode(v, ops.record_fields))
    return protocol.decode(json.loads(wire), ops.make_record)


def test_protocol_exact_values():
    v = {"a": (1, 2.5, float("inf")), "b": [b"\x00\xff", bytearray(b"xy")], (1, 2): None, "n": -0.0, "s": "x"}
    got = _roundtrip(v)
    assert got["a"] == (1, 2.5, float("inf")) and got["b"] == [b"\x00\xff", bytearray(b"xy")]
    assert got[(1, 2)] is None and str(got["n"]) == "-0.0"


def test_protocol_vertex_lists_are_packed():
    verts = [(0.1, 0.2, 0.3), (1e-300, 2.0, -3.0)]
    assert _roundtrip(verts) == verts
    assert "$tl" in json.dumps(protocol.encode(verts, ops.record_fields))


def test_numpy_array_is_exact():
    np = pytest.importorskip("numpy")
    a = np.array([[0.1, 0.2], [1 / 3, 2 / 3]], np.float32)
    b = _roundtrip(a)
    assert b.dtype == a.dtype and b.tobytes() == a.tobytes()


def test_pack_box_and_read_back():
    verts, faces = ops.AP._make_box_verts_faces()
    data = ops.call("pack_convex_polytope", [verts, faces], {})
    assert data[:4] == b"\x57\xe0\xe0\x57"                 # hkx packfile magic
    shapes = ops.call("parse_bytes", [data], {})
    assert len(shapes) >= 1


def test_record_roundtrip():
    p = ops.make_record("PhysicsProps", {"is_dynamic": True, "mass": 2.5})
    q = _roundtrip(p)
    assert type(q).__name__ == "PhysicsProps" and q.is_dynamic and q.mass == 2.5


def test_serve_process_answers_in_order():
    verts, faces = ops.AP._make_box_verts_faces()
    reqs = [{"id": 1, "op": "version", "a": [], "k": {"$d": []}},
            {"id": 2, "op": "pack_convex_polytope", "a": protocol.encode([verts, faces], ops.record_fields),
             "k": {"$d": []}},
            {"id": 3, "op": "no_such_op", "a": [], "k": {"$d": []}}]
    p = subprocess.run([sys.executable, os.path.join(ROOT, "f34havok", "__main__.py"), "--serve"],
                       input="\n".join(json.dumps(r) for r in reqs) + "\n", capture_output=True, text=True, timeout=60)
    out = [json.loads(x) for x in p.stdout.splitlines()]
    assert [o["id"] for o in out] == [1, 2, 3]
    assert out[0]["ok"] and out[0]["r"] == ops.VERSION
    assert out[1]["ok"] and out[2]["ok"] is False
