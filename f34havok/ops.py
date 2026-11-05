# f34havok - Havok packfile / FO4 animation helper for the Fallout 34 converter.
# Copyright (C) 2026 Cobalt Mods. GPL-3.0-or-later (see LICENSE).
# Uses PyNifly (GPL-3.0, BadDogSkyrim) - see vendor/ and README.md.
"""The operations f34havok offers (name -> function). Every one is a thin call into PyNifly's code in vendor/:
the converter sends the same arguments it used to pass in-process and gets the same result back."""
from __future__ import annotations
import dataclasses
import sys
import os
import tempfile

from .vendor.pyn import bhk_autopack as AP
from .vendor.pyn import bhk_autounpack as AU
from .vendor.hkx import anim_fo4 as H

VERSION = "1.0.0"

CLASSES = {
    "PhysicsProps": AU.PhysicsProps, "CollisionShape": AU.CollisionShape, "BodyTransform": AU.BodyTransform,
    "SectionHdr": AU.SectionHdr,
    "AnimationData": H.AnimationData, "TrackData": H.TrackData, "Annotation": H.Annotation,
    "BonePose": H.BonePose, "Skeleton": H.Skeleton,
}
_BY_TYPE = {cls: name for name, cls in CLASSES.items()}


def record_fields(obj):
    name = _BY_TYPE.get(type(obj))
    if name is None:
        return None
    f = {fl.name: getattr(obj, fl.name) for fl in dataclasses.fields(obj)}
    f.update({k: v for k, v in vars(obj).items() if k not in f})     # extra attributes (e.g. anim.ref_samples)
    return name, f


def make_record(name, fields):
    cls = CLASSES[name]
    names = {fl.name for fl in dataclasses.fields(cls)}
    obj = cls(**{k: v for k, v in fields.items() if k in names})
    for k, v in fields.items():
        if k not in names:
            setattr(obj, k, v)
    return obj


def schema():
    """Field names + defaults of every record class (the caller's stand-in objects use these)."""
    out = {}
    for name, cls in CLASSES.items():
        fl = []
        for f in dataclasses.fields(cls):
            if f.default is not dataclasses.MISSING:
                fl.append([f.name, "value", f.default])
            elif f.default_factory is not dataclasses.MISSING:          # type: ignore[misc]
                fl.append([f.name, "factory", f.default_factory()])
            else:
                fl.append([f.name, "required", None])
        out[name] = fl
    return out


def _pack_convex_polytope(verts, faces, physics=None, transform=None, shape_bytes=None):
    """pack_convex_polytope; shape_bytes = the caller's own hknpConvexPolytopeShape object bytes instead of
    PyNifly's (the converter writes the vanilla FO4 layout)."""
    if shape_bytes is None:
        return AP.pack_convex_polytope(verts, faces, physics=physics, transform=transform)
    old = AP._build_convex_polytope_shape
    AP._build_convex_polytope_shape = lambda v, f: shape_bytes
    try:
        return AP.pack_convex_polytope(verts, faces, physics=physics, transform=transform)
    finally:
        AP._build_convex_polytope_shape = old


def _anim_write(anim):
    fd, p = tempfile.mkstemp(suffix=".hkx")
    os.close(fd)
    try:
        H.write_fo4_animation(p, anim)
        with open(p, "rb") as f:
            return f.read()
    finally:
        os.remove(p)


def _anim_load(data):
    fd, p = tempfile.mkstemp(suffix=".hkx")
    os.close(fd)
    try:
        with open(p, "wb") as f:
            f.write(data)
        return H.load_fo4_animation(p)
    finally:
        os.remove(p)


OPS = {
    "version": lambda: VERSION,
    "python": lambda: f"{sys.version_info[0]}.{sys.version_info[1]}",      # float sums differ from 3.12 on (README)
    "schema": schema,
    "consts": lambda: {"DYN_INERTIA_TEMPLATE": AP._DYN_INERTIA_TEMPLATE, "CONVEX_HDR": AP._CONVEX_HDR,
                       "MOTION_ID_STATIC": AU.MOTION_ID_STATIC},
    # bhk_autopack (write)
    "matrix_to_quat": AP._matrix_to_quat,
    "split_cm_sections": AP._split_cm_sections,
    "quantize_section": AP._quantize_section,
    "pack_compressed_mesh": AP.pack_compressed_mesh,
    "pack_multi_cm": AP.pack_multi_cm,
    "pack_convex_polytope": _pack_convex_polytope,
    "build_dyn_motion": AP._build_dyn_motion,
    # bhk_autounpack (read)
    "parse_section_headers": AU.parse_section_headers,
    "parse_virtual_fixups": AU.parse_virtual_fixups,
    "parse_local_fixups": AU.parse_local_fixups,
    "parse_global_fixups": AU.parse_global_fixups,
    "parse_bytes": AU.parse_bytes,
    "parse_physics_props": AU.parse_physics_props,
    "extract_bhk_physics_system": AU.extract_bhk_physics_system,
    # FO4 animation (hkaSplineCompressedAnimation)
    "anim_write": _anim_write,
    "anim_parse": H._parse_animation_hkx,
    "anim_load": _anim_load,
}


def call(op, args, kwargs):
    return OPS[op](*args, **kwargs)
