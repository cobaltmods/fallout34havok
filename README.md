# f34havok

A small command-line program that reads and writes **Havok** data for the Fallout 4 engine: collision packfiles
(`bhkPhysicsSystem` / `hknpPhysicsSystemData`, compressed-mesh and convex-polytope shapes) and `hkaSplineCompressedAnimation`
animation files (`.hkx`). 

Licence: **GPL-3.0-or-later** (see `LICENSE`).  Credit to Cobalt for the glue code; the vendored files keep
their own authors (below).  Source for every shipped binary is this repository.

Fallout 34: https://www.nexusmods.com/fallout4/mods/110254

## Credits

| Part | Origin | Licence |
|---|---|---|
| `f34havok/vendor/pyn/bhk_autopack.py`, `bhk_autounpack.py` | [PyNifly](https://github.com/BadDogSkyrim/PyNifly) 29.1.0 (`io_scene_nifly/pyn`) by BadDogSkyrim, **unmodified** | GPL-3.0 |
| `f34havok/vendor/hkx/anim_fo4.py` | PyNifly `hkx/anim_fo4.py` (itself based on Dagobaking's skyrim-fo4-animation-conversion and PredatorCZ's HavokLib), **one marked change**: the writer honours `anim.ref_samples` (root motion) | GPL-3.0 |
| `f34havok/ops.py`, `protocol.py`, `__main__.py`, `launcher.py`, `build_exe.py`, tests | Cobalt  | GPL-3.0-or-later |

## Python version matters

The vendored code is not bit-for-bit the same on every Python: `sum()` of floats is compensated since Python 3.12 (the
mesh sectioning in `bhk_autopack._split_cm_sections` and the animation decompression sum floats), so the same input can give
a different, equally valid result.  The Fallout 34 converter's reference output was made with **Python 3.10**; build and
run f34havok with 3.10 to reproduce it byte for byte (`build_exe.py` is meant to run under a 3.10 virtual environment).

## Build

Needs Python 3.10 (see above) and numpy (only for the array type of the wire format).

    python -m pytest tests                  # tests
    python -m f34havok --version            # run from source
    python -m pip install nuitka            # + Visual Studio 2022 C++ build tools
    python build_exe.py                     # -> dist\f34havok\f34havok.exe (folder is the program, no Python needed)

## Use

    f34havok --serve                         requests (one JSON line each) on stdin, answers on stdout, until EOF
    f34havok <jobs.jsonl> <out.jsonl>        batch: every request of a file, one answer line per request
    f34havok --version

### Job format (one JSON object per line)

    request   {"id": 7, "op": "pack_compressed_mesh", "a": [<args>], "k": {<keyword args>}}
    answer    {"id": 7, "ok": true,  "r": <result>}
              {"id": 7, "ok": false, "err": "ValueError: ...", "tb": "<traceback tail>"}

Values are plain JSON plus tagged objects for what JSON cannot carry **bit-exactly** (so an answer equals the in-process
result byte for byte): floats are `{"$f": "<float.hex()>"}`, bytes `{"$b": "<base64>"}`, bytearray `{"$ba": ..}`, tuples
`{"$t": [..]}`, dicts `{"$d": [[key, value], ..]}`, lists of equally long number tuples (vertices, faces) packed as
`{"$tl": "d"|"q", "n": <width>, "b": "<base64 of little-endian doubles/int64>", "tup": <bool>}`, numpy arrays
`{"$nd": "<dtype>", "s": [shape], "b": "<base64>"}`, record objects `{"$dc": "<Class>", "f": {fields}}`.

### Operations (`op`)

| op | what |
|---|---|
| `version`, `schema`, `consts` | tool version; field names/defaults of the record classes; byte templates (`DYN_INERTIA_TEMPLATE`, `CONVEX_HDR`) |
| `pack_compressed_mesh`, `pack_multi_cm`, `pack_convex_polytope` | triangle mesh / several meshes / convex hull -> Havok packfile bytes (`pack_convex_polytope` takes an optional `shape_bytes` to use the caller's own shape object) |
| `build_dyn_motion`, `split_cm_sections`, `quantize_section`, `matrix_to_quat` | helpers of the packer (motion block, mesh sectioning, vertex quantisation, rotation matrix to quaternion) |
| `parse_bytes`, `parse_section_headers`, `parse_virtual_fixups`, `parse_local_fixups`, `parse_global_fixups`, `extract_bhk_physics_system` | read a packfile (shapes + physics properties / its tables) |
| `anim_write`, `anim_parse`, `anim_load` | `AnimationData` record -> `.hkx` bytes; `.hkx` bytes -> `AnimationData` |
