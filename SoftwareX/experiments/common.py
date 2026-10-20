# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared helpers for the SoftwareX experiments: demo projects, filled sheets, degradations."""
import random
import sys
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from examtool import i18n  # noqa: E402
from examtool import layout as L  # noqa: E402
from examtool.pdf import _pdf_copia, generar_pdf, generar_soluciones  # noqa: E402
from examtool.proyecto import Proyecto  # noqa: E402
from examtool.simulacion import marcar, aspa  # noqa: E402

import demo_data  # noqa: E402

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

DPI = 220
K = DPI / 25.4


def p(x, y):
    return int(round(x * K)), int(round(y * K))


def make_versions_project(base: Path, seed=2026) -> Proyecto:
    """Four-version exam (A: testing group, B: requirements, C: both, D: whole bank)."""
    proy = Proyecto.crear(base, "Software Engineering Final exam")
    demo_data.write_bank(proy.ruta("preguntas.xlsx"))
    demo_data.write_students(proy.ruta("alumnos.xlsx"))
    cfg = proy.config()
    cfg.update(titulo="Final exam", asignatura="Software Engineering", convocatoria="Junio",
               curso="2025-2026", idioma_examen="en", n_preguntas=20, valor_bien=1.0, valor_mal=-0.25,
               multiples="parcial", copias=40,
               modelos=[{"nombre": "A", "grupos": "T"}, {"nombre": "B", "grupos": "R"},
                        {"nombre": "C", "grupos": "T,R"}, {"nombre": "D", "grupos": ""}])
    proy.guardar_config(cfg)
    with i18n.en("en"):
        proy.generar(semilla=seed)
        generar_pdf(proy)
        generar_soluciones(proy)
    return proy


def make_personalised_project(base: Path, seed=2026) -> Proyecto:
    """One exam per student without the questions each one already passed in class."""
    proy = Proyecto.crear(base, "Software Engineering Personalised exam")
    demo_data.write_bank(proy.ruta("preguntas.xlsx"))
    rng = random.Random(5)
    passed = {}
    for i in range(40):
        k = rng.choice([0, 0, 2, 4, 6, 8])
        pool = [str(x) for x in range(1, 11)] if i % 2 == 0 else [str(x) for x in range(11, 21)]
        passed[i] = ", ".join(sorted(rng.sample(pool, k), key=int))
    demo_data.write_students(proy.ruta("alumnos.xlsx"), passed)
    cfg = proy.config()
    cfg.update(titulo="Personalised exam", asignatura="Software Engineering", convocatoria="Junio",
               curso="2025-2026", idioma_examen="en", tipo="personalizado", n_preguntas=20,
               valor_bien=1.0, valor_mal=-0.25, reserva=3,
               modelos=[{"nombre": "A", "grupos": "T"}, {"nombre": "B", "grupos": "R"}])
    proy.guardar_config(cfg)
    with i18n.en("en"):
        proy.generar(semilla=seed)
        generar_pdf(proy)
        generar_soluciones(proy)
    return proy


_CACHE = {}


def blank_sheet(proy, midx, copia):
    """First page of a printed copy rendered at DPI (as the printer would)."""
    key = (str(proy.dir), midx, copia)
    if key not in _CACHE:
        with i18n.en("en"):
            gen = proy.generado()
            pdf = _pdf_copia(proy.config(), proy.descripcion(personalizado=bool(gen["modelos"][midx].get("alumno"))),
                             gen, midx, copia)
        with fitz.open(stream=pdf, filetype="pdf") as d:
            pix = d[0].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            _CACHE[key] = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width).copy()
    return _CACHE[key].copy()


