# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Accuracy and robustness of the optical mark reader on synthetic filled sheets.

    python SoftwareX/experiments/run_omr.py <work_dir> [n_realistic] [n_per_level]

Writes <work_dir>/omr_results.json. Every sheet is filled with known answers, degraded and
read with examtool.lector.leer_pagina, exactly as Aspa does with a real scan.
"""
import json
import random
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

import common as C
from examtool.lector import leer_pagina
from examtool import layout as L
import demo_data


def compare(res, truth):
    """Per-sheet metrics against the ground truth."""
    out = {"read": bool(res.get("ok")), "qr": False, "id": None, "q_total": len(truth["respuestas"]),
           "q_ok": 0, "q_err": 0, "q_err_flagged": 0, "box_fp": 0, "box_fn": 0, "flagged": 0}
    if not res.get("ok"):
        out["error"] = res.get("error")
        return out
    qr = res.get("qr") or {}
    out["qr"] = qr.get("modelo") == truth["modelo"] and qr.get("copia") == truth["copia"]
    if truth["digitos"]:
        out["id"] = res["id_leido"] == truth["digitos"]
    for q, (rv, rl) in enumerate(zip(truth["respuestas"], res["respuestas"])):
        flagged = bool(rl.get("dudas"))
        out["flagged"] += flagged
        if rv["m"] == rl["m"] and rv["anular"] == rl["anular"]:
            out["q_ok"] += 1
        else:
            out["q_err"] += 1
            out["q_err_flagged"] += flagged
        out["box_fp"] += len(set(rl["m"]) - set(rv["m"])) + (rl["anular"] and not rv["anular"])
        out["box_fn"] += len(set(rv["m"]) - set(rl["m"])) + (rv["anular"] and not rl["anular"])
    return out


def summarise(rows, times=None):
    n = len(rows)
    read = [r for r in rows if r["read"]]
    q_total = sum(r["q_total"] for r in rows)
    q_ok = sum(r["q_ok"] for r in read)
    q_err = sum(r["q_err"] for r in read)
    ids = [r["id"] for r in read if r["id"] is not None]
    s = {
        "sheets": n,
        "read_rate": len(read) / n if n else 0,
        "qr_rate": sum(r["qr"] for r in rows) / n if n else 0,
        "id_rate": (sum(ids) / len(ids)) if ids else None,
        "answer_accuracy": q_ok / q_total if q_total else 0,  # unread sheets count as wrong
        "answer_errors": q_err,
        "answer_errors_flagged": sum(r["q_err_flagged"] for r in read),
        "answers": q_total,
        "box_fp": sum(r["box_fp"] for r in read),
        "box_fn": sum(r["box_fn"] for r in read),
        "flagged": sum(r["flagged"] for r in read),
        "unread_reasons": sorted({r.get("error", "") for r in rows if not r["read"]}),
        "perfect_sheets": sum(1 for r in read if r["q_err"] == 0 and r["qr"] and r["id"] in (None, True)) / n if n else 0,
    }
    if times:
        s["time_mean_s"] = statistics.mean(times)
        s["time_median_s"] = statistics.median(times)
    return s


def read(img):
    t0 = time.perf_counter()
    r = leer_pagina(img)
    return r, time.perf_counter() - t0


def realistic_experiment(proy, n, seed=11):
    """Mixture of defects of examtool.simulacion (rotation ±4°, perspective, curvature up to 2 mm,
    shadow, grey paper, noise, blur, JPEG 60-85) with pen and light pencil; 1 in 10 upside down."""
    rng = random.Random(seed)
    studs = demo_data.students()
    ncop = len(proy.generado()["impresion"])
    rows, times, by_ink = [], [], {}
    for h in range(n):
        ink = rng.choice([25, 40, 60, 90, 130])
        img, truth = C.fill_sheet(proy, h % ncop, studs[h % len(studs)], rng, ink=ink)
        img = C.realistic(img, rng, upside_down=(h % 10 == 3))
        img = C.jpeg(img, rng.uniform(60, 85))
        res, dt = read(img)
        row = compare(res, truth)
        rows.append(row)
        times.append(dt)
        by_ink.setdefault(ink, []).append(row)
    return {"all": summarise(rows, times), "by_ink": {str(k): summarise(v) for k, v in sorted(by_ink.items())},
            "image_size_px": list(img.shape)}


SWEEPS = {
    # name: (levels, function(img, level, rng) -> img)
    "rotation_deg": ([0, 2, 5, 10, 15, 30, 45, 90, 180, 270],
                     lambda im, v, r: (np.ascontiguousarray(np.rot90(im, k=v // 90)) if v % 90 == 0 and v
                                       else C.rotate(im, v, scale=0.82 if v > 10 else 0.95))),
    "perspective": ([0, 0.02, 0.04, 0.06, 0.08, 0.10], lambda im, v, r: C.perspective(im, v, r)),
    "phone_tilt": ([0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30], lambda im, v, r: C.phone_photo(im, v, r)),
    "warp_mm": ([0, 1, 1.5, 2, 2.5, 3, 4], lambda im, v, r: C.warp(im, v, r)),
    "blur_sigma_px": ([0, 1, 1.5, 2, 2.5, 3, 4], lambda im, v, r: C.blur(im, v)),
    "noise_sigma": ([0, 10, 20, 30, 40, 50], lambda im, v, r: C.noise(im, v, r)),
    "jpeg_quality": ([95, 70, 50, 30, 20, 10, 5], lambda im, v, r: C.jpeg(im, v)),
    "dpi": ([220, 200, 150, 120, 100, 80, 60, 50, 40], lambda im, v, r: C.resample(im, v)),
    "shadow_min_gain": ([1.0, 0.8, 0.6, 0.45, 0.3, 0.2], lambda im, v, r: C.shadow(im, v)),
    "occluded_markers": ([0, 1, 2], lambda im, v, r: C.occlude_markers(im, list(range(v)))),
}
INK_LEVELS = [25, 60, 100, 130, 145, 160, 175, 190, 210]


def sweeps(proy, n_per_level, seed=21):
    studs = demo_data.students()
    ncop = len(proy.generado()["impresion"])
    out = {}
    for name, (levels, fn) in SWEEPS.items():
        out[name] = {}
        for v in levels:
            rng = random.Random(seed)
            rows = []
            for h in range(n_per_level):
                img, truth = C.fill_sheet(proy, h % ncop, studs[h % len(studs)], rng, ink=40)
                img = C.noise(fn(img, v, rng), 3, rng)
                rows.append(compare(read(img)[0], truth))
            out[name][str(v)] = summarise(rows)
            print(f"  {name}={v}: acc={out[name][str(v)]['answer_accuracy']:.4f} "
                  f"qr={out[name][str(v)]['qr_rate']:.2f} read={out[name][str(v)]['read_rate']:.2f}", flush=True)
    out["ink_grey_level"] = {}
    for v in INK_LEVELS:
        rng = random.Random(seed)
        rows = []
        for h in range(n_per_level):
            img, truth = C.fill_sheet(proy, h % ncop, studs[h % len(studs)], rng, ink=v)
            rows.append(compare(read(C.noise(img, 3, rng))[0], truth))
        out["ink_grey_level"][str(v)] = summarise(rows)
        print(f"  ink={v}: acc={out['ink_grey_level'][str(v)]['answer_accuracy']:.4f}", flush=True)
    return out


def non_sheet_pages(proy):
    """Question pages, blank pages and unrelated images must be ignored, not reported as errors."""
    import pymupdf as fitz
    res = {}
    with fitz.open(proy.ruta("examenes.pdf")) as d:
        pix = d[1].get_pixmap(dpi=C.DPI, colorspace=fitz.csGRAY)
        page2 = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width).copy()
    r = leer_pagina(page2)
    res["question_page"] = {"ok": r["ok"], "ignored": bool(r.get("vacia")), "error": r.get("error")}
    rng = random.Random(1)
    blank = C.noise(np.full_like(page2, 240), 4, rng)
    r = leer_pagina(blank)
    res["blank_page"] = {"ok": r["ok"], "ignored": bool(r.get("vacia")), "error": r.get("error")}
    return res


def main():
    work = Path(sys.argv[1])
    n_real = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    n_lvl = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    work.mkdir(parents=True, exist_ok=True)
    proy = next((C.Proyecto(d) for d in work.glob("software-engineering-final-exam*")), None) \
        or C.make_versions_project(work)
    pers = next((C.Proyecto(d) for d in work.glob("software-engineering-personalised-exam*")), None) \
        or C.make_personalised_project(work)
    results = {"cv2": cv2.__version__}
    print("realistic (versions)...", flush=True)
    results["realistic_versions"] = realistic_experiment(proy, n_real)
    print(json.dumps(results["realistic_versions"]["all"], indent=1), flush=True)
    print("realistic (personalised)...", flush=True)
    results["realistic_personalised"] = realistic_experiment(pers, max(n_real // 4, 40), seed=12)
    print(json.dumps(results["realistic_personalised"]["all"], indent=1), flush=True)
    print("non-sheet pages...", flush=True)
    results["non_sheet"] = non_sheet_pages(proy)
    print(results["non_sheet"])
    print("sweeps...", flush=True)
    results["sweeps"] = sweeps(proy, n_lvl)
    (work / "omr_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print("saved", work / "omr_results.json")


if __name__ == "__main__":
    main()
