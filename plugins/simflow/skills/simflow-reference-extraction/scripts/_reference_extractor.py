#!/usr/bin/env python3
"""Deterministic helpers for the SimFlow reference-extraction Task Skill.

Adapted from the local scientific-reference-extractor v0.3 implementation.
This module handles document/source inspection and deterministic vector/raster
preparation. Semantic choices remain with the host agent.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.helper_evidence import build_helper_evidence, source_file_record
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run

try:  # Optional dependencies are checked by the commands that need them.
    import numpy as np
except ImportError:  # pragma: no cover - exercised with import blocking in tests
    np = None

try:
    import cv2
except ImportError:  # pragma: no cover - exercised with import blocking in tests
    cv2 = None

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - exercised with import blocking in tests
    Image = None
    ImageDraw = None

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - exercised with import blocking in tests
    fitz = None

RAW_EXTS = {
    ".csv", ".dat", ".txt", ".json", ".npy", ".npz", ".h5", ".hdf5",
    ".xlsx", ".xls", ".tsv", ".parquet", ".pkl", ".pickle"
}
NORMALIZABLE_RAW_EXTS = {".csv", ".dat", ".txt", ".json", ".npy", ".npz", ".h5", ".hdf5", ".xlsx", ".tsv"}
SCRIPT_EXTS = {".py", ".ipynb", ".m", ".r", ".R", ".jl", ".gnuplot", ".gp"}
FIG_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".eps", ".svg"}


def require_fitz() -> None:
    if fitz is None:
        raise ValueError(
            "This command requires PyMuPDF. Install the reference-extraction optional dependencies."
        )


def require_numpy() -> None:
    if np is None:
        raise ValueError(
            "This command requires NumPy. Install the reference-extraction optional dependencies."
        )


def require_raster_dependencies() -> None:
    missing = []
    if np is None:
        missing.append("NumPy")
    if cv2 is None:
        missing.append("opencv-python-headless")
    if Image is None or ImageDraw is None:
        missing.append("Pillow")
    if missing:
        raise ValueError(
            "This command requires raster dependencies: " + ", ".join(missing)
        )


def require_pillow() -> None:
    if Image is None or ImageDraw is None:
        raise ValueError(
            "This command requires Pillow. Install the reference-extraction optional dependencies."
        )


def prepare_output_dir(path: Path, *, overwrite: bool, project_root: str | None = None) -> Path:
    """Create a dedicated output directory without silently deleting user data."""
    resolved = path.expanduser().resolve()
    protected = {Path("/").resolve(), Path.home().resolve(), Path.cwd().resolve()}
    if project_root:
        protected.add(Path(project_root).expanduser().resolve())
    if resolved in protected:
        raise ValueError(f"Refusing to use protected directory as extraction output: {resolved}")
    if resolved.exists() and not resolved.is_dir():
        raise ValueError(f"Output path exists and is not a directory: {resolved}")
    if resolved.is_dir() and any(resolved.iterdir()):
        if not overwrite:
            raise ValueError(
                f"Output directory is not empty: {resolved}. Pass --overwrite to replace it."
            )
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def jdump(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_extract_tar(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    with tarfile.open(archive, "r:*") as tf:
        members = tf.getmembers()
        for m in members:
            target = (dest / m.name).resolve()
            if root != target and root not in target.parents:
                raise ValueError(f"Unsafe archive path: {m.name}")
            if m.issym() or m.islnk():
                raise ValueError(f"Archive links are not allowed: {m.name}")
        try:
            tf.extractall(dest, filter="data")
        except TypeError:
            tf.extractall(dest)


def strip_tex_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        out = []
        escaped = False
        for ch in line:
            if ch == "%" and not escaped:
                break
            out.append(ch)
            escaped = (ch == "\\" and not escaped)
            if ch != "\\":
                escaped = False
        lines.append("".join(out))
    return "\n".join(lines)


def balanced_brace_content(text: str, brace_pos: int) -> tuple[str | None, int | None]:
    if brace_pos >= len(text) or text[brace_pos] != "{":
        return None, None
    depth = 0
    start = brace_pos + 1
    escaped = False
    for i in range(brace_pos, len(text)):
        ch = text[i]
        if ch == "\\" and not escaped:
            escaped = True
            continue
        if escaped:
            escaped = False
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
    return None, None


def find_command_arg(text: str, command: str, start: int = 0) -> tuple[str | None, int | None, int | None]:
    m = re.search(r"\\" + re.escape(command) + r"\s*(?:\[[^\]]*\]\s*)?\{", text[start:], flags=re.S)
    if not m:
        return None, None, None
    brace = start + m.end() - 1
    content, end = balanced_brace_content(text, brace)
    return content, start + m.start(), end


def clean_tex_text(s: str | None) -> str | None:
    if s is None:
        return None
    s = re.sub(r"\\(?:textbf|textit|emph|mathrm|mathbf|operatorname)\s*\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\(?:cite|ref|label)\s*\{[^{}]*\}", "", s)
    s = s.replace("~", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def resolve_figure_file(tex_dir: Path, name: str) -> Path | None:
    raw = Path(name.strip())
    candidates = [tex_dir / raw]
    if not raw.suffix:
        candidates += [tex_dir / (str(raw) + ext) for ext in [".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"]]
    for c in candidates:
        if c.exists() and c.is_file():
            return c.resolve()
    return None


def parse_tex_file(tex_path: Path, source_root: Path) -> dict[str, Any]:
    raw = tex_path.read_text(encoding="utf-8", errors="replace")
    text = strip_tex_comments(raw)
    figures: list[dict[str, Any]] = []
    fig_pat = re.compile(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", re.S)
    for n, m in enumerate(fig_pat.finditer(text), 1):
        body = m.group(1)
        includes = []
        for im in re.finditer(r"\\includegraphics\s*(?:\[([^\]]*)\]\s*)?\{([^{}]+)\}", body, re.S):
            name = im.group(2).strip()
            resolved = resolve_figure_file(tex_path.parent, name)
            includes.append({
                "declared": name,
                "options": (im.group(1) or "").strip() or None,
                "resolved": str(resolved.relative_to(source_root)) if resolved and source_root in resolved.parents else (str(resolved) if resolved else None),
            })
        caption, _, _ = find_command_arg(body, "caption")
        label, _, _ = find_command_arg(body, "label")
        figures.append({
            "ordinal_in_tex": n,
            "label": label.strip() if label else None,
            "caption_tex": caption.strip() if caption else None,
            "caption_text": clean_tex_text(caption),
            "includegraphics": includes,
        })

    tables = []
    tab_pat = re.compile(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", re.S)
    for n, m in enumerate(tab_pat.finditer(text), 1):
        body = m.group(1)
        caption, _, _ = find_command_arg(body, "caption")
        label, _, _ = find_command_arg(body, "label")
        tables.append({
            "ordinal_in_tex": n,
            "label": label.strip() if label else None,
            "caption_text": clean_tex_text(caption),
            "latex": body.strip(),
        })

    verbatim_numeric = []
    for n, vm in enumerate(re.finditer(r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}", text, re.S), 1):
        body = vm.group(1).strip()
        nums = re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", body)
        if len(nums) >= 4:
            verbatim_numeric.append({"ordinal_in_tex": n, "number_count": len(nums), "text": body})

    ref_contexts: dict[str, list[str]] = {}
    labels = [f["label"] for f in figures if f.get("label")]
    for lab in labels:
        patt = re.compile(r"(.{0,500}\\(?:ref|autoref)\{" + re.escape(lab) + r"\}.{0,900})", re.S)
        snippets = []
        for rm in patt.finditer(text):
            snip = re.sub(r"\s+", " ", rm.group(1)).strip()
            if snip:
                snippets.append(snip)
        ref_contexts[lab] = snippets[:5]

    return {
        "file": str(tex_path.relative_to(source_root)),
        "figures": figures,
        "tables": tables,
        "numeric_verbatim_blocks": verbatim_numeric,
        "figure_reference_context": ref_contexts,
    }


def inspect_pdf_structure(path: Path) -> dict[str, Any]:
    require_fitz()
    doc = fitz.open(path)
    pages = []
    total_images = total_drawings = 0
    for pno, page in enumerate(doc):
        images = page.get_images(full=True)
        drawings = page.get_drawings()
        total_images += len(images)
        total_drawings += len(drawings)
        image_records = []
        for im in images:
            xref = im[0]
            rects = page.get_image_rects(xref)
            image_records.append({
                "xref": xref,
                "width_px": im[2],
                "height_px": im[3],
                "bpc": im[4],
                "colorspace": im[5],
                "rects": [[float(r.x0), float(r.y0), float(r.x1), float(r.y1)] for r in rects],
            })
        pages.append({
            "page": pno + 1,
            "width_pt": float(page.rect.width),
            "height_pt": float(page.rect.height),
            "image_count": len(images),
            "drawing_count": len(drawings),
            "text_char_count": len(page.get_text("text")),
            "images": image_records,
        })
    kind = "vector"
    if total_images and total_drawings:
        kind = "mixed"
    elif total_images and not total_drawings:
        kind = "raster"
    return {
        "schema_version": "0.3",
        "file": str(path),
        "sha256": file_sha256(path),
        "page_count": len(doc),
        "total_images": total_images,
        "total_drawings": total_drawings,
        "coarse_kind": kind,
        "pages": pages,
    }


def render_pdf_page(pdf: Path, out_png: Path, page_number: int = 1, dpi: int = 180, clip: fitz.Rect | None = None) -> None:
    require_fitz()
    doc = fitz.open(pdf)
    page = doc[page_number - 1]
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False, clip=clip)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    pix.save(out_png)


def line_item(d: dict[str, Any]):
    items = d.get("items", [])
    if len(items) != 1 or items[0][0] != "l":
        return None
    return items[0][1], items[0][2]


def near(a: float, b: float, tol: float = 0.8) -> bool:
    return abs(a - b) <= tol


def blackish(c: Any) -> bool:
    if c is None:
        return False
    return max(c) <= 0.18


def detect_axes(page) -> list[dict[str, Any]]:
    verticals = []
    horizontals = []
    drawings = page.get_drawings()
    for idx, d in enumerate(drawings):
        if not blackish(d.get("color")):
            continue
        li = line_item(d)
        if li is None:
            continue
        p1, p2 = li
        if near(p1.x, p2.x, 0.2) and abs(p2.y - p1.y) >= 30:
            verticals.append((idx, float(p1.x), min(float(p1.y), float(p2.y)), max(float(p1.y), float(p2.y))))
        elif near(p1.y, p2.y, 0.2) and abs(p2.x - p1.x) >= 40:
            horizontals.append((idx, float(p1.y), min(float(p1.x), float(p2.x)), max(float(p1.x), float(p2.x))))

    found = []
    for i, v1 in enumerate(verticals):
        for v2 in verticals[i + 1:]:
            if abs(v1[1] - v2[1]) < 40:
                continue
            if not (near(v1[2], v2[2]) and near(v1[3], v2[3])):
                continue
            x0, x1 = sorted([v1[1], v2[1]])
            y0, y1 = v1[2], v1[3]
            hs = [h for h in horizontals if near(h[1], y0) or near(h[1], y1)]
            top = next((h for h in hs if near(h[1], y0) and near(h[2], x0) and near(h[3], x1)), None)
            bottom = next((h for h in hs if near(h[1], y1) and near(h[2], x0) and near(h[3], x1)), None)
            if not top or not bottom:
                continue
            if x1 - x0 < 50 or y1 - y0 < 30:
                continue
            found.append({
                "rect": [x0, y0, x1, y1],
                "spine_drawing_indices": [v1[0], v2[0], top[0], bottom[0]],
            })
    # de-duplicate close rectangles
    uniq = []
    for f in found:
        r = f["rect"]
        if any(max(abs(a-b) for a,b in zip(r, u["rect"])) < 1.0 for u in uniq):
            continue
        uniq.append(f)
    uniq.sort(key=lambda a: (round(a["rect"][1] / 10), a["rect"][0]))
    return uniq


def rect_overlap_fraction(inner: fitz.Rect, outer: fitz.Rect) -> float:
    inter = inner & outer
    if inter.is_empty or inner.get_area() <= 0:
        return 0.0
    return inter.get_area() / inner.get_area()


def color_hex(c: Any) -> str | None:
    if c is None:
        return None
    vals = [max(0, min(255, round(float(v) * 255))) for v in c]
    return "#" + "".join(f"{v:02x}" for v in vals)


def detect_tick_positions(page, axes_rect: list[float]) -> dict[str, list[float]]:
    ar = fitz.Rect(*axes_rect)
    x_ticks = []
    y_ticks = []
    for d in page.get_drawings():
        if not blackish(d.get("color")):
            continue
        li = line_item(d)
        if li is None:
            continue
        p1, p2 = li
        # x-axis tick: short vertical line attached to bottom spine
        if near(p1.x, p2.x, 0.2) and abs(p2.y-p1.y) <= 8:
            x = float(p1.x)
            ys = [float(p1.y), float(p2.y)]
            if ar.x0 - 1 <= x <= ar.x1 + 1 and min(abs(y-ar.y1) for y in ys) <= 1.2:
                x_ticks.append(x)
        # y-axis tick: short horizontal line attached to left spine
        elif near(p1.y, p2.y, 0.2) and abs(p2.x-p1.x) <= 8:
            y = float(p1.y)
            xs = [float(p1.x), float(p2.x)]
            if ar.y0 - 1 <= y <= ar.y1 + 1 and min(abs(x-ar.x0) for x in xs) <= 1.2:
                y_ticks.append(y)
    def uniq(vals):
        vals = sorted(vals)
        out=[]
        for v in vals:
            if not out or abs(v-out[-1]) > 0.5:
                out.append(v)
        return out
    return {"x_tick_positions_pt": uniq(x_ticks), "y_tick_positions_pt": uniq(y_ticks)}


def candidate_curves(page, axes_rect: list[float]) -> list[dict[str, Any]]:
    ar = fitz.Rect(*axes_rect)
    out = []
    for idx, d in enumerate(page.get_drawings()):
        c = d.get("color")
        if c is None or blackish(c):
            continue
        items = d.get("items", [])
        if len(items) < 3:
            continue
        dr = fitz.Rect(d["rect"])
        # candidate should lie mostly within the axes and span a meaningful range
        if rect_overlap_fraction(dr, ar) < 0.75:
            continue
        if dr.width < ar.width * 0.15 and dr.height < ar.height * 0.15:
            continue
        types = {}
        for it in items:
            types[it[0]] = types.get(it[0], 0) + 1
        out.append({
            "drawing_index": idx,
            "stroke_rgb": [float(v) for v in c],
            "stroke_hex": color_hex(c),
            "line_width_pt": float(d.get("width") or 0),
            "dashes": d.get("dashes"),
            "item_count": len(items),
            "item_types": types,
            "bbox": [float(dr.x0), float(dr.y0), float(dr.x1), float(dr.y1)],
        })
    out.sort(key=lambda x: (-x["item_count"], x["drawing_index"]))
    return out


def page_colored_paths(page) -> list[dict[str, Any]]:
    out=[]
    for idx,d in enumerate(page.get_drawings()):
        c=d.get("color")
        items=d.get("items",[])
        if c is None or blackish(c) or len(items)<3:
            continue
        r=fitz.Rect(d["rect"])
        if r.width < 5 and r.height < 5:
            continue
        out.append({
            "drawing_index": idx,
            "stroke_rgb": [float(v) for v in c],
            "stroke_hex": color_hex(c),
            "line_width_pt": float(d.get("width") or 0),
            "dashes": d.get("dashes"),
            "item_count": len(items),
            "bbox": [float(r.x0),float(r.y0),float(r.x1),float(r.y1)]
        })
    out.sort(key=lambda x:(-x["item_count"],x["drawing_index"]))
    return out



def effective_drawing_color(d: dict[str, Any]) -> Any:
    """Return stroke color when available, otherwise fill color."""
    return d.get("color") if d.get("color") is not None else d.get("fill")


def _drawing_item_signature(d: dict[str, Any]) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for it in d.get("items", []):
        counts[it[0]] = counts.get(it[0], 0) + 1
    return tuple(sorted(counts.items()))


def detect_marker_groups(page, axes_rect: list[float]) -> list[dict[str, Any]]:
    """Group repeated small vector drawings that plausibly represent data markers.

    Matplotlib commonly emits one small drawing per marker.  The grouping is
    intentionally geometry based: it does not infer the scientific series name.
    """
    ar = fitz.Rect(*axes_rect)
    max_w = max(18.0, min(24.0, ar.width * 0.08))
    max_h = max(18.0, min(24.0, ar.height * 0.12))
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for idx, d in enumerate(page.get_drawings()):
        r = fitz.Rect(d["rect"])
        if r.is_empty or r.width < 0.6 or r.height < 0.6:
            continue
        if r.width > max_w or r.height > max_h:
            continue
        cx, cy = (r.x0 + r.x1) / 2.0, (r.y0 + r.y1) / 2.0
        if not (ar.x0 - 0.5 <= cx <= ar.x1 + 0.5 and ar.y0 - 0.5 <= cy <= ar.y1 + 0.5):
            continue
        items = d.get("items", [])
        # Single straight line is normally a tick/cap, not a marker.
        if len(items) == 1 and items[0][0] == "l":
            continue
        c = effective_drawing_color(d)
        if c is None:
            continue
        # Quantize size enough to group repeated markers despite tiny PDF rounding.
        sig = (
            color_hex(c),
            color_hex(d.get("fill")),
            _drawing_item_signature(d),
            round(r.width * 2) / 2.0,
            round(r.height * 2) / 2.0,
        )
        groups.setdefault(sig, []).append({
            "drawing_index": idx,
            "center_pdf_pt": [float(cx), float(cy)],
            "bbox": [float(r.x0), float(r.y0), float(r.x1), float(r.y1)],
        })
    out = []
    for sig, members in groups.items():
        # A scientific marker series should repeat; two symbols are too ambiguous.
        if len(members) < 3:
            continue
        # Suppress near-identical stacked objects at the same location.
        centers = sorted((m["center_pdf_pt"][0], m["center_pdf_pt"][1]) for m in members)
        unique = []
        for c in centers:
            if not unique or abs(c[0]-unique[-1][0]) > 0.25 or abs(c[1]-unique[-1][1]) > 0.25:
                unique.append(c)
        if len(unique) < 3:
            continue
        color, fill, item_sig, width_bin, height_bin = sig
        # If a long same-color path exists, distinguish data markers lying on that
        # path from legend markers that happen to share the same symbol.
        long_paths=[]
        for didx,d in enumerate(page.get_drawings()):
            if color_hex(effective_drawing_color(d)) != color:
                continue
            rr=fitz.Rect(d["rect"]); items=d.get("items",[])
            if len(items) < 3 or (rr.width < ar.width*0.25 and rr.height < ar.height*0.25):
                continue
            if rect_overlap_fraction(rr,ar) < 0.7:
                continue
            long_paths.append((didx,points_from_drawing(d)))
        data_members=members
        assoc=None
        if long_paths:
            def pdist(pt,poly):
                px,py=pt; best=1e30
                for a,b in zip(poly,poly[1:]):
                    ax,ay=float(a.x),float(a.y); bx,by=float(b.x),float(b.y)
                    dx,dy=bx-ax,by-ay; den=dx*dx+dy*dy
                    t=0.0 if den==0 else max(0.0,min(1.0,((px-ax)*dx+(py-ay)*dy)/den))
                    qx,qy=ax+t*dx,ay+t*dy
                    best=min(best,math.hypot(px-qx,py-qy))
                return best
            scored=[]
            tol=max(3.5,max(width_bin,height_bin)*0.8)
            for didx,poly in long_paths:
                near_members=[m for m in members if pdist(m["center_pdf_pt"],poly)<=tol]
                scored.append((len(near_members),didx,near_members))
            scored.sort(reverse=True,key=lambda z:z[0])
            if scored and scored[0][0] >= 3:
                _,assoc,data_members=scored[0]
        out.append({
            "marker_group_index": -1,
            "stroke_or_fill_hex": color,
            "fill_hex": fill,
            "item_signature": list(item_sig),
            "marker_width_pt": width_bin,
            "marker_height_pt": height_bin,
            "marker_count": len(members),
            "drawing_indices": [m["drawing_index"] for m in members],
            "centers_pdf_pt": [m["center_pdf_pt"] for m in members],
            "associated_curve_drawing_index": assoc,
            "data_marker_count": len(data_members),
            "data_drawing_indices": [m["drawing_index"] for m in data_members],
            "data_centers_pdf_pt": [m["center_pdf_pt"] for m in data_members],
        })
    out.sort(key=lambda g: (-g["marker_count"], g["stroke_or_fill_hex"] or "", g["marker_width_pt"]))
    for i, g in enumerate(out):
        g["marker_group_index"] = i
    return out


def candidate_vertical_errorbars(page, axes_rect: list[float]) -> list[dict[str, Any]]:
    """Return single vertical colored line segments that may encode y error bars."""
    ar = fitz.Rect(*axes_rect)
    out=[]
    for idx,d in enumerate(page.get_drawings()):
        li=line_item(d)
        if li is None:
            continue
        p1,p2=li
        if not near(p1.x,p2.x,0.25):
            continue
        length=abs(float(p2.y)-float(p1.y))
        if length < 2.0 or length > ar.height * 0.8:
            continue
        x=float((p1.x+p2.x)/2); ya=min(float(p1.y),float(p2.y)); yb=max(float(p1.y),float(p2.y))
        if not (ar.x0-0.5 <= x <= ar.x1+0.5 and ar.y0-0.5 <= ya <= ar.y1+0.5 and ar.y0-0.5 <= yb <= ar.y1+0.5):
            continue
        c=effective_drawing_color(d)
        if c is None:
            continue
        out.append({
            "drawing_index":idx,
            "x_pdf_pt":x,
            "y0_pdf_pt":ya,
            "y1_pdf_pt":yb,
            "length_pt":length,
            "stroke_hex":color_hex(c),
            "line_width_pt":float(d.get("width") or 0),
        })
    return out

def figure_inspect(pdf: Path, out: Path, dpi: int = 180) -> dict[str, Any]:
    require_fitz()
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    if len(doc) != 1:
        # standalone figures are normally one page; still inspect first page and report it.
        pass
    page = doc[0]
    axes = detect_axes(page)
    for n, a in enumerate(axes):
        a["axes_index"] = n
        a.update(detect_tick_positions(page, a["rect"]))
        a["candidate_curves"] = candidate_curves(page, a["rect"])
        a["marker_groups"] = detect_marker_groups(page, a["rect"])
        a["candidate_vertical_errorbars"] = candidate_vertical_errorbars(page, a["rect"])
    info = {
        "schema_version": "0.3",
        "file": str(pdf),
        "sha256": file_sha256(pdf),
        "page_count": len(doc),
        "page_size_pt": [float(page.rect.width), float(page.rect.height)],
        "image_count": len(page.get_images(full=True)),
        "drawing_count": len(page.get_drawings()),
        "colored_paths": page_colored_paths(page),
        "axes": axes,
    }
    jdump(info, out / "figure_inspection.json")
    render_pdf_page(pdf, out / "figure_preview.png", 1, dpi)
    # also render each detected axes with a small padding
    for a in axes:
        r = fitz.Rect(*a["rect"])
        pad = 12
        clip = fitz.Rect(max(0, r.x0-pad), max(0, r.y0-pad), min(page.rect.x1, r.x1+pad), min(page.rect.y1, r.y1+pad))
        render_pdf_page(pdf, out / f"axes_{a['axes_index']:02d}.png", 1, max(dpi, 220), clip)
    return info


def parse_series_spec(spec: str) -> list[tuple[int, str]]:
    result = []
    if not spec:
        return result
    for part in spec.split(","):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError(f"Invalid series entry: {part}; expected DRAWING_INDEX=name")
        i, name = part.split("=", 1)
        result.append((int(i.strip()), name.strip()))
    return result


def points_from_drawing(d: dict[str, Any]) -> list[fitz.Point]:
    pts: list[fitz.Point] = []
    for item in d.get("items", []):
        typ = item[0]
        if typ == "l":
            p1, p2 = item[1], item[2]
            if not pts or (abs(pts[-1].x - p1.x) > 1e-4 or abs(pts[-1].y - p1.y) > 1e-4):
                pts.append(fitz.Point(p1))
            pts.append(fitz.Point(p2))
        elif typ == "c":
            # Cubic Bezier: sample it rather than discarding curvature.
            p0, p1, p2, p3 = item[1], item[2], item[3], item[4]
            if not pts or (abs(pts[-1].x - p0.x) > 1e-4 or abs(pts[-1].y - p0.y) > 1e-4):
                pts.append(fitz.Point(p0))
            for k in range(1, 13):
                t = k / 12.0
                mt = 1 - t
                x = mt**3*p0.x + 3*mt**2*t*p1.x + 3*mt*t**2*p2.x + t**3*p3.x
                y = mt**3*p0.y + 3*mt**2*t*p1.y + 3*mt*t**2*p2.y + t**3*p3.y
                pts.append(fitz.Point(x, y))
    # consecutive exact duplicates add noise
    dedup = []
    for p in pts:
        if dedup and abs(dedup[-1].x-p.x) < 1e-6 and abs(dedup[-1].y-p.y) < 1e-6:
            continue
        dedup.append(p)
    return dedup



def parse_group_spec(spec: str) -> list[tuple[int, str]]:
    result=[]
    if not spec:
        return result
    for part in spec.split(","):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError(f"Invalid group entry: {part}; expected GROUP_INDEX=name")
        i,name=part.split("=",1)
        result.append((int(i.strip()),name.strip()))
    return result


def _calibrate_axes_for_vector(page, ax: dict[str, Any], args) -> tuple[Any, Any, list[tuple[float,float]], list[tuple[float,float]], dict[str,list[float]]]:
    x_anchors=parse_calibration(args.x_cal)
    y_anchors=parse_calibration(args.y_cal)
    ticks=detect_tick_positions(page,ax["rect"])
    if args.x_tick_values:
        vals=parse_value_list(args.x_tick_values); pos=ticks["x_tick_positions_pt"]
        if len(vals)!=len(pos):
            raise ValueError(f"x tick value count {len(vals)} does not match detected tick count {len(pos)}")
        x_anchors=list(zip(pos,vals))
    if args.y_tick_values:
        vals=parse_value_list(args.y_tick_values); pos=ticks["y_tick_positions_pt"]
        if len(vals)!=len(pos):
            raise ValueError(f"y tick value count {len(vals)} does not match detected tick count {len(pos)}")
        y_anchors=list(zip(pos,vals))
    x_fit=fit_calibration(x_anchors,args.x_scale) if x_anchors else None
    y_fit=fit_calibration(y_anchors,args.y_scale) if y_anchors else None
    if not x_fit and (args.x_min is None or args.x_max is None):
        raise ValueError("Provide --x-cal anchors (preferred) or both --x-min/--x-max")
    if not y_fit and (args.y_min is None or args.y_max is None):
        raise ValueError("Provide --y-cal anchors (preferred) or both --y-min/--y-max")
    return x_fit,y_fit,x_anchors,y_anchors,ticks


def vector_marker_extract(args) -> dict[str, Any]:
    require_fitz()
    pdf=Path(args.pdf).resolve(); out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=True)
    doc=fitz.open(pdf); page=doc[0]; axes=detect_axes(page)
    if args.axes_rect:
        vals=[float(v) for v in args.axes_rect.split(",")]
        if len(vals)!=4: raise ValueError("axes-rect must be x0,y0,x1,y1 in PDF points")
        ax={"rect":vals,"axes_index":None,"manual":True}
    else:
        if args.axes_index is None: raise ValueError("Provide --axes-index or --axes-rect")
        if args.axes_index<0 or args.axes_index>=len(axes): raise ValueError(f"axes-index {args.axes_index} out of range; detected {len(axes)} axes")
        ax=axes[args.axes_index]
    ar=fitz.Rect(*ax["rect"])
    groups=detect_marker_groups(page,ax["rect"])
    selected=parse_group_spec(args.groups)
    if not selected:
        selected=[(g["marker_group_index"],f"series_{i+1}") for i,g in enumerate(groups)]
    x_fit,y_fit,x_anchors,y_anchors,ticks=_calibrate_axes_for_vector(page,ax,args)
    errorbars=candidate_vertical_errorbars(page,ax["rect"]) if args.with_yerr else []
    rows=[]; smeta=[]
    for gi,name in selected:
        if gi<0 or gi>=len(groups): raise ValueError(f"marker group index {gi} out of range; detected {len(groups)} groups")
        g=groups[gi]
        # Use the effective color as a robust key for associated error bars.
        target_hex=g["stroke_or_fill_hex"]
        pts=[]
        marker_indices=g.get("data_drawing_indices") or g["drawing_indices"]
        marker_centers=g.get("data_centers_pdf_pt") or g["centers_pdf_pt"]
        for drawing_index,(px,py) in zip(marker_indices,marker_centers):
            xv=apply_calibration(px,x_fit,args.x_scale) if x_fit else map_axis_bounds(px,ar.x0,ar.x1,args.x_min,args.x_max,args.x_scale)
            yv=apply_calibration(py,y_fit,args.y_scale) if y_fit else map_axis_bounds(py,ar.y1,ar.y0,args.y_min,args.y_max,args.y_scale)
            rec={"series":name,"source_order":0,args.x_name:xv,args.y_name:yv,"pdf_x_pt":px,"pdf_y_pt":py,"marker_drawing_index":drawing_index,
                 "errorbar_drawing_index":None,"y_low":None,"y_high":None,"yerr_minus":None,"yerr_plus":None}
            if args.with_yerr:
                cands=[]
                for eb in errorbars:
                    if target_hex and eb["stroke_hex"] != target_hex: continue
                    if abs(eb["x_pdf_pt"]-px) > args.errorbar_x_tolerance: continue
                    # Prefer a bar that contains or nearly contains the marker center.
                    inside = eb["y0_pdf_pt"]-args.errorbar_y_tolerance <= py <= eb["y1_pdf_pt"]+args.errorbar_y_tolerance
                    dist = 0.0 if inside else min(abs(py-eb["y0_pdf_pt"]),abs(py-eb["y1_pdf_pt"]))
                    cands.append((0 if inside else 1,dist,abs(eb["x_pdf_pt"]-px),-eb["length_pt"],eb))
                if cands:
                    eb=sorted(cands,key=lambda z:z[:4])[0][-1]
                    ya=apply_calibration(eb["y0_pdf_pt"],y_fit,args.y_scale) if y_fit else map_axis_bounds(eb["y0_pdf_pt"],ar.y1,ar.y0,args.y_min,args.y_max,args.y_scale)
                    yb=apply_calibration(eb["y1_pdf_pt"],y_fit,args.y_scale) if y_fit else map_axis_bounds(eb["y1_pdf_pt"],ar.y1,ar.y0,args.y_min,args.y_max,args.y_scale)
                    low,high=min(ya,yb),max(ya,yb)
                    rec.update({"errorbar_drawing_index":eb["drawing_index"],"y_low":low,"y_high":high,"yerr_minus":max(0.0,yv-low),"yerr_plus":max(0.0,high-yv)})
            pts.append(rec)
        pts.sort(key=lambda r:(r[args.x_name],r["pdf_x_pt"]))
        for order,r in enumerate(pts): r["source_order"]=order; rows.append(r)
        smeta.append({"name":name,"marker_group_index":gi,"marker_count":len(pts),"stroke_or_fill_hex":target_hex,"fill_hex":g.get("fill_hex"),"item_signature":g.get("item_signature"),"with_yerr":bool(args.with_yerr)})
    fields=["series","source_order",args.x_name,args.y_name,"pdf_x_pt","pdf_y_pt","marker_drawing_index","errorbar_drawing_index","y_low","y_high","yerr_minus","yerr_plus"]
    csv_path=out/"reference_data.csv"
    with csv_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    meta={
        "schema_version":"0.3",
        "dataset_id":args.dataset_id or f"{pdf.stem}_markers_axes{args.axes_index if args.axes_index is not None else 'manual'}",
        "paper":{"title":None,"authors":[],"year":None,"doi":None,"arxiv_id":args.arxiv_id},
        "source":{"input_type":"figure_file","source_file":pdf.name,"source_sha256":file_sha256(pdf),"page":1,"panel":args.panel,"axes_index":args.axes_index,"axes_rect_pdf_pt":ax["rect"]},
        "quantity":{"name":args.quantity,"x_name":args.x_name,"x_unit":args.x_unit,"y_name":args.y_name,"y_unit":args.y_unit,"conditions":json.loads(args.conditions) if args.conditions else {}},
        "series":smeta,
        "extraction":{"provenance_grade":"B1","method":"vector_marker_reconstruction","x_scale":args.x_scale,"y_scale":args.y_scale,"with_yerr":bool(args.with_yerr),"calibration":{"x_anchors_pdf_to_data":x_anchors or None,"y_anchors_pdf_to_data":y_anchors or None,"x_fit":x_fit,"y_fit":y_fit}},
        "quality":{"status":"needs_review","checks":["Confirm marker groups map to the intended legend series.","Inspect marker_overlay.png."] + (["Confirm matched error bars belong to the selected marker series."] if args.with_yerr else [])},
        "outputs":{"csv":csv_path.name,"overlay":"marker_overlay.png"}
    }
    jdump(meta,out/"metadata.json")
    overlay=fitz.open(pdf); op=overlay[0]
    for r in rows:
        op.draw_circle(fitz.Point(r["pdf_x_pt"],r["pdf_y_pt"]),1.4,color=(0,0,0),width=0.45,overlay=True)
    opath=out/"marker_overlay.pdf"; overlay.save(opath); render_pdf_page(opath,out/"marker_overlay.png",1,220)
    return meta

def parse_calibration(spec: str | None) -> list[tuple[float, float]]:
    if not spec:
        return []
    pts=[]
    for part in spec.split(","):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError(f"Invalid calibration anchor: {part}; expected PDF_COORD=DATA_VALUE")
        p, d = part.split("=", 1)
        pts.append((float(p.strip()), float(d.strip())))
    if len(pts) < 2:
        raise ValueError("At least two calibration anchors are required")
    return pts


def parse_value_list(spec: str | None) -> list[float]:
    if not spec:
        return []
    return [float(v.strip()) for v in spec.split(",") if v.strip()]


def fit_calibration(anchors: list[tuple[float,float]], scale: str) -> dict[str, float]:
    xs=[p for p,_ in anchors]
    if scale == "linear":
        ys=[d for _,d in anchors]
    elif scale == "log10":
        if any(d <= 0 for _,d in anchors):
            raise ValueError("log10 calibration values must be > 0")
        ys=[math.log10(d) for _,d in anchors]
    else:
        raise ValueError(f"Unsupported scale: {scale}")
    mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
    denom=sum((x-mx)**2 for x in xs)
    if denom == 0:
        raise ValueError("Calibration PDF coordinates must differ")
    a=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/denom
    b=my-a*mx
    residuals=[y-(a*x+b) for x,y in zip(xs,ys)]
    rmse=(sum(r*r for r in residuals)/len(residuals))**0.5
    return {"a": a, "b": b, "rmse_transformed": rmse}


def apply_calibration(v: float, fit: dict[str,float], scale: str) -> float:
    z=fit["a"]*v+fit["b"]
    return z if scale == "linear" else 10**z


def map_axis_bounds(v: float, p0: float, p1: float, d0: float, d1: float, scale: str) -> float:
    f = (v - p0) / (p1 - p0)
    if scale == "linear":
        return d0 + f * (d1 - d0)
    if scale == "log10":
        if d0 <= 0 or d1 <= 0:
            raise ValueError("log10 axis limits must be > 0")
        return 10 ** (math.log10(d0) + f * (math.log10(d1) - math.log10(d0)))
    raise ValueError(f"Unsupported scale: {scale}")


def vector_extract(args) -> dict[str, Any]:
    require_fitz()
    pdf = Path(args.pdf).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    page = doc[0]
    axes = detect_axes(page)
    if args.axes_rect:
        vals=[float(v) for v in args.axes_rect.split(",")]
        if len(vals)!=4:
            raise ValueError("axes-rect must be x0,y0,x1,y1 in PDF points")
        ax={"rect": vals, "axes_index": None, "manual": True}
    else:
        if args.axes_index is None:
            raise ValueError("Provide --axes-index or --axes-rect")
        if args.axes_index < 0 or args.axes_index >= len(axes):
            raise ValueError(f"axes-index {args.axes_index} out of range; detected {len(axes)} axes")
        ax = axes[args.axes_index]
    ar = fitz.Rect(*ax["rect"])
    series = parse_series_spec(args.series)
    if not series:
        cands = candidate_curves(page, ax["rect"])
        series = [(c["drawing_index"], f"series_{i+1}") for i,c in enumerate(cands)]
    drawings = page.get_drawings()
    x_anchors = parse_calibration(args.x_cal)
    y_anchors = parse_calibration(args.y_cal)
    ticks = detect_tick_positions(page, ax["rect"])
    if args.x_tick_values:
        vals = parse_value_list(args.x_tick_values)
        pos = ticks["x_tick_positions_pt"]
        if len(vals) != len(pos):
            raise ValueError(f"x tick value count {len(vals)} does not match detected tick count {len(pos)}")
        x_anchors = list(zip(pos, vals))
    if args.y_tick_values:
        vals = parse_value_list(args.y_tick_values)
        pos = ticks["y_tick_positions_pt"]
        if len(vals) != len(pos):
            raise ValueError(f"y tick value count {len(vals)} does not match detected tick count {len(pos)}")
        y_anchors = list(zip(pos, vals))
    x_fit = fit_calibration(x_anchors, args.x_scale) if x_anchors else None
    y_fit = fit_calibration(y_anchors, args.y_scale) if y_anchors else None
    if not x_fit and (args.x_min is None or args.x_max is None):
        raise ValueError("Provide --x-cal anchors (preferred) or both --x-min/--x-max")
    if not y_fit and (args.y_min is None or args.y_max is None):
        raise ValueError("Provide --y-cal anchors (preferred) or both --y-min/--y-max")

    rows = []
    series_meta = []
    for drawing_index, name in series:
        if drawing_index < 0 or drawing_index >= len(drawings):
            raise ValueError(f"drawing index out of range: {drawing_index}")
        d = drawings[drawing_index]
        pts = points_from_drawing(d)
        kept = []
        for p in pts:
            # keep points inside plotting rectangle with a small numerical tolerance
            if ar.x0 - 1 <= p.x <= ar.x1 + 1 and ar.y0 - 1 <= p.y <= ar.y1 + 1:
                x = apply_calibration(p.x, x_fit, args.x_scale) if x_fit else map_axis_bounds(p.x, ar.x0, ar.x1, args.x_min, args.x_max, args.x_scale)
                # With explicit anchors, PDF-y inversion is naturally encoded by the fitted slope.
                y = apply_calibration(p.y, y_fit, args.y_scale) if y_fit else map_axis_bounds(p.y, ar.y1, ar.y0, args.y_min, args.y_max, args.y_scale)
                kept.append((p.x, p.y, x, y))
        # If path orientation is right-to-left, sort only for output convenience while preserving source order column.
        for order, (px, py, x, y) in enumerate(kept):
            rows.append({
                "series": name,
                "source_order": order,
                args.x_name: x,
                args.y_name: y,
                "pdf_x_pt": px,
                "pdf_y_pt": py,
                "source_drawing_index": drawing_index,
            })
        series_meta.append({
            "name": name,
            "source_drawing_index": drawing_index,
            "stroke_rgb": [float(v) for v in d.get("color")] if d.get("color") else None,
            "stroke_hex": color_hex(d.get("color")),
            "line_width_pt": float(d.get("width") or 0),
            "dashes": d.get("dashes"),
            "path_point_count": len(kept),
        })

    csv_path = out / "reference_data.csv"
    fieldnames = ["series", "source_order", args.x_name, args.y_name, "pdf_x_pt", "pdf_y_pt", "source_drawing_index"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    metadata = {
        "schema_version": "0.3",
        "dataset_id": args.dataset_id or f"{pdf.stem}_axes{args.axes_index if args.axes_index is not None else 'manual'}",
        "paper": {"title": None, "authors": [], "year": None, "doi": None, "arxiv_id": args.arxiv_id},
        "source": {
            "input_type": "figure_file",
            "source_file": pdf.name,
            "source_sha256": file_sha256(pdf),
            "tex_source": args.tex_source,
            "figure_label": args.figure_label,
            "figure_caption": args.figure_caption,
            "page": 1,
            "panel": args.panel,
            "axes_index": args.axes_index,
            "axes_rect_pdf_pt": ax["rect"],
        },
        "quantity": {
            "name": args.quantity,
            "x_name": args.x_name,
            "x_unit": args.x_unit,
            "y_name": args.y_name,
            "y_unit": args.y_unit,
            "conditions": json.loads(args.conditions) if args.conditions else {},
        },
        "series": series_meta,
        "extraction": {
            "provenance_grade": "B2",
            "method": "vector_path_reconstruction",
            "x_scale": args.x_scale,
            "y_scale": args.y_scale,
            "calibration": {
                "x_anchors_pdf_to_data": x_anchors or None,
                "y_anchors_pdf_to_data": y_anchors or None,
                "x_fit": x_fit,
                "y_fit": y_fit,
                "fallback_axis_bounds": {"x_min": args.x_min, "x_max": args.x_max, "y_min": args.y_min, "y_max": args.y_max} if not (x_fit and y_fit) else None
            },
            "notes": [
                "Vector path points reproduce the published plotted path and may reflect interpolation/path simplification rather than raw simulation samples."
            ],
        },
        "quality": {"status": "needs_review", "checks": ["Compare reconstructed values/path against rendered figure preview."]},
        "outputs": {"csv": csv_path.name},
    }
    jdump(metadata, out / "metadata.json")

    # Make a deterministic overlay on a rendered page: circles at extracted source coordinates.
    overlay_pdf = fitz.open(pdf)
    op = overlay_pdf[0]
    for row in rows:
        op.draw_circle(fitz.Point(row["pdf_x_pt"], row["pdf_y_pt"]), 1.1, color=(0,0,0), width=0.35, overlay=True)
    overlay_pdf_path = out / "vector_overlay.pdf"
    overlay_pdf.save(overlay_pdf_path)
    render_pdf_page(overlay_pdf_path, out / "vector_overlay.png", 1, 220)
    return metadata



def load_rgb_image(path: Path) -> np.ndarray:
    require_raster_dependencies()
    return np.array(Image.open(path).convert("RGB"))


def parse_bbox(spec: str | None, *, ints: bool = False) -> list[float] | list[int] | None:
    if not spec:
        return None
    vals = [float(v.strip()) for v in spec.split(",") if v.strip()]
    if len(vals) != 4:
        raise ValueError("bbox must contain x0,y0,x1,y1")
    if ints:
        return [int(round(v)) for v in vals]
    return vals


def _cluster_positions(values: list[int], tol: int = 4) -> list[int]:
    if not values:
        return []
    values = sorted(values)
    groups = [[values[0]]]
    for v in values[1:]:
        if abs(v - groups[-1][-1]) <= tol:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [int(round(sum(g) / len(g))) for g in groups]


def detect_raster_plot_rects(rgb: np.ndarray) -> list[dict[str, Any]]:
    """Detect rectangular scientific plotting regions from long dark axis/spine lines."""
    h, w = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    black = ((gray < 90).astype(np.uint8) * 255)
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, w // 30), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, h // 30)))
    hm = cv2.morphologyEx(black, cv2.MORPH_OPEN, hk)
    vm = cv2.morphologyEx(black, cv2.MORPH_OPEN, vk)
    hlines = cv2.HoughLinesP(hm, 1, np.pi / 180, threshold=40, minLineLength=max(50, int(w * 0.12)), maxLineGap=8)
    vlines = cv2.HoughLinesP(vm, 1, np.pi / 180, threshold=40, minLineLength=max(45, int(h * 0.12)), maxLineGap=8)
    hs=[]; vs=[]
    if hlines is not None:
        for l in np.asarray(hlines).reshape(-1, 4):
            x1,y1,x2,y2=map(int,l)
            if abs(y2-y1) <= 3:
                hs.append((int(round((y1+y2)/2)), min(x1,x2), max(x1,x2)))
    if vlines is not None:
        for l in np.asarray(vlines).reshape(-1, 4):
            x1,y1,x2,y2=map(int,l)
            if abs(x2-x1) <= 3:
                vs.append((int(round((x1+x2)/2)), min(y1,y2), max(y1,y2)))
    x_pos=_cluster_positions([x for x,_,_ in vs], tol=4)
    y_pos=_cluster_positions([y for y,_,_ in hs], tol=4)
    rects=[]
    for i,x0 in enumerate(x_pos):
        for x1 in x_pos[i+1:]:
            if x1-x0 < max(80, w*0.18):
                continue
            for j,y0 in enumerate(y_pos):
                for y1 in y_pos[j+1:]:
                    if y1-y0 < max(60, h*0.15):
                        continue
                    # Find supporting lines spanning most of each side.
                    top=max((max(0, min(x1,b)-max(x0,a)) for y,a,b in hs if abs(y-y0)<=5), default=0)
                    bot=max((max(0, min(x1,b)-max(x0,a)) for y,a,b in hs if abs(y-y1)<=5), default=0)
                    left=max((max(0, min(y1,b)-max(y0,a)) for x,a,b in vs if abs(x-x0)<=5), default=0)
                    right=max((max(0, min(y1,b)-max(y0,a)) for x,a,b in vs if abs(x-x1)<=5), default=0)
                    if min(top,bot) < 0.78*(x1-x0) or min(left,right) < 0.78*(y1-y0):
                        continue
                    area=(x1-x0)*(y1-y0)
                    if area > 0.88*w*h:
                        continue
                    rects.append({
                        "bbox_px":[x0,y0,x1,y1],
                        "width_px":x1-x0,
                        "height_px":y1-y0,
                        "support":{"top":top,"bottom":bot,"left":left,"right":right}
                    })
    # Deduplicate and prefer larger supported rectangles.
    rects.sort(key=lambda r: -(r["width_px"]*r["height_px"]))
    uniq=[]
    for r in rects:
        b=r["bbox_px"]
        if any(max(abs(a-bb) for a,bb in zip(b,u["bbox_px"])) <= 8 for u in uniq):
            continue
        uniq.append(r)
    uniq.sort(key=lambda r:(r["bbox_px"][1], r["bbox_px"][0]))
    for i,r in enumerate(uniq):
        r["plot_index"]=i
    return uniq[:24]


def dominant_plot_colors(rgb: np.ndarray, bbox: list[int], limit: int = 10) -> list[dict[str, Any]]:
    x0,y0,x1,y1=bbox
    crop=rgb[max(0,y0):min(rgb.shape[0],y1+1), max(0,x0):min(rgb.shape[1],x1+1)]
    if crop.size == 0:
        return []
    hsv=cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    # Exclude grayscale axes/text and very pale antialiasing pixels.
    mask=(hsv[:,:,1] >= 70) & (hsv[:,:,2] >= 50)
    pix=crop[mask]
    if len(pix)==0:
        return []
    q=(pix//24).astype(np.int32)
    keys=q[:,0]*121 + q[:,1]*11 + q[:,2]
    u,c=np.unique(keys, return_counts=True)
    order=np.argsort(c)[::-1]
    out=[]
    used=[]
    for idx in order:
        sel=keys==u[idx]
        mean=pix[sel].mean(axis=0)
        rgbv=[int(round(v)) for v in mean]
        # suppress near-duplicates from antialiasing
        if any(sum((a-b)**2 for a,b in zip(rgbv,z))**0.5 < 35 for z in used):
            continue
        used.append(rgbv)
        out.append({
            "rgb":rgbv,
            "hex":"#"+"".join(f"{v:02x}" for v in rgbv),
            "pixel_count":int(c[idx]),
            "fraction_of_crop":float(c[idx]/(crop.shape[0]*crop.shape[1]))
        })
        if len(out)>=limit:
            break
    return out


def raster_inspect(image: Path, out: Path) -> dict[str, Any]:
    require_raster_dependencies()
    out.mkdir(parents=True, exist_ok=True)
    rgb=load_rgb_image(image)
    h,w=rgb.shape[:2]
    plots=detect_raster_plot_rects(rgb)
    for p in plots:
        p["dominant_series_colors"] = dominant_plot_colors(rgb, p["bbox_px"])
    info={
        "schema_version":"0.3",
        "file":str(image),
        "sha256":file_sha256(image),
        "width_px":w,
        "height_px":h,
        "plot_regions":plots,
        "notes":["Dominant color proposals emphasize saturated colors; black/gray series should be mapped explicitly when present."],
    }
    jdump(info, out/"raster_inspection.json")
    # Annotated preview.
    im=Image.open(image).convert("RGB")
    dr=ImageDraw.Draw(im)
    for p in plots:
        x0,y0,x1,y1=p["bbox_px"]
        dr.rectangle((x0,y0,x1,y1), outline=(0,0,0), width=3)
        dr.text((x0+5,y0+5), f"plot {p['plot_index']}", fill=(0,0,0))
    im.save(out/"raster_inspection_overlay.png")
    return info


def parse_hex_color(s: str) -> tuple[int,int,int]:
    s=s.strip()
    if s.startswith("#"):
        s=s[1:]
    if len(s)==3:
        s="".join(ch*2 for ch in s)
    if len(s)!=6 or not re.fullmatch(r"[0-9a-fA-F]{6}", s):
        raise ValueError(f"Invalid RGB color: {s}")
    return tuple(int(s[i:i+2],16) for i in (0,2,4))


def parse_raster_series_spec(spec: str) -> list[tuple[str, tuple[int,int,int]]]:
    out=[]
    if not spec:
        return out
    for part in spec.split(","):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError(f"Invalid series entry: {part}; expected name=#RRGGBB")
        name,c=part.split("=",1)
        out.append((name.strip(), parse_hex_color(c.strip())))
    return out


def raster_color_mask(crop_rgb: np.ndarray, target_rgb: tuple[int,int,int], tolerance: float) -> np.ndarray:
    lab=cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    one=np.array([[target_rgb]], dtype=np.uint8)
    target=cv2.cvtColor(one, cv2.COLOR_RGB2LAB).astype(np.float32)[0,0]
    dist=np.sqrt(((lab-target)**2).sum(axis=2))
    return (dist <= tolerance).astype(np.uint8)


def _runs(vals: np.ndarray) -> list[tuple[int,int]]:
    if vals.size==0:
        return []
    vals=np.sort(vals)
    out=[]; start=prev=int(vals[0])
    for vv in vals[1:]:
        v=int(vv)
        if v<=prev+1:
            prev=v
        else:
            out.append((start,prev)); start=prev=v
    out.append((start,prev))
    return out


def trace_line_mask(mask: np.ndarray, max_gap: int = 10, max_jump: float = 60.0) -> list[tuple[int,float]]:
    """Recover a long coherent colored trace using dynamic programming across image columns."""
    h,w=mask.shape
    candidates=[]
    for x in range(w):
        ys=np.flatnonzero(mask[:,x])
        cs=[(a+b)/2 for a,b in _runs(ys)]
        candidates.append(cs)
    # States map candidate index to (score, previous x, previous candidate index).
    histories=[]
    last_states={}
    for x,cs in enumerate(candidates):
        states={}
        for j,y in enumerate(cs):
            best=(1.0, None, None)
            for px in range(max(0,x-max_gap-1), x):
                if px>=len(histories):
                    continue
                for pj,(pscore,_,_,py) in histories[px].items():
                    jump=abs(y-py)
                    gap=x-px-1
                    if jump > max_jump + gap*10:
                        continue
                    score=pscore + 1.0 - 0.018*jump - 0.20*gap
                    if score>best[0]:
                        best=(score,px,pj)
            states[j]=(best[0],best[1],best[2],float(y))
        histories.append(states)
    # Longest/highest score end state. Coverage bonus suppresses short legend swatches.
    best_end=None
    for x,states in enumerate(histories):
        for j,(score,px,pj,y) in states.items():
            val=score + 0.002*x
            if best_end is None or val>best_end[0]:
                best_end=(val,x,j)
    if best_end is None:
        return []
    _,x,j=best_end
    path=[]
    while x is not None and j is not None:
        score,px,pj,y=histories[x][j]
        path.append((x,y))
        x,j=px,pj
    path.reverse()
    # Remove obvious tiny solutions.
    if not path or path[-1][0]-path[0][0] < max(20, int(w*0.12)):
        return []
    return path


def scatter_points_from_mask(mask: np.ndarray, min_area: int = 4, max_area: int | None = None) -> list[tuple[float,float,int]]:
    n, labels, stats, cents=cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    out=[]
    H,W=mask.shape
    if max_area is None:
        max_area=max(100, int(H*W*0.02))
    for i in range(1,n):
        area=int(stats[i,cv2.CC_STAT_AREA])
        if min_area<=area<=max_area:
            x,y=map(float,cents[i])
            out.append((x,y,area))
    return out


def bar_points_from_mask(mask: np.ndarray, baseline_y: float | None = None, min_area: int = 20) -> list[tuple[float,float,float,int]]:
    n, labels, stats, cents=cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    H,W=mask.shape
    comps=[]
    for i in range(1,n):
        x=int(stats[i,cv2.CC_STAT_LEFT]); y=int(stats[i,cv2.CC_STAT_TOP])
        ww=int(stats[i,cv2.CC_STAT_WIDTH]); hh=int(stats[i,cv2.CC_STAT_HEIGHT]); area=int(stats[i,cv2.CC_STAT_AREA])
        if area<min_area or ww<2 or hh<3:
            continue
        # Filled bars should have reasonable rectangular occupancy.
        occ=area/max(1,ww*hh)
        if occ<0.35:
            continue
        cx=x+ww/2
        if baseline_y is None:
            # Common positive-bar convention; caller can supply baseline for signed bars.
            value_y=float(y)
        else:
            center_y=y+hh/2
            value_y=float(y if center_y < baseline_y else y+hh-1)
        comps.append((float(cx), value_y, float(hh), area))
    comps.sort()
    return comps


def raster_extract(args) -> dict[str, Any]:
    require_raster_dependencies()
    image=Path(args.image).resolve(); out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=True)
    rgb=load_rgb_image(image); H,W=rgb.shape[:2]
    plots=detect_raster_plot_rects(rgb)
    if args.plot_bbox:
        b=parse_bbox(args.plot_bbox, ints=True)
        plot={"bbox_px":b,"plot_index":None,"manual":True}
    else:
        if args.plot_index is None:
            raise ValueError("Provide --plot-index or --plot-bbox")
        if args.plot_index<0 or args.plot_index>=len(plots):
            raise ValueError(f"plot-index {args.plot_index} out of range; detected {len(plots)} plot regions")
        plot=plots[args.plot_index]
    x0,y0,x1,y1=map(int,plot["bbox_px"])
    if x1<=x0 or y1<=y0:
        raise ValueError("Invalid plot bbox")
    crop=rgb[y0:y1+1,x0:x1+1]
    series=parse_raster_series_spec(args.series)
    if not series:
        dom=dominant_plot_colors(rgb,[x0,y0,x1,y1],limit=4)
        series=[(f"series_{i+1}",tuple(c["rgb"])) for i,c in enumerate(dom)]
    x_anchors=parse_calibration(args.x_cal)
    y_anchors=parse_calibration(args.y_cal)
    x_fit=fit_calibration(x_anchors,args.x_scale) if x_anchors else None
    y_fit=fit_calibration(y_anchors,args.y_scale) if y_anchors else None
    if not x_fit and (args.x_min is None or args.x_max is None):
        raise ValueError("Provide --x-cal pixel anchors or both --x-min/--x-max")
    if not y_fit and (args.y_min is None or args.y_max is None):
        raise ValueError("Provide --y-cal pixel anchors or both --y-min/--y-max")
    excludes=[]
    for spec in args.exclude_bbox or []:
        bb=parse_bbox(spec,ints=True); excludes.append(bb)
    rows=[]; smeta=[]
    overlay=Image.open(image).convert("RGB"); dr=ImageDraw.Draw(overlay)
    for name,color in series:
        mask=raster_color_mask(crop,color,args.color_tolerance)
        # Remove plot-frame pixels; this is especially important for black/gray data series.
        m=max(0,int(args.axis_margin))
        if m:
            mask[:m,:]=0; mask[-m:,:]=0; mask[:,:m]=0; mask[:,-m:]=0
        # erase explicitly excluded regions, in absolute pixel coordinates
        for ex in excludes:
            ex0,ey0,ex1,ey1=ex
            ax0=max(0,ex0-x0); ay0=max(0,ey0-y0); ax1=min(mask.shape[1]-1,ex1-x0); ay1=min(mask.shape[0]-1,ey1-y0)
            if ax1>=ax0 and ay1>=ay0:
                mask[ay0:ay1+1,ax0:ax1+1]=0
        # tiny morphology closes anti-aliased gaps without aggressively merging nearby series
        if args.morphology>1:
            k=np.ones((args.morphology,args.morphology),np.uint8)
            mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,k)
        safe_name=re.sub(r"[^A-Za-z0-9._-]+","_",name).strip("_") or "series"
        mask_file=f"raster_mask_{safe_name}.png"
        Image.fromarray((mask*255).astype(np.uint8), mode="L").save(out/mask_file)
        points=[]
        if args.mode=="line":
            traced=trace_line_mask(mask,max_gap=args.max_gap,max_jump=args.max_jump)
            points=[(float(px),float(py),None) for px,py in traced[::max(1,args.sample_step)]]
        elif args.mode=="scatter":
            points=[(x,y,area) for x,y,area in scatter_points_from_mask(mask,args.min_component_area)]
        elif args.mode=="bar":
            base=None if args.baseline_px is None else float(args.baseline_px-y0)
            points=[(x,y,area) for x,y,h,area in bar_points_from_mask(mask,base,args.min_component_area)]
        else:
            raise ValueError(args.mode)
        for order,(cx,cy,aux) in enumerate(points):
            absx=x0+cx; absy=y0+cy
            xv=apply_calibration(absx,x_fit,args.x_scale) if x_fit else map_axis_bounds(absx,x0,x1,args.x_min,args.x_max,args.x_scale)
            yv=apply_calibration(absy,y_fit,args.y_scale) if y_fit else map_axis_bounds(absy,y1,y0,args.y_min,args.y_max,args.y_scale)
            rows.append({"series":name,"source_order":order,args.x_name:xv,args.y_name:yv,"pixel_x":absx,"pixel_y":absy,"source_aux":aux})
            if order % max(1,len(points)//150 or 1)==0:
                r=2
                dr.ellipse((absx-r,absy-r,absx+r,absy+r),outline=(0,0,0),width=1)
        smeta.append({"name":name,"target_rgb":list(color),"target_hex":"#"+"".join(f"{v:02x}" for v in color),"point_count":len(points),"mask_file":mask_file})
    csv_path=out/"reference_data.csv"
    fields=["series","source_order",args.x_name,args.y_name,"pixel_x","pixel_y","source_aux"]
    with csv_path.open("w",newline="",encoding="utf-8") as f:
        wri=csv.DictWriter(f,fieldnames=fields); wri.writeheader(); wri.writerows(rows)
    overlay.save(out/"raster_overlay.png")
    meta={
        "schema_version":"0.3",
        "dataset_id":args.dataset_id or f"{image.stem}_plot{args.plot_index if args.plot_index is not None else 'manual'}",
        "paper":{"title":None,"authors":[],"year":None,"doi":None,"arxiv_id":args.arxiv_id},
        "source":{"input_type":"figure_file","source_file":image.name,"source_sha256":file_sha256(image),"page":args.page,"panel":args.panel,"plot_index":args.plot_index,"plot_bbox_px":[x0,y0,x1,y1]},
        "quantity":{"name":args.quantity,"x_name":args.x_name,"x_unit":args.x_unit,"y_name":args.y_name,"y_unit":args.y_unit,"conditions":json.loads(args.conditions) if args.conditions else {}},
        "series":smeta,
        "extraction":{
            "provenance_grade":args.provenance_grade,
            "method":f"raster_{args.mode}_digitization",
            "x_scale":args.x_scale,
            "y_scale":args.y_scale,
            "color_tolerance_lab":args.color_tolerance,
            "algorithm":{
                "axis_margin_px":args.axis_margin,
                "morphology_kernel_px":args.morphology,
                "line_max_gap_px":args.max_gap if args.mode=="line" else None,
                "line_max_jump_px":args.max_jump if args.mode=="line" else None,
                "sample_step_px":args.sample_step if args.mode=="line" else None,
                "min_component_area_px":args.min_component_area if args.mode in {"scatter","bar"} else None,
                "baseline_px":args.baseline_px if args.mode=="bar" else None
            },
            "calibration":{
                "x_anchors_pixel_to_data":x_anchors or None,
                "y_anchors_pixel_to_data":y_anchors or None,
                "x_fit":x_fit,
                "y_fit":y_fit,
                "fallback_axis_bounds":{"x_min":args.x_min,"x_max":args.x_max,"y_min":args.y_min,"y_max":args.y_max} if not (x_fit and y_fit) else None,
                "linear_resolution_estimate":{
                    "x_data_per_pixel":((args.x_max-args.x_min)/(x1-x0)) if args.x_scale=="linear" and x_fit is None and args.x_min is not None and args.x_max is not None else None,
                    "y_data_per_pixel":((args.y_max-args.y_min)/(y1-y0)) if args.y_scale=="linear" and y_fit is None and args.y_min is not None and args.y_max is not None else None
                }
            },
            "excluded_bboxes_px":excludes
        },
        "quality":{"status":"needs_review","checks":["Inspect raster_overlay.png for alignment with the source marks/curve.","Confirm tick calibration, series mapping, and any overlapping/occluded regions."]},
        "outputs":{"csv":csv_path.name,"overlay":"raster_overlay.png"}
    }
    jdump(meta,out/"metadata.json")
    return meta


def _is_number_token(v: str) -> bool:
    try:
        float(v.strip().replace("−", "-"))
        return True
    except Exception:
        return False


def _coerce_cell(v: Any) -> Any:
    if v is None:
        return ""
    numpy_integer = (np.integer,) if np is not None else ()
    numpy_floating = (np.floating,) if np is not None else ()
    if isinstance(v, (int, float, *numpy_integer, *numpy_floating)):
        if isinstance(v, (float, *numpy_floating)) and (math.isnan(float(v)) or math.isinf(float(v))):
            return str(v)
        return v.item() if hasattr(v, "item") else v
    t=str(v).strip()
    if _is_number_token(t):
        try:
            return float(t.replace("−","-"))
        except Exception:
            pass
    return t


def _sanitize_columns(cols: list[str], n: int) -> list[str]:
    out=[]; used={}
    for i in range(n):
        raw=(cols[i] if i < len(cols) else "") or f"col_{i+1}"
        name=re.sub(r"\s+","_",str(raw).strip())
        name=re.sub(r"[^A-Za-z0-9_.()\[\]-]+","_",name).strip("_") or f"col_{i+1}"
        used[name]=used.get(name,0)+1
        if used[name]>1: name=f"{name}_{used[name]}"
        out.append(name)
    return out


def _strip_latex_cell(cell: str) -> str:
    cell=cell.strip()
    cell=re.sub(r"\\(?:textbf|textit|emph|mathrm|mathbf|mathit|operatorname)\s*\{([^{}]*)\}",r"\1",cell)
    cell=re.sub(r"\\(?:hline|toprule|midrule|bottomrule|cline\{[^{}]*\})","",cell)
    cell=re.sub(r"\\(?:cite|citep|citet|ref|label)\s*\{[^{}]*\}","",cell)
    cell=cell.replace("$","").replace("~"," ")
    cell=cell.replace(r"\%","%").replace(r"\_","_")
    cell=re.sub(r"\\,|\\;|\\!|\\quad|\\qquad"," ",cell)
    cell=re.sub(r"\s+"," ",cell).strip()
    return cell


def _rows_from_delimited_text(text: str, delimiter: str = "auto", header: str = "auto") -> tuple[list[str], list[list[Any]], dict[str, Any]]:
    raw_lines=[]
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith(("#","%","//")):
            continue
        # Strip common trailing comments only when separated from data.
        line=re.split(r"\s+#\s|\s+//\s",line,maxsplit=1)[0].strip()
        if line: raw_lines.append(line)
    if not raw_lines:
        raise ValueError("No tabular rows found")
    delim={"comma":",","tab":"\t","semicolon":";","space":"whitespace"}.get(delimiter,delimiter)
    if delim == "auto":
        scores={d:sum(line.count(d) for line in raw_lines[:20]) for d in [",","\t",";"]}
        best=max(scores,key=scores.get)
        delim=best if scores[best] > 0 else "whitespace"
    split=[]
    for line in raw_lines:
        if delim == "whitespace":
            toks=re.split(r"\s+",line.strip())
        else:
            toks=next(csv.reader([line],delimiter=delim))
        split.append([t.strip() for t in toks])
    widths=[len(r) for r in split]
    # Prefer the modal width and discard obvious prose/footer lines while reporting it.
    width=max(set(widths),key=widths.count)
    kept=[r for r in split if len(r)==width]
    dropped=len(split)-len(kept)
    if not kept: raise ValueError("No consistent-width rows found")
    if header == "yes": has_header=True
    elif header == "no": has_header=False
    else:
        first_num=sum(_is_number_token(x) for x in kept[0])/max(1,width)
        later=kept[1:min(len(kept),6)]
        later_num=(sum(sum(_is_number_token(x) for x in r) for r in later)/max(1,len(later)*width)) if later else first_num
        has_header=first_num < 0.6 and later_num >= 0.6
    if has_header:
        cols=_sanitize_columns([_strip_latex_cell(x) for x in kept[0]],width)
        data=kept[1:]
    else:
        cols=[f"col_{i+1}" for i in range(width)]
        data=kept
    rows=[[_coerce_cell(_strip_latex_cell(x)) for x in r] for r in data]
    return cols,rows,{"delimiter":delim,"header_detected":has_header,"dropped_inconsistent_rows":dropped,"column_count":width}


def _rows_from_json(path: Path) -> tuple[list[str], list[list[Any]], dict[str, Any]]:
    obj=json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj,list) and obj and all(isinstance(x,dict) for x in obj):
        cols=[]
        for rec in obj:
            for k in rec:
                if k not in cols: cols.append(str(k))
        return _sanitize_columns(cols,len(cols)), [[_coerce_cell(rec.get(k,"")) for k in cols] for rec in obj], {"json_shape":"records"}
    if isinstance(obj,list) and (not obj or all(isinstance(x,(list,tuple)) for x in obj)):
        width=max((len(x) for x in obj),default=1)
        cols=[f"col_{i+1}" for i in range(width)]
        rows=[[_coerce_cell(v) for v in list(r)+[""]*(width-len(r))] for r in obj]
        return cols,rows,{"json_shape":"matrix"}
    if isinstance(obj,dict):
        vals=list(obj.values())
        if vals and all(isinstance(v,list) for v in vals) and len({len(v) for v in vals})==1:
            cols=list(map(str,obj.keys())); n=len(vals[0])
            return _sanitize_columns(cols,len(cols)), [[_coerce_cell(obj[k][i]) for k in obj] for i in range(n)], {"json_shape":"column_arrays"}
        return ["key","value"], [[str(k),json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else _coerce_cell(v)] for k,v in obj.items()], {"json_shape":"mapping"}
    return ["value"],[[_coerce_cell(obj)]],{"json_shape":"scalar"}


def _rows_from_numpy(path: Path) -> tuple[list[str], list[list[Any]], dict[str, Any]]:
    require_numpy()
    if path.suffix.lower()==".npy":
        arr=np.load(path,allow_pickle=False)
        name=path.stem
        arrays={name:arr}
    else:
        z=np.load(path,allow_pickle=False); arrays={k:z[k] for k in z.files}
    if len(arrays)>1 and all(a.ndim==1 for a in arrays.values()) and len({len(a) for a in arrays.values()})==1:
        cols=list(arrays); n=len(next(iter(arrays.values())))
        return _sanitize_columns(cols,len(cols)), [[_coerce_cell(arrays[k][i]) for k in cols] for i in range(n)], {"numpy_shape":"parallel_1d_arrays"}
    if len(arrays)==1:
        name,arr=next(iter(arrays.items()))
        if arr.ndim==1:
            return ["index","value"], [[i,_coerce_cell(v)] for i,v in enumerate(arr.tolist())], {"numpy_shape":list(arr.shape),"array_name":name}
        if arr.ndim==2:
            cols=[f"col_{i+1}" for i in range(arr.shape[1])]
            return cols,[[_coerce_cell(v) for v in row] for row in arr.tolist()],{"numpy_shape":list(arr.shape),"array_name":name}
    rows=[]
    for name,arr in arrays.items():
        for idx in np.ndindex(arr.shape):
            rows.append([name,*idx,_coerce_cell(arr[idx])])
    maxdim=max((a.ndim for a in arrays.values()),default=1)
    cols=["array"]+[f"index_{i}" for i in range(maxdim)]+["value"]
    padded=[]
    for r in rows:
        padded.append(r[:-1]+[""]*(len(cols)-len(r))+[r[-1]])
    return cols,padded,{"numpy_shape":"long_format","arrays":{k:list(v.shape) for k,v in arrays.items()}}


def _rows_from_excel(path: Path, sheet: str | None) -> tuple[list[str], list[list[Any]], dict[str, Any]]:
    try:
        import openpyxl
    except Exception as exc:
        raise ValueError("Excel extraction requires openpyxl") from exc
    wb=openpyxl.load_workbook(path,read_only=True,data_only=True)
    ws=wb[sheet] if sheet else wb[wb.sheetnames[0]]
    raw=[[c for c in row] for row in ws.iter_rows(values_only=True)]
    raw=[r for r in raw if any(v is not None for v in r)]
    if not raw: raise ValueError("No rows found in worksheet")
    width=max(len(r) for r in raw); raw=[list(r)+[None]*(width-len(r)) for r in raw]
    first_num=sum(isinstance(x,(int,float)) for x in raw[0])/max(1,width)
    later=raw[1:min(6,len(raw))]
    later_num=sum(sum(isinstance(x,(int,float)) for x in r) for r in later)/max(1,len(later)*width) if later else first_num
    has_header=first_num<0.6 and later_num>=0.5
    cols=_sanitize_columns([str(v or "") for v in raw[0]],width) if has_header else [f"col_{i+1}" for i in range(width)]
    data=raw[1:] if has_header else raw
    return cols,[[_coerce_cell(v) for v in r] for r in data],{"sheet":ws.title,"header_detected":has_header}


def _rows_from_hdf5(path: Path) -> tuple[list[str], list[list[Any]], dict[str, Any]]:
    require_numpy()
    try:
        import h5py
    except Exception as exc:
        raise ValueError("HDF5 extraction requires h5py") from exc
    rows=[]; shapes={}
    with h5py.File(path,"r") as h5:
        def visit(name,obj):
            if isinstance(obj,h5py.Dataset):
                arr=np.asarray(obj); shapes[name]=list(arr.shape)
                for idx in np.ndindex(arr.shape):
                    v=arr[idx]
                    rows.append([name,";".join(map(str,idx)),_coerce_cell(v.decode() if isinstance(v,(bytes,bytearray)) else v)])
        h5.visititems(visit)
    return ["dataset","index","value"],rows,{"datasets":shapes,"format":"hdf5_long"}


def _extract_tex_table_rows(tex: str, index: int) -> tuple[list[str],list[list[Any]],dict[str,Any]]:
    tables=list(re.finditer(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}",strip_tex_comments(tex),re.S))
    if index<0 or index>=len(tables): raise ValueError(f"table index {index} out of range; found {len(tables)}")
    body=tables[index].group(1)
    tabs=list(re.finditer(r"\\begin\{tabular\}\{[^{}]*\}(.*?)\\end\{tabular\}",body,re.S))
    if not tabs: raise ValueError("Selected table has no simple tabular environment")
    tab=tabs[0].group(1)
    tab=re.sub(r"\\(?:hline|toprule|midrule|bottomrule)\s*","",tab)
    rawrows=[r.strip() for r in re.split(r"(?<!\\)\\\\",tab) if r.strip()]
    split=[[_strip_latex_cell(c) for c in r.split("&")] for r in rawrows]
    width=max((len(r) for r in split),default=0); split=[r for r in split if len(r)==width]
    if not split: raise ValueError("No consistent rows in tabular")
    first_num=sum(_is_number_token(x) for x in split[0])/max(1,width)
    later=split[1:min(6,len(split))]
    later_num=sum(sum(_is_number_token(x) for x in r) for r in later)/max(1,len(later)*width) if later else first_num
    has_header=first_num<0.6 and later_num>=0.4
    cols=_sanitize_columns(split[0],width) if has_header else [f"col_{i+1}" for i in range(width)]
    data=split[1:] if has_header else split
    return cols,[[_coerce_cell(x) for x in r] for r in data],{"table_index":index,"header_detected":has_header,"column_count":width}


def _extract_tex_verbatim_rows(tex: str,index: int,delimiter: str="auto",header: str="auto") -> tuple[list[str],list[list[Any]],dict[str,Any]]:
    blocks=list(re.finditer(r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}",strip_tex_comments(tex),re.S))
    if index<0 or index>=len(blocks): raise ValueError(f"verbatim index {index} out of range; found {len(blocks)}")
    cols,rows,meta=_rows_from_delimited_text(blocks[index].group(1),delimiter,header)
    meta["verbatim_index"]=index
    return cols,rows,meta


def source_extract(args) -> dict[str, Any]:
    src=Path(args.input).resolve(); out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=True)
    kind=args.kind
    if kind=="auto":
        kind="tex-table" if src.suffix.lower()==".tex" and args.table_index is not None else ("tex-verbatim" if src.suffix.lower()==".tex" and args.verbatim_index is not None else "raw")
    details={}
    if kind=="tex-table":
        tex=src.read_text(encoding="utf-8",errors="replace")
        cols,rows,details=_extract_tex_table_rows(tex,args.table_index or 0)
        grade="A2"; method="tex_table_extraction"
    elif kind=="tex-verbatim":
        tex=src.read_text(encoding="utf-8",errors="replace")
        cols,rows,details=_extract_tex_verbatim_rows(tex,args.verbatim_index or 0,args.delimiter,args.header)
        grade="A2"; method="tex_verbatim_extraction"
    elif kind=="raw":
        ext=src.suffix.lower()
        if ext not in NORMALIZABLE_RAW_EXTS:
            raise ValueError(f"Raw format {ext or '<none>'} is inventoried but not normalized by this version. Do not execute or unpickle untrusted source files.")
        if ext==".json": cols,rows,details=_rows_from_json(src)
        elif ext in {".npy",".npz"}: cols,rows,details=_rows_from_numpy(src)
        elif ext in {".xlsx",".xls"}: cols,rows,details=_rows_from_excel(src,args.sheet)
        elif ext in {".h5",".hdf5"}: cols,rows,details=_rows_from_hdf5(src)
        else: cols,rows,details=_rows_from_delimited_text(src.read_text(encoding="utf-8",errors="replace"),args.delimiter,args.header)
        grade="A0"; method="author_data_normalization"
    else:
        raise ValueError(kind)
    csv_path=out/"reference_data.csv"
    with csv_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(cols); w.writerows(rows)
    meta={
        "schema_version":"0.3",
        "dataset_id":args.dataset_id or f"{src.stem}_{kind.replace('-','_')}",
        "paper":{"title":None,"authors":[],"year":None,"doi":None,"arxiv_id":args.arxiv_id},
        "source":{"input_type":"source_file","source_file":src.name,"source_path":str(src),"source_sha256":file_sha256(src),"source_kind":kind},
        "quantity":{"name":args.quantity,"columns":cols,"conditions":json.loads(args.conditions) if args.conditions else {}},
        "series":[],
        "extraction":{"provenance_grade":grade,"method":method,"details":details,"notes":["Values are normalized without smoothing, interpolation, or unit conversion."]},
        "quality":{"status":"needs_review","checks":["Confirm inferred headers/columns and source semantics before downstream use."]},
        "outputs":{"csv":csv_path.name}
    }
    jdump(meta,out/"metadata.json")
    return meta


def _colorbar_lut(rgb: np.ndarray,bbox:list[int],orientation:str,min_position:str,vmin:float,vmax:float,scale:str) -> tuple[np.ndarray,np.ndarray]:
    x0,y0,x1,y1=bbox; crop=rgb[y0:y1+1,x0:x1+1]
    if crop.size==0: raise ValueError("Empty colorbar bbox")
    if orientation=="vertical":
        a=max(0,int(crop.shape[1]*0.25)); b=max(a+1,int(crop.shape[1]*0.75))
        colors=np.median(crop[:,a:b,:],axis=1).astype(np.uint8)
        if min_position=="bottom": order=np.arange(len(colors)-1,-1,-1)
        elif min_position=="top": order=np.arange(len(colors))
        else: raise ValueError("vertical colorbar min-position must be top or bottom")
    else:
        a=max(0,int(crop.shape[0]*0.25)); b=max(a+1,int(crop.shape[0]*0.75))
        colors=np.median(crop[a:b,:,:],axis=0).astype(np.uint8)
        if min_position=="left": order=np.arange(len(colors))
        elif min_position=="right": order=np.arange(len(colors)-1,-1,-1)
        else: raise ValueError("horizontal colorbar min-position must be left or right")
    colors=colors[order]
    # Colorbars frequently have a dark outline. Drop a tiny end margin before
    # constructing the LUT so the outline cannot become a false endpoint color.
    edge=max(1,int(round(len(colors)*0.01)))
    if len(colors) > 2*edge + 4:
        colors=colors[edge:-edge]
    # Remove consecutive near-identical colors produced by antialiased colorbar borders.
    keep=[0]
    for i in range(1,len(colors)):
        if np.linalg.norm(colors[i].astype(float)-colors[keep[-1]].astype(float))>=0.8:
            keep.append(i)
    colors=colors[keep]
    if len(colors)<4: raise ValueError("Colorbar contains too few distinct colors")
    if scale=="linear": vals=np.linspace(vmin,vmax,len(colors))
    elif scale=="log10":
        if vmin<=0 or vmax<=0: raise ValueError("log10 colorbar limits must be >0")
        vals=np.logspace(math.log10(vmin),math.log10(vmax),len(colors))
    else: raise ValueError(scale)
    return colors,vals


def raster_heatmap_extract(args) -> dict[str, Any]:
    require_raster_dependencies()
    image=Path(args.image).resolve(); out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=True)
    rgb=load_rgb_image(image); H,W=rgb.shape[:2]
    hb=parse_bbox(args.heatmap_bbox,ints=True); cb=parse_bbox(args.colorbar_bbox,ints=True)
    if hb is None or cb is None: raise ValueError("Provide --heatmap-bbox and --colorbar-bbox")
    hx0,hy0,hx1,hy1=hb; hx0=max(0,hx0);hy0=max(0,hy0);hx1=min(W-1,hx1);hy1=min(H-1,hy1)
    colors,values=_colorbar_lut(rgb,cb,args.colorbar_orientation,args.colorbar_min_position,args.colorbar_min,args.colorbar_max,args.value_scale)
    lut_lab=cv2.cvtColor(colors.reshape(-1,1,3),cv2.COLOR_RGB2LAB).reshape(-1,3).astype(np.float32)
    stride=max(1,args.stride)
    hm=max(0,int(args.heatmap_margin))
    if hx1-hx0 <= 2*hm or hy1-hy0 <= 2*hm: raise ValueError("heatmap margin is too large for the bbox")
    ys=np.arange(hy0+hm,hy1-hm+1,stride); xs=np.arange(hx0+hm,hx1-hm+1,stride)
    sample=rgb[np.ix_(ys,xs)]
    flat=sample.reshape(-1,3)
    uniq,inv=np.unique(flat,axis=0,return_inverse=True)
    ulab=cv2.cvtColor(uniq.reshape(-1,1,3).astype(np.uint8),cv2.COLOR_RGB2LAB).reshape(-1,3).astype(np.float32)
    nearest=np.empty(len(uniq),dtype=np.int32); dist=np.empty(len(uniq),dtype=np.float32)
    for start in range(0,len(uniq),2048):
        block=ulab[start:start+2048]
        d=((block[:,None,:]-lut_lab[None,:,:])**2).sum(axis=2)
        idx=np.argmin(d,axis=1); nearest[start:start+len(block)]=idx; dist[start:start+len(block)]=np.sqrt(d[np.arange(len(block)),idx])
    nidx=nearest[inv].reshape(sample.shape[:2]); ndist=dist[inv].reshape(sample.shape[:2]); mapped=values[nidx]
    x_anchors=parse_calibration(args.x_cal); y_anchors=parse_calibration(args.y_cal)
    x_fit=fit_calibration(x_anchors,args.x_scale) if x_anchors else None; y_fit=fit_calibration(y_anchors,args.y_scale) if y_anchors else None
    if not x_fit and (args.x_min is None or args.x_max is None): raise ValueError("Provide --x-cal or both --x-min/--x-max")
    if not y_fit and (args.y_min is None or args.y_max is None): raise ValueError("Provide --y-cal or both --y-min/--y-max")
    rows=[]; valid_count=0
    csv_path=out/"reference_data.csv"
    with csv_path.open("w",newline="",encoding="utf-8") as f:
        fields=[args.x_name,args.y_name,args.value_name,"pixel_x","pixel_y","color_distance_lab","valid"]
        wri=csv.DictWriter(f,fieldnames=fields); wri.writeheader()
        for iy,py in enumerate(ys):
            yv=apply_calibration(float(py),y_fit,args.y_scale) if y_fit else map_axis_bounds(float(py),hy1,hy0,args.y_min,args.y_max,args.y_scale)
            for ix,px in enumerate(xs):
                xv=apply_calibration(float(px),x_fit,args.x_scale) if x_fit else map_axis_bounds(float(px),hx0,hx1,args.x_min,args.x_max,args.x_scale)
                dd=float(ndist[iy,ix]); valid=dd<=args.max_color_distance
                if valid: valid_count+=1
                rec={args.x_name:xv,args.y_name:yv,args.value_name:(float(mapped[iy,ix]) if valid else ""),"pixel_x":int(px),"pixel_y":int(py),"color_distance_lab":dd,"valid":int(valid)}
                wri.writerow(rec)
    recon=colors[nidx].astype(np.uint8)
    Image.fromarray(recon,"RGB").save(out/"heatmap_reconstruction.png")
    err=np.clip(ndist/max(1e-9,args.max_color_distance)*255,0,255).astype(np.uint8)
    Image.fromarray(err,"L").save(out/"heatmap_color_error.png")
    meta={
        "schema_version":"0.3","dataset_id":args.dataset_id or f"{image.stem}_heatmap",
        "paper":{"title":None,"authors":[],"year":None,"doi":None,"arxiv_id":args.arxiv_id},
        "source":{"input_type":"figure_file","source_file":image.name,"source_sha256":file_sha256(image),"page":args.page,"panel":args.panel,"heatmap_bbox_px":hb,"colorbar_bbox_px":cb},
        "quantity":{"name":args.quantity,"x_name":args.x_name,"x_unit":args.x_unit,"y_name":args.y_name,"y_unit":args.y_unit,"value_name":args.value_name,"value_unit":args.value_unit,"conditions":json.loads(args.conditions) if args.conditions else {}},
        "series":[],
        "extraction":{"provenance_grade":args.provenance_grade,"method":"raster_heatmap_colorbar_digitization","x_scale":args.x_scale,"y_scale":args.y_scale,"colorbar":{"min":args.colorbar_min,"max":args.colorbar_max,"scale":args.value_scale,"orientation":args.colorbar_orientation,"min_position":args.colorbar_min_position,"lut_size":len(colors)},"stride_px":stride,"heatmap_margin_px":hm,"max_color_distance_lab":args.max_color_distance,"calibration":{"x_anchors_pixel_to_data":x_anchors or None,"y_anchors_pixel_to_data":y_anchors or None,"x_fit":x_fit,"y_fit":y_fit,"fallback_axis_bounds":{"x_min":args.x_min,"x_max":args.x_max,"y_min":args.y_min,"y_max":args.y_max} if not (x_fit and y_fit) else None}},
        "quality":{"status":"needs_review","valid_fraction":valid_count/max(1,mapped.size),"checks":["Inspect heatmap_reconstruction.png and heatmap_color_error.png.","Confirm the colorbar limits, orientation, direction, and axis calibration."]},
        "outputs":{"csv":csv_path.name,"reconstruction":"heatmap_reconstruction.png","color_error":"heatmap_color_error.png"}
    }
    jdump(meta,out/"metadata.json"); return meta


def dataset_validate(dataset_dir: Path) -> dict[str, Any]:
    meta_path=dataset_dir/"metadata.json"; csv_path=dataset_dir/"reference_data.csv"
    issues=[]; warnings=[]
    if not meta_path.exists(): issues.append("metadata.json missing")
    if not csv_path.exists(): issues.append("reference_data.csv missing")
    meta={}
    if meta_path.exists():
        try: meta=json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc: issues.append(f"metadata.json invalid: {exc}")
    rows=0; fields=[]
    if csv_path.exists():
        try:
            with csv_path.open(encoding="utf-8",newline="") as f:
                r=csv.reader(f); fields=next(r,[]); rows=sum(1 for _ in r)
            if not fields: issues.append("CSV header missing")
            if rows==0: warnings.append("CSV contains no data rows")
        except Exception as exc: issues.append(f"CSV invalid: {exc}")
    if meta:
        if meta.get("schema_version")!="0.3": warnings.append(f"schema_version is {meta.get('schema_version')}, expected 0.3")
        grade=((meta.get("extraction") or {}).get("provenance_grade"))
        if grade not in {"A0","A1","A2","B1","B2","C1","C2"}: issues.append(f"invalid or missing provenance grade: {grade}")
        for _,fname in (meta.get("outputs") or {}).items():
            if isinstance(fname,str) and fname and not (dataset_dir/fname).exists(): warnings.append(f"declared output missing: {fname}")
    result={"schema_version":"0.3","dataset_dir":str(dataset_dir),"row_count":rows,"columns":fields,"ok":not issues,"issues":issues,"warnings":warnings}
    jdump(result,dataset_dir/"validation_report.json")
    return result

def source_manifest(source: Path, out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    temporary_source = None
    if source.is_dir():
        root = source.resolve()
    else:
        temporary_source = tempfile.TemporaryDirectory(prefix="simflow-reference-source-")
        root = Path(temporary_source.name).resolve()
        safe_extract_tar(source, root)
    files = [p for p in root.rglob("*") if p.is_file()]
    raw_data = []
    scripts = []
    figures = []
    tex_files = []
    for p in files:
        rel = str(p.relative_to(root))
        ext = p.suffix
        rec = {"file": rel, "size_bytes": p.stat().st_size}
        if ext.lower() in {e.lower() for e in RAW_EXTS} and "readme" not in p.name.lower():
            rec["normalizer_supported"] = ext.lower() in NORMALIZABLE_RAW_EXTS
            raw_data.append(rec)
        if ext in SCRIPT_EXTS or ext.lower() in {x.lower() for x in SCRIPT_EXTS}:
            scripts.append(rec)
        if ext.lower() in FIG_EXTS:
            if ext.lower() == ".pdf":
                try:
                    st = inspect_pdf_structure(p)
                    rec.update({"coarse_kind": st["coarse_kind"], "total_images": st["total_images"], "total_drawings": st["total_drawings"]})
                except Exception as exc:
                    rec["inspect_error"] = str(exc)
            else:
                rec["coarse_kind"] = "raster" if ext.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"} else "unknown"
            figures.append(rec)
        if ext.lower() == ".tex":
            tex_files.append(parse_tex_file(p, root))

    manifest = {
        "schema_version": "0.3",
        "input": str(source),
        "input_sha256": file_sha256(source) if source.is_file() else None,
        "source_root": str(root) if source.is_dir() else None,
        "archive_inspection_ephemeral": not source.is_dir(),
        "file_count": len(files),
        "raw_data_candidates": raw_data,
        "plotting_script_candidates": scripts,
        "figure_files": figures,
        "tex": tex_files,
        "priority_guidance": ["A0 raw data", "A1 plotting data/script", "A2 TeX numerical values", "B1 vector markers", "B2 vector paths", "C1/C2 raster digitization"],
    }
    jdump(manifest, out / "source_manifest.json")
    if temporary_source is not None:
        temporary_source.cleanup()
    return manifest


def pdf_inspect(pdf: Path, out: Path) -> dict[str, Any]:
    require_fitz()
    out.mkdir(parents=True, exist_ok=True)
    info = inspect_pdf_structure(pdf)
    jdump(info, out / "pdf_inspection.json")
    # render first few pages for semantic inspection without exploding output size
    doc = fitz.open(pdf)
    preview_dir = out / "previews"
    preview_dir.mkdir(exist_ok=True)
    for pno in range(min(4, len(doc))):
        render_pdf_page(pdf, preview_dir / f"page_{pno+1:03d}.png", pno+1, 160)
    return info


def raster_prepare(args) -> dict[str, Any]:
    src = Path(args.input).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    if src.suffix.lower() == ".pdf":
        require_fitz()
        doc = fitz.open(src)
        page = doc[args.page - 1]
        images = page.get_images(full=True)
        if images and not args.force_render:
            for n, im in enumerate(images, 1):
                xref = im[0]
                base = doc.extract_image(xref)
                ext = base.get("ext", "png")
                p = out / f"embedded_image_{n:02d}.{ext}"
                p.write_bytes(base["image"])
                rects = page.get_image_rects(xref)
                jobs.append({
                    "file": p.name,
                    "method": "embedded_image",
                    "xref": xref,
                    "page": args.page,
                    "width_px": int(base.get("width") or im[2]),
                    "height_px": int(base.get("height") or im[3]),
                    "page_rects_pdf_pt": [[float(r.x0), float(r.y0), float(r.x1), float(r.y1)] for r in rects],
                    "provenance_grade": "C1"
                })
        else:
            clip = None
            if args.bbox:
                vals = [float(v) for v in args.bbox.split(",")]
                if len(vals) != 4:
                    raise ValueError("bbox must be x0,y0,x1,y1 in PDF points")
                clip = fitz.Rect(*vals)
            p = out / f"rendered_page_{args.page:03d}.png"
            render_pdf_page(src, p, args.page, args.dpi, clip)
            jobs.append({
                "file": p.name,
                "method": "rendered_page_crop" if clip else "rendered_page",
                "page": args.page,
                "dpi": args.dpi,
                "clip_pdf_pt": [float(clip.x0),float(clip.y0),float(clip.x1),float(clip.y1)] if clip else None,
                "provenance_grade": "C2"
            })
    else:
        require_pillow()
        p = out / src.name
        shutil.copy2(src, p)
        with Image.open(p) as im:
            wh=list(im.size)
        jobs.append({"file": p.name, "method": "standalone_raster", "width_px": wh[0], "height_px": wh[1], "provenance_grade": "C1"})
    manifest = {
        "schema_version": "0.3",
        "source": str(src),
        "source_sha256": file_sha256(src),
        "jobs": jobs,
        "next_step": "Run raster-inspect on the prepared image, then raster-extract with calibrated axes and explicit series mapping.",
    }
    jdump(manifest, out / "raster_job.json")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="extract_reference_data.py",
        description="SimFlow scientific reference-data extraction helpers",
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("source-manifest", help="Inspect an arXiv/source archive or directory")
    s.add_argument("source")
    s.add_argument("--out", required=True)

    s = sub.add_parser("pdf-inspect", help="Inspect publisher/full-paper PDF structure")
    s.add_argument("pdf")
    s.add_argument("--out", required=True)

    s = sub.add_parser("figure-inspect", help="Detect axes and candidate vector curves in a standalone figure PDF")
    s.add_argument("pdf")
    s.add_argument("--out", required=True)
    s.add_argument("--dpi", type=int, default=180)

    s = sub.add_parser("vector-extract", help="Extract selected vector drawing paths into calibrated scientific coordinates")
    s.add_argument("pdf")
    s.add_argument("--out", required=True)
    s.add_argument("--axes-index", type=int)
    s.add_argument("--axes-rect", help="Manual plotting rectangle x0,y0,x1,y1 in PDF points; use when automatic axes detection fails")
    s.add_argument("--x-min", type=float)
    s.add_argument("--x-max", type=float)
    s.add_argument("--y-min", type=float)
    s.add_argument("--y-max", type=float)
    s.add_argument("--x-cal", help="Calibration anchors as PDF_COORD=DATA_VALUE,...")
    s.add_argument("--y-cal", help="Calibration anchors as PDF_COORD=DATA_VALUE,...")
    s.add_argument("--x-tick-values", help="Preferred: visible major tick values left-to-right; pairs with auto-detected x tick positions")
    s.add_argument("--y-tick-values", help="Preferred: visible major tick values top-to-bottom; pairs with auto-detected y tick positions")
    s.add_argument("--x-scale", choices=["linear", "log10"], default="linear")
    s.add_argument("--y-scale", choices=["linear", "log10"], default="linear")
    s.add_argument("--series", default="", help="Comma-separated DRAWING_INDEX=name mappings")
    s.add_argument("--dataset-id")
    s.add_argument("--arxiv-id")
    s.add_argument("--tex-source")
    s.add_argument("--figure-label")
    s.add_argument("--figure-caption")
    s.add_argument("--panel")
    s.add_argument("--quantity", required=True)
    s.add_argument("--x-name", default="x")
    s.add_argument("--x-unit")
    s.add_argument("--y-name", default="y")
    s.add_argument("--y-unit")
    s.add_argument("--conditions", help="JSON object string")

    s = sub.add_parser("vector-marker-extract", help="Extract repeated vector marker groups; optionally recover matched vertical y error bars")
    s.add_argument("pdf")
    s.add_argument("--out", required=True)
    s.add_argument("--axes-index", type=int)
    s.add_argument("--axes-rect", help="Manual plotting rectangle x0,y0,x1,y1 in PDF points")
    s.add_argument("--x-min", type=float); s.add_argument("--x-max", type=float)
    s.add_argument("--y-min", type=float); s.add_argument("--y-max", type=float)
    s.add_argument("--x-cal", help="Calibration anchors as PDF_COORD=DATA_VALUE,...")
    s.add_argument("--y-cal", help="Calibration anchors as PDF_COORD=DATA_VALUE,...")
    s.add_argument("--x-tick-values"); s.add_argument("--y-tick-values")
    s.add_argument("--x-scale", choices=["linear","log10"], default="linear")
    s.add_argument("--y-scale", choices=["linear","log10"], default="linear")
    s.add_argument("--groups", default="", help="Comma-separated MARKER_GROUP_INDEX=name mappings")
    s.add_argument("--with-yerr", action="store_true")
    s.add_argument("--errorbar-x-tolerance", type=float, default=1.0)
    s.add_argument("--errorbar-y-tolerance", type=float, default=1.0)
    s.add_argument("--dataset-id"); s.add_argument("--arxiv-id"); s.add_argument("--panel")
    s.add_argument("--quantity", required=True)
    s.add_argument("--x-name", default="x"); s.add_argument("--x-unit")
    s.add_argument("--y-name", default="y"); s.add_argument("--y-unit")
    s.add_argument("--conditions", help="JSON object string")

    s = sub.add_parser("source-extract", help="Normalize author source data or TeX-embedded numerical tables/verbatim blocks")
    s.add_argument("input")
    s.add_argument("--out", required=True)
    s.add_argument("--kind", choices=["auto","raw","tex-table","tex-verbatim"], default="auto")
    s.add_argument("--table-index", type=int)
    s.add_argument("--verbatim-index", type=int)
    s.add_argument("--delimiter", default="auto", help="auto, whitespace, comma, tab, semicolon, or a single delimiter character")
    s.add_argument("--header", choices=["auto","yes","no"], default="auto")
    s.add_argument("--sheet")
    s.add_argument("--dataset-id"); s.add_argument("--arxiv-id")
    s.add_argument("--quantity", default="Author-provided numerical data")
    s.add_argument("--conditions", help="JSON object string")

    s = sub.add_parser("raster-prepare", help="Extract embedded raster figures or render a page/crop without resampling when possible")
    s.add_argument("input")
    s.add_argument("--out", required=True)
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--bbox", help="x0,y0,x1,y1 in PDF points")
    s.add_argument("--dpi", type=int, default=300)
    s.add_argument("--force-render", action="store_true")

    s = sub.add_parser("raster-inspect", help="Detect plot regions and candidate series colors in a raster scientific figure")
    s.add_argument("image")
    s.add_argument("--out", required=True)

    s = sub.add_parser("raster-extract", help="Digitize line, scatter, or bar data from a raster scientific figure")
    s.add_argument("image")
    s.add_argument("--out", required=True)
    s.add_argument("--plot-index", type=int)
    s.add_argument("--plot-bbox", help="Manual plot rectangle x0,y0,x1,y1 in image pixels")
    s.add_argument("--mode", choices=["line","scatter","bar"], default="line")
    s.add_argument("--series", default="", help="Comma-separated name=#RRGGBB mappings; if omitted, dominant saturated colors are proposed")
    s.add_argument("--color-tolerance", type=float, default=28.0, help="Euclidean tolerance in OpenCV Lab space")
    s.add_argument("--exclude-bbox", action="append", help="Absolute image-pixel bbox x0,y0,x1,y1 to ignore; repeatable")
    s.add_argument("--morphology", type=int, default=1, help="Closing-kernel size; 1 disables morphology")
    s.add_argument("--axis-margin", type=int, default=4, help="Ignore this many pixels along each plot-frame edge")
    s.add_argument("--max-gap", type=int, default=12)
    s.add_argument("--max-jump", type=float, default=70.0)
    s.add_argument("--sample-step", type=int, default=1)
    s.add_argument("--min-component-area", type=int, default=4)
    s.add_argument("--baseline-px", type=float, help="Absolute baseline y pixel for signed bar charts")
    s.add_argument("--x-min", type=float)
    s.add_argument("--x-max", type=float)
    s.add_argument("--y-min", type=float)
    s.add_argument("--y-max", type=float)
    s.add_argument("--x-cal", help="Calibration anchors as ABS_PIXEL_X=DATA_VALUE,...")
    s.add_argument("--y-cal", help="Calibration anchors as ABS_PIXEL_Y=DATA_VALUE,...")
    s.add_argument("--x-scale", choices=["linear","log10"], default="linear")
    s.add_argument("--y-scale", choices=["linear","log10"], default="linear")
    s.add_argument("--dataset-id")
    s.add_argument("--arxiv-id")
    s.add_argument("--page", type=int)
    s.add_argument("--panel")
    s.add_argument("--provenance-grade", choices=["C1","C2"], default="C1")
    s.add_argument("--quantity", required=True)
    s.add_argument("--x-name", default="x")
    s.add_argument("--x-unit")
    s.add_argument("--y-name", default="y")
    s.add_argument("--y-unit")
    s.add_argument("--conditions", help="JSON object string")

    s = sub.add_parser("raster-heatmap-extract", help="Digitize a raster heatmap by calibrating its colorbar")
    s.add_argument("image")
    s.add_argument("--out", required=True)
    s.add_argument("--heatmap-bbox", required=True, help="x0,y0,x1,y1 in image pixels")
    s.add_argument("--colorbar-bbox", required=True, help="x0,y0,x1,y1 in image pixels")
    s.add_argument("--colorbar-min", type=float, required=True); s.add_argument("--colorbar-max", type=float, required=True)
    s.add_argument("--colorbar-orientation", choices=["vertical","horizontal"], default="vertical")
    s.add_argument("--colorbar-min-position", choices=["top","bottom","left","right"], default="bottom")
    s.add_argument("--value-scale", choices=["linear","log10"], default="linear")
    s.add_argument("--max-color-distance", type=float, default=32.0)
    s.add_argument("--stride", type=int, default=1)
    s.add_argument("--heatmap-margin", type=int, default=2, help="Ignore this many pixels along the heatmap bbox edge")
    s.add_argument("--x-min", type=float); s.add_argument("--x-max", type=float)
    s.add_argument("--y-min", type=float); s.add_argument("--y-max", type=float)
    s.add_argument("--x-cal"); s.add_argument("--y-cal")
    s.add_argument("--x-scale", choices=["linear","log10"], default="linear")
    s.add_argument("--y-scale", choices=["linear","log10"], default="linear")
    s.add_argument("--dataset-id"); s.add_argument("--arxiv-id"); s.add_argument("--page", type=int); s.add_argument("--panel")
    s.add_argument("--provenance-grade", choices=["C1","C2"], default="C1")
    s.add_argument("--quantity", required=True)
    s.add_argument("--x-name", default="x"); s.add_argument("--x-unit")
    s.add_argument("--y-name", default="y"); s.add_argument("--y-unit")
    s.add_argument("--value-name", default="value"); s.add_argument("--value-unit")
    s.add_argument("--conditions", help="JSON object string")

    s = sub.add_parser("dataset-validate", help="Validate a normalized output directory and write validation_report.json")
    s.add_argument("dataset_dir")
    for name, command_parser in sub.choices.items():
        add_helper_recording_args(command_parser, default_stage="analysis_visualization")
        if name != "dataset-validate":
            command_parser.add_argument(
                "--overwrite",
                action="store_true",
                help="Replace a non-empty dedicated output directory",
            )
    return p


def _command_input_paths(args: argparse.Namespace) -> list[str]:
    for name in ("source", "pdf", "input", "image", "dataset_dir"):
        value = getattr(args, name, None)
        if value:
            return [str(Path(value).expanduser().resolve())]
    return []


def _attach_helper_evidence(args: argparse.Namespace, result: dict[str, Any]) -> dict[str, Any]:
    validation_ok = result.get("ok")
    status = "warning" if validation_ok is False else "success"
    result["helper_evidence"] = build_helper_evidence(
        helper="extract_reference_data",
        capability=args.command.replace("-", "_"),
        status=status,
        stage=args.stage,
        activity="scientific_reference_extraction",
        evidence_role="reference_dataset",
        source_files=[source_file_record(path) for path in _command_input_paths(args)],
        actual_tool_used={"software": "custom", "name": "simflow-reference-extraction"},
        parser_status="parsed" if status == "success" else "partial",
        claim_limits=[
            "Successful parsing does not establish scientific correctness.",
            "Figure-derived values remain reconstructions at their recorded provenance grade.",
        ],
        warnings=result.get("warnings", []),
        limitations=[
            "Semantic figure, panel, series, unit, and condition choices require scientific review.",
        ],
        parent_artifacts=getattr(args, "parent_artifact", None),
        dataset_schema_version=result.get("schema_version"),
    )
    return result


def main() -> int:
    args = build_parser().parse_args()
    try:
        if hasattr(args, "out"):
            args.out = str(
                prepare_output_dir(
                    Path(args.out),
                    overwrite=bool(args.overwrite),
                    project_root=args.project_root,
                )
            )
        if args.command == "source-manifest":
            result = source_manifest(Path(args.source).resolve(), Path(args.out).resolve())
        elif args.command == "pdf-inspect":
            result = pdf_inspect(Path(args.pdf).resolve(), Path(args.out).resolve())
        elif args.command == "figure-inspect":
            result = figure_inspect(Path(args.pdf).resolve(), Path(args.out).resolve(), args.dpi)
        elif args.command == "vector-extract":
            result = vector_extract(args)
        elif args.command == "vector-marker-extract":
            result = vector_marker_extract(args)
        elif args.command == "source-extract":
            result = source_extract(args)
        elif args.command == "raster-prepare":
            result = raster_prepare(args)
        elif args.command == "raster-inspect":
            result = raster_inspect(Path(args.image).resolve(), Path(args.out).resolve())
        elif args.command == "raster-extract":
            result = raster_extract(args)
        elif args.command == "raster-heatmap-extract":
            result = raster_heatmap_extract(args)
        elif args.command == "dataset-validate":
            result = dataset_validate(Path(args.dataset_dir).resolve())
        else:
            raise AssertionError(args.command)
        result = _attach_helper_evidence(args, result)
        output_paths = [args.out] if hasattr(args, "out") else [str(Path(args.dataset_dir).resolve() / "validation_report.json")]
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).with_name("extract_reference_data.py"),
            helper_name="extract_reference_data",
            software="custom",
            input_paths=_command_input_paths(args),
            output_paths=output_paths,
            metadata={
                "capability": args.command.replace("-", "_"),
                "evidence_role": "reference_dataset",
                "dataset_schema_version": result.get("schema_version"),
            },
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