def fill_sheet(proy, copia_idx, student, rng, ink=40, p_blank=0.10, p_correct=0.5, p_two=0.15, p_annul=0.05):
    """Fill a copy as a student would. Returns (image, truth)."""
    gen = proy.generado()
    midx = gen["impresion"][copia_idx]
    img = blank_sheet(proy, midx, copia_idx + 1)
    printed = gen["modelos"][midx].get("alumno")
    dig = "" if printed else "".join(ch for ch in student[0] if ch.isdigit())[:10]
    for c, ch in enumerate(dig):
        wb = L.id_write_box(c)
        cv2.putText(img, ch, p(wb.x + 0.6, wb.y + wb.h - 1), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.1, ink, 2, cv2.LINE_AA)
        marcar(img, L.id_box(c, int(ch)), rng, ink)
    respuestas = []
    for q, item in enumerate(gen["modelos"][midx]["preguntas"]):
        u = rng.random()
        n_opts = sum(1 for o in item["perm"] if o is not None)
        letters = "ABCD"[:n_opts]
        if u < p_blank:
            marc = ""
        elif u < p_blank + p_correct:
            marc = item["correctas"]
        elif u < p_blank + p_correct + p_two and n_opts > 2:
            marc = "".join(sorted(rng.sample(letters, 2)))
        else:
            marc = rng.choice(letters)
        anular = rng.random() < p_annul
        for k, letra in enumerate("ABCD"):
            if letra in marc:
                marcar(img, L.ans_box(q, k), rng, ink)
        if anular:
            aspa(img, L.ans_box(q, 4), rng, ink)
        respuestas.append({"m": marc, "anular": anular})
    return img, {"modelo": midx, "copia": copia_idx + 1, "digitos": dig, "respuestas": respuestas,
                 "documento": printed["documento"] if printed else student[0]}


# ------------------------------------------------------------------ degradations

def rotate(img, angle, scale=1.0, shift=(0, 0), border=235):
    h, w = img.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    M[:, 2] += shift
    return cv2.warpAffine(img, M, (w, h), borderValue=border)


def perspective(img, strength, rng, border=235):
    """Random displacement of the four corners by up to `strength` x width."""
    h, w = img.shape
    d = strength * w
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = src + np.float32([[rng.uniform(-d, d), rng.uniform(-d, d)] for _ in range(4)])
    return cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h), borderValue=border)


def phone_photo(img, tilt, rng, out_w=3000):
    """Sheet lying on a darker table photographed with a tilted phone (keystone + background)."""
    h, w = img.shape
    W, H = int(w * 1.25), int(h * 1.2)
    canvas = np.full((H, W), 90, np.uint8)
    canvas = (canvas + np.random.default_rng(rng.randint(0, 999)).normal(0, 8, canvas.shape)).clip(0, 255).astype(np.uint8)
    ox, oy = (W - w) // 2, (H - h) // 2
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    # top edge farther from the camera: shrink it by `tilt`
    k = tilt * w / 2
    dst = np.float32([[ox + k, oy + 0.5 * k], [ox + w - k, oy + 0.5 * k], [ox + w, oy + h], [ox, oy + h]])
    dst += np.float32([[rng.uniform(-15, 15), rng.uniform(-15, 15)] for _ in range(4)])
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (W, H), borderValue=0)
    mask = cv2.warpPerspective(np.full_like(img, 255), M, (W, H), borderValue=0)
    out = np.where(mask > 0, warped, canvas)
    out = cv2.resize(out, (out_w, int(out_w * H / W)), interpolation=cv2.INTER_AREA)
    return out


def warp(img, amp_mm, rng):
    """Smooth non-linear displacement (paper curvature, lens distortion) of up to amp_mm."""
    h, w = img.shape
    amp = amp_mm * K
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fx, fy = rng.uniform(0.5, 1.5), rng.uniform(0.5, 1.5)
    mapx = xx + amp * np.sin(np.pi * yy / h * fy + rng.uniform(0, 3)) * np.sin(np.pi * xx / w)
    mapy = yy + amp * np.sin(np.pi * xx / w * fx + rng.uniform(0, 3))
    return cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR, borderValue=235)


def shadow(img, min_gain):
    """Linear illumination gradient from min_gain (left) to 1 (right)."""
    h, w = img.shape
    grad = np.linspace(min_gain, 1.0, w, dtype=np.float32)[None, :]
    return (img.astype(np.float32) * grad).clip(0, 255).astype(np.uint8)


def noise(img, sigma, rng):
    n = np.random.default_rng(rng.randint(0, 99999)).normal(0, sigma, img.shape)
    return (img.astype(np.float32) + n).clip(0, 255).astype(np.uint8)


def blur(img, sigma):
    return cv2.GaussianBlur(img, (0, 0), sigma) if sigma > 0 else img


def jpeg(img, quality):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    return cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)


def resample(img, dpi):
    f = dpi / DPI
    return cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)


def occlude_markers(img, ids):
    out = img.copy()
    for mid in ids:
        x, y = L.MARKERS[mid]
        cv2.rectangle(out, p(x - 1, y - 1), p(x + L.MARKER + 1, y + L.MARKER + 1), 255, -1)
    return out


def realistic(img, rng, upside_down=False):
    """Moderate mixture of defects, as in examtool.simulacion.distorsionar."""
    from examtool.simulacion import distorsionar
    return distorsionar(img, rng, invertir=upside_down)
