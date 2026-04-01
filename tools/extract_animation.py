"""Extract complete animation data from VLibras AssetBundle to JSON.

Reads Unity AssetBundle via UnityPy and outputs a JSON file with
ALL keyframes preserved (no simplification or truncation).

Enhancements over the original extract_casa.py:
  --tangents    Include tangent data (inSlope, outSlope, weights)
  --prebake     Sample curves at uniform intervals (eliminates Hermite in browser)
  --fps N       Frames per second for pre-bake (default 30)
  --batch       Process all files in a directory
  --compact     No JSON indentation for smaller files
  --bounds      Include animation bounds data

Usage:
    python extract_animation.py CASA                          # same as original
    python extract_animation.py CASA --tangents               # with tangent data
    python extract_animation.py CASA --prebake --fps 60       # pre-baked at 60fps
    python extract_animation.py assets/ --batch               # batch directory
    python extract_animation.py CASA --compact -o output.json # compact output
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

try:
    import UnityPy
except ImportError:
    print("UnityPy required: pip install UnityPy")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Quaternion / Vector math for pre-bake interpolation
# ---------------------------------------------------------------------------

def _quat_dot(a: list[float], b: list[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]


def _quat_slerp(a: list[float], b: list[float], t: float) -> list[float]:
    """Spherical linear interpolation between two quaternions."""
    dot = _quat_dot(a, b)

    # Ensure shortest path
    if dot < 0.0:
        b = [-c for c in b]
        dot = -dot

    dot = min(dot, 1.0)

    # For very close quaternions, fall back to linear interpolation
    if dot > 0.9995:
        result = [a[i] + t * (b[i] - a[i]) for i in range(4)]
        mag = math.sqrt(sum(c * c for c in result))
        if mag > 0.0:
            return [c / mag for c in result]
        return list(a)

    theta_0 = math.acos(dot)
    theta = theta_0 * t
    sin_theta = math.sin(theta)
    sin_theta_0 = math.sin(theta_0)

    s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
    s1 = sin_theta / sin_theta_0

    return [s0 * a[i] + s1 * b[i] for i in range(4)]


def _lerp_vec(a: list[float], b: list[float], t: float) -> list[float]:
    """Linear interpolation between two vectors of equal length."""
    return [a[i] + t * (b[i] - a[i]) for i in range(len(a))]


def _lerp_scalar(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


# ---------------------------------------------------------------------------
# Keyframe sampling for pre-bake
# ---------------------------------------------------------------------------

def _find_segment(keyframes: list[dict], time: float) -> tuple[int, int, float]:
    """Find the two keyframes surrounding `time` and the local t parameter."""
    if time <= keyframes[0]["time"]:
        return 0, 0, 0.0
    if time >= keyframes[-1]["time"]:
        last = len(keyframes) - 1
        return last, last, 0.0

    for i in range(len(keyframes) - 1):
        t0 = keyframes[i]["time"]
        t1 = keyframes[i + 1]["time"]
        if t0 <= time <= t1:
            dt = t1 - t0
            local_t = (time - t0) / dt if dt > 0 else 0.0
            return i, i + 1, local_t

    last = len(keyframes) - 1
    return last, last, 0.0


def _prebake_rotation_curve(
    curve: dict, duration: float, fps: int
) -> dict:
    """Sample a rotation curve at uniform intervals using SLERP."""
    keyframes = curve["keyframes"]
    if not keyframes:
        return curve

    num_samples = max(int(duration * fps) + 1, 2)
    samples = []

    for i in range(num_samples):
        time = (i / (num_samples - 1)) * duration
        idx_a, idx_b, t = _find_segment(keyframes, time)
        val_a = keyframes[idx_a]["value"]
        val_b = keyframes[idx_b]["value"]
        value = _quat_slerp(val_a, val_b, t)
        samples.append({"time": round(time, 6), "value": value})

    return {
        "path": curve["path"],
        "keyframe_count": len(samples),
        "keyframes": samples,
    }


def _prebake_vector_curve(
    curve: dict, duration: float, fps: int
) -> dict:
    """Sample a position/scale curve at uniform intervals using LERP."""
    keyframes = curve["keyframes"]
    if not keyframes:
        return curve

    num_samples = max(int(duration * fps) + 1, 2)
    samples = []

    for i in range(num_samples):
        time = (i / (num_samples - 1)) * duration
        idx_a, idx_b, t = _find_segment(keyframes, time)
        val_a = keyframes[idx_a]["value"]
        val_b = keyframes[idx_b]["value"]
        value = _lerp_vec(val_a, val_b, t)
        samples.append({"time": round(time, 6), "value": value})

    return {
        "path": curve["path"],
        "keyframe_count": len(samples),
        "keyframes": samples,
    }


def _prebake_float_curve(
    curve: dict, duration: float, fps: int
) -> dict:
    """Sample a float curve at uniform intervals using LERP."""
    keyframes = curve["keyframes"]
    if not keyframes:
        return curve

    num_samples = max(int(duration * fps) + 1, 2)
    samples = []

    for i in range(num_samples):
        time = (i / (num_samples - 1)) * duration
        idx_a, idx_b, t = _find_segment(keyframes, time)
        val_a = keyframes[idx_a]["value"]
        val_b = keyframes[idx_b]["value"]
        value = _lerp_scalar(val_a, val_b, t)
        samples.append({"time": round(time, 6), "value": round(value, 6)})

    result = {
        "path": curve["path"],
        "attribute": curve["attribute"],
        "keyframe_count": len(samples),
        "keyframes": samples,
    }
    return result


# ---------------------------------------------------------------------------
# Tangent extraction helpers
# ---------------------------------------------------------------------------

def _extract_quaternion_tangent(slope) -> list[float]:
    """Extract 4-component tangent from a Quaternion slope value."""
    return [slope.x, slope.y, slope.z, slope.w]


def _extract_vector3_tangent(slope) -> list[float]:
    """Extract 3-component tangent from a Vector3 slope value."""
    return [slope.x, slope.y, slope.z]


# ---------------------------------------------------------------------------
# Duration computation
# ---------------------------------------------------------------------------

def _compute_duration(*curve_lists: list[dict]) -> float:
    """Compute the maximum keyframe time across all curve lists."""
    max_time = 0.0
    for curves in curve_lists:
        for curve in curves:
            for kf in curve["keyframes"]:
                if kf["time"] > max_time:
                    max_time = kf["time"]
    return max_time


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def extract(
    bundle_path: str | Path,
    output_path: str | Path | None = None,
    *,
    include_tangents: bool = False,
    prebake: bool = False,
    fps: int = 30,
    compact: bool = False,
    include_bounds: bool = False,
) -> Path:
    """Extract animation data from a Unity AssetBundle file.

    Args:
        bundle_path: Path to the AssetBundle file.
        output_path: Optional output JSON path. Defaults to <name>_full.json.
        include_tangents: If True, include slope/weight tangent data per keyframe.
        prebake: If True, resample all curves at uniform time intervals.
        fps: Frames per second for pre-bake sampling.
        compact: If True, write JSON without indentation.
        include_bounds: If True, include animation bounds data.

    Returns:
        The Path to the written JSON file.
    """
    bundle_path = Path(bundle_path)
    if output_path is None:
        output_path = bundle_path.parent / f"{bundle_path.name}_full.json"
    else:
        output_path = Path(output_path)

    env = UnityPy.load(str(bundle_path))

    clip = None
    for obj in env.objects:
        if obj.type.name == "AnimationClip":
            clip = obj.read()
            break

    if clip is None:
        print(f"Error: No AnimationClip found in {bundle_path}")
        return output_path

    # ------------------------------------------------------------------
    # Collect bone paths from all curve types
    # ------------------------------------------------------------------
    bone_paths: list[str] = []
    seen: set[str] = set()

    def add_path(p: str) -> None:
        if p not in seen:
            bone_paths.append(p)
            seen.add(p)

    for rc in clip.m_RotationCurves:
        add_path(rc.path)
    for pc in clip.m_PositionCurves:
        add_path(pc.path)

    # ------------------------------------------------------------------
    # Rotation curves
    # ------------------------------------------------------------------
    rotation_curves: list[dict[str, Any]] = []
    for rc in clip.m_RotationCurves:
        keyframes = []
        for kf in rc.curve.m_Curve:
            entry: dict[str, Any] = {
                "time": kf.time,
                "value": [kf.value.x, kf.value.y, kf.value.z, kf.value.w],
            }
            if include_tangents:
                entry["inSlope"] = _extract_quaternion_tangent(kf.inSlope)
                entry["outSlope"] = _extract_quaternion_tangent(kf.outSlope)
                entry["inWeight"] = _extract_quaternion_tangent(kf.inWeight)
                entry["outWeight"] = _extract_quaternion_tangent(kf.outWeight)
                entry["weightedMode"] = kf.weightedMode
            keyframes.append(entry)
        rotation_curves.append({
            "path": rc.path,
            "keyframe_count": len(keyframes),
            "keyframes": keyframes,
        })

    # ------------------------------------------------------------------
    # Position curves
    # ------------------------------------------------------------------
    position_curves: list[dict[str, Any]] = []
    for pc in clip.m_PositionCurves:
        keyframes = []
        for kf in pc.curve.m_Curve:
            entry: dict[str, Any] = {
                "time": kf.time,
                "value": [kf.value.x, kf.value.y, kf.value.z],
            }
            if include_tangents:
                entry["inSlope"] = _extract_vector3_tangent(kf.inSlope)
                entry["outSlope"] = _extract_vector3_tangent(kf.outSlope)
                entry["inWeight"] = _extract_vector3_tangent(kf.inWeight)
                entry["outWeight"] = _extract_vector3_tangent(kf.outWeight)
                entry["weightedMode"] = kf.weightedMode
            keyframes.append(entry)
        position_curves.append({
            "path": pc.path,
            "keyframe_count": len(keyframes),
            "keyframes": keyframes,
        })

    # ------------------------------------------------------------------
    # Scale curves
    # ------------------------------------------------------------------
    scale_curves: list[dict[str, Any]] = []
    if hasattr(clip, "m_ScaleCurves"):
        for sc in clip.m_ScaleCurves:
            add_path(sc.path)
            keyframes = []
            for kf in sc.curve.m_Curve:
                entry: dict[str, Any] = {
                    "time": kf.time,
                    "value": [kf.value.x, kf.value.y, kf.value.z],
                }
                if include_tangents:
                    entry["inSlope"] = _extract_vector3_tangent(kf.inSlope)
                    entry["outSlope"] = _extract_vector3_tangent(kf.outSlope)
                    entry["inWeight"] = _extract_vector3_tangent(kf.inWeight)
                    entry["outWeight"] = _extract_vector3_tangent(kf.outWeight)
                    entry["weightedMode"] = kf.weightedMode
                keyframes.append(entry)
            scale_curves.append({
                "path": sc.path,
                "keyframe_count": len(keyframes),
                "keyframes": keyframes,
            })

    # ------------------------------------------------------------------
    # Float curves (blendshapes)
    # ------------------------------------------------------------------
    float_curves: list[dict[str, Any]] = []
    for fc in clip.m_FloatCurves:
        keyframes = []
        for kf in fc.curve.m_Curve:
            entry: dict[str, Any] = {
                "time": kf.time,
                "value": kf.value,
            }
            if include_tangents:
                entry["inSlope"] = kf.inSlope
                entry["outSlope"] = kf.outSlope
                entry["inWeight"] = kf.inWeight
                entry["outWeight"] = kf.outWeight
                entry["weightedMode"] = kf.weightedMode
            keyframes.append(entry)
        float_curves.append({
            "path": fc.path,
            "attribute": fc.attribute,
            "keyframe_count": len(keyframes),
            "keyframes": keyframes,
        })

    # ------------------------------------------------------------------
    # Duration
    # ------------------------------------------------------------------
    duration = _compute_duration(
        rotation_curves, position_curves, scale_curves, float_curves
    )

    # ------------------------------------------------------------------
    # Pre-bake (resample at uniform intervals)
    # ------------------------------------------------------------------
    if prebake and duration > 0:
        rotation_curves = [
            _prebake_rotation_curve(c, duration, fps) for c in rotation_curves
        ]
        position_curves = [
            _prebake_vector_curve(c, duration, fps) for c in position_curves
        ]
        scale_curves = [
            _prebake_vector_curve(c, duration, fps) for c in scale_curves
        ]
        float_curves = [
            _prebake_float_curve(c, duration, fps) for c in float_curves
        ]

    # ------------------------------------------------------------------
    # Assemble output
    # ------------------------------------------------------------------
    data: dict[str, Any] = {
        "name": clip.m_Name,
        "duration": duration,
        "sample_rate": clip.m_SampleRate,
        "legacy": getattr(clip, "m_Legacy", False),
        "bone_paths": bone_paths,
        "rotation_curves": rotation_curves,
        "position_curves": position_curves,
        "scale_curves": scale_curves,
        "float_curves": float_curves,
    }

    if prebake:
        data["prebaked"] = True
        data["prebake_fps"] = fps

    # ------------------------------------------------------------------
    # Bounds extraction
    # ------------------------------------------------------------------
    if include_bounds:
        bounds_data: dict[str, Any] = {}
        if hasattr(clip, "m_Bounds"):
            b = clip.m_Bounds
            if hasattr(b, "m_Center"):
                center = b.m_Center
                bounds_data["center"] = [center.x, center.y, center.z]
            if hasattr(b, "m_Extent"):
                extent = b.m_Extent
                bounds_data["extent"] = [extent.x, extent.y, extent.z]
        data["bounds"] = bounds_data

    # ------------------------------------------------------------------
    # Write JSON
    # ------------------------------------------------------------------
    indent = None if compact else 2
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    rot_kfs = sum(len(rc["keyframes"]) for rc in rotation_curves)
    pos_kfs = sum(len(pc["keyframes"]) for pc in position_curves)
    sc_kfs = sum(len(sc_["keyframes"]) for sc_ in scale_curves)
    fl_kfs = sum(len(fc_["keyframes"]) for fc_ in float_curves)
    animated_rot = sum(
        1 for rc in rotation_curves if len(rc["keyframes"]) > 2
    )

    print(f"Extracted: {bundle_path.name} -> {output_path.name}")
    print(f"  Clip: {clip.m_Name}, {clip.m_SampleRate} fps")
    print(f"  Duration: {duration:.4f}s")
    print(f"  Bones: {len(bone_paths)}")
    print(
        f"  Rotation: {len(rotation_curves)} curves, "
        f"{rot_kfs} keyframes ({animated_rot} animated)"
    )
    print(f"  Position: {len(position_curves)} curves, {pos_kfs} keyframes")
    print(f"  Scale:    {len(scale_curves)} curves, {sc_kfs} keyframes")
    print(f"  Float:    {len(float_curves)} curves, {fl_kfs} keyframes")
    if prebake:
        print(f"  Pre-baked at {fps} fps ({int(duration * fps) + 1} samples)")
    if include_tangents:
        print("  Tangent data: included")
    if include_bounds:
        print(f"  Bounds: {data.get('bounds', {})}")

    return output_path


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def extract_batch(
    directory: str | Path,
    *,
    include_tangents: bool = False,
    prebake: bool = False,
    fps: int = 30,
    compact: bool = False,
    include_bounds: bool = False,
) -> list[Path]:
    """Process all files in a directory as AssetBundles.

    Skips files that end with common non-bundle extensions and files
    that fail to load. Outputs one JSON per successfully processed file.

    Returns:
        List of output file paths.
    """
    directory = Path(directory)
    if not directory.is_dir():
        print(f"Error: {directory} is not a directory")
        sys.exit(1)

    skip_extensions = {
        ".json", ".txt", ".md", ".py", ".log", ".csv",
        ".png", ".jpg", ".jpeg", ".gif", ".bmp",
        ".meta", ".manifest",
    }

    results: list[Path] = []
    files = sorted(directory.iterdir())
    total = 0
    success = 0
    skipped = 0

    for fpath in files:
        if not fpath.is_file():
            continue
        if fpath.suffix.lower() in skip_extensions:
            continue

        total += 1
        try:
            out = extract(
                fpath,
                include_tangents=include_tangents,
                prebake=prebake,
                fps=fps,
                compact=compact,
                include_bounds=include_bounds,
            )
            results.append(out)
            success += 1
        except Exception as exc:
            print(f"  SKIP {fpath.name}: {exc}")
            skipped += 1

    print(f"\nBatch complete: {success}/{total} extracted, {skipped} skipped")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract VLibras AssetBundle animation to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python extract_animation.py CASA\n"
            "  python extract_animation.py CASA --tangents\n"
            "  python extract_animation.py CASA --prebake --fps 60\n"
            "  python extract_animation.py assets/ --batch --compact\n"
        ),
    )
    parser.add_argument("input", help="AssetBundle file or directory (with --batch)")
    parser.add_argument("-o", "--output", help="Output JSON path (single-file mode)")
    parser.add_argument(
        "--tangents",
        action="store_true",
        help="Include tangent data (inSlope, outSlope, weights) per keyframe",
    )
    parser.add_argument(
        "--prebake",
        action="store_true",
        help="Resample curves at uniform time intervals",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Frames per second for --prebake (default: 30)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all files in a directory",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Write JSON without indentation for smaller files",
    )
    parser.add_argument(
        "--bounds",
        action="store_true",
        help="Include animation bounds data (center, extent)",
    )

    args = parser.parse_args()

    if args.batch:
        extract_batch(
            args.input,
            include_tangents=args.tangents,
            prebake=args.prebake,
            fps=args.fps,
            compact=args.compact,
            include_bounds=args.bounds,
        )
    else:
        extract(
            args.input,
            args.output,
            include_tangents=args.tangents,
            prebake=args.prebake,
            fps=args.fps,
            compact=args.compact,
            include_bounds=args.bounds,
        )


if __name__ == "__main__":
    main()
