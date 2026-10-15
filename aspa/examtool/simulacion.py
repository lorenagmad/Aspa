# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Escaneos simulados: rellena hojas como un alumno y las «escanea» con defectos.

Sirve para probar el lector y para el proyecto de demostración. Escribe las imágenes
en <proyecto>/escaneos y la solución real en <proyecto>/simulacion.json.
"""
import json
import random
import cv2
import numpy as np

from . import layout as L

try:
    import pymupdf as fitz
except ImportError:
    import fitz

DPI = 220
K = DPI / 25.4


def p(x, y):
    return int(round(x * K)), int(round(y * K))


def aspa(img, r, rng, tinta):
    m = rng.uniform(0.3, 0.9)
    j = lambda: rng.uniform(-0.5, 0.5)  # noqa: E731
    g = rng.choice([2, 2, 3, 4])
    cv2.line(img, p(r.x + m + j(), r.y + m + j()), p(r.x + r.w - m + j(), r.y + r.h - m + j()), tinta, g, cv2.LINE_AA)
    cv2.line(img, p(r.x + r.w - m + j(), r.y + m + j()), p(r.x + m + j(), r.y + r.h - m + j()), tinta, g, cv2.LINE_AA)


def relleno(img, r, rng, tinta):
    m = rng.uniform(0.2, 0.6)
    cv2.rectangle(img, p(r.x + m, r.y + m), p(r.x + r.w - m, r.y + r.h - m), tinta, -1)


def visto(img, r, rng, tinta):
    pts = np.array([p(r.x + 0.6, r.cy), p(r.cx - 0.3, r.y + r.h - 0.5), p(r.x + r.w + 0.8, r.y - 0.8)], np.int32)
    cv2.polylines(img, [pts], False, tinta, 3, cv2.LINE_AA)


def marcar(img, r, rng, tinta):
    rng.choices([aspa, relleno, visto], [0.75, 0.15, 0.10])[0](img, r, rng, tinta)


def distorsionar(img, rng, invertir=False):
    h, w = img.shape
    ang = rng.uniform(-4, 4) + (180 if invertir else 0)
    esc = rng.uniform(0.95, 1.02)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, esc)
    M[:, 2] += [rng.uniform(-40, 40), rng.uniform(-40, 40)]
    img = cv2.warpAffine(img, M, (w, h), borderValue=int(rng.uniform(200, 245)))
    d = 0.012 * w
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = src + np.float32([[rng.uniform(-d, d), rng.uniform(-d, d)] for _ in range(4)])
    img = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h), borderValue=230)
    # curvatura del papel / lente del móvil: desplazamiento suave no lineal (hasta ~2 mm)
    amp = rng.uniform(0, 2.0) * K
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fx, fy = rng.uniform(0.5, 1.5), rng.uniform(0.5, 1.5)
    mapx = xx + amp * np.sin(np.pi * yy / h * fy + rng.uniform(0, 3)) * np.sin(np.pi * xx / w)
    mapy = yy + amp * np.sin(np.pi * xx / w * fx + rng.uniform(0, 3))
    img = cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR, borderValue=230)
    # iluminación irregular (sombra de la mano o del móvil)
    grad = np.linspace(rng.uniform(0.75, 1.0), 1.0, w, dtype=np.float32)[None, :]
    img = (img.astype(np.float32) * grad).astype(np.uint8)
    papel = rng.uniform(0.86, 0.98)
    img = (img.astype(np.float32) * papel + rng.uniform(-8, 8))
    img += np.random.default_rng(rng.randint(0, 9999)).normal(0, rng.uniform(2, 7), img.shape)
    img = cv2.GaussianBlur(np.clip(img, 0, 255).astype(np.uint8), (3, 3), rng.uniform(0.3, 1.0))
    return img


def simular(proy, n=12, semilla=3):
    rng = random.Random(semilla)
    gen = proy.generado()
    from .pdf import _pdf_copia
    alumnos = proy.alumnos()
    cfg = proy.config()
    nmod = len(gen["modelos"])
    impresion = gen.get("impresion") or [(c - 1) % nmod for c in range(1, int(gen["copias"]) + 1)]
    salida = proy.ruta("escaneos")
    salida.mkdir(exist_ok=True)
    verdad = {}
    for h in range(n):
        copia = h % len(impresion)
        midx = impresion[copia]
        # primera página de esa copia, generada igual que en el PDF de examen
        hoja = fitz.open(stream=_pdf_copia(cfg, proy.descripcion(), gen, midx, copia + 1), filetype="pdf")
        pix = hoja[0].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
        img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width).copy()
        tinta = int(rng.choice([25, 40, 60, 90, 130]))  # 130 ~ lápiz flojo
        impreso = gen["modelos"][midx].get("alumno")
        al = alumnos[h % len(alumnos)]
        dig = "" if impreso else "".join(ch for ch in al.documento if ch.isdigit())
        for c, ch in enumerate(dig[:10]):
            wb = L.id_write_box(c)
            cv2.putText(img, ch, p(wb.x + 0.6, wb.y + wb.h - 1), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,
                        1.1, tinta, 2, cv2.LINE_AA)
            marcar(img, L.id_box(c, int(ch)), rng, tinta)
        nombre_y = L.ACLA_Y + L.ACLA_H + 4 + 6.4 + 9
        cv2.putText(img, al.nombre[:28], p(15, nombre_y + 9), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.4, tinta, 2)
        respuestas = []
        modelo = gen["modelos"][midx]
        for q, item in enumerate(modelo["preguntas"]):
            u = rng.random()
            if u < 0.10:
                marc = ""
            elif u < 0.60:
                marc = item["correctas"]
            elif u < 0.75:
                marc = "".join(sorted(rng.sample("ABCD", 2)))
            else:
                marc = rng.choice("ABCD")
            anular = rng.random() < 0.05
            for k, letra in enumerate("ABCD"):
                if letra in marc:
                    marcar(img, L.ans_box(q, k), rng, tinta)
            if anular:
                aspa(img, L.ans_box(q, 4), rng, tinta)
                cv2.putText(img, f"{q + 1}. la {rng.choice('ABCD')}", p(16 + 30 * (q % 5), L.ACLA_Y + 10),
                            cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.2, tinta, 2)
            respuestas.append({"m": marc, "anular": anular})
        # garabatos fuera de las casillas, como hacen algunos alumnos
        for _ in range(rng.randint(0, 3)):
            x, y = rng.uniform(80, 190), rng.uniform(36, 40)
            cv2.circle(img, p(x, y), rng.randint(4, 12), tinta, 2)
        img = distorsionar(img, rng, invertir=(h == 3))
        nombre = f"escaneo_{h + 1:02d}.jpg"
        cv2.imwrite(str(salida / nombre), img, [cv2.IMWRITE_JPEG_QUALITY, int(rng.uniform(60, 85))])
        verdad[nombre] = {"modelo": midx, "copia": copia + 1,
                          "documento": impreso["documento"] if impreso else al.documento,
                          "digitos": dig[:10], "respuestas": respuestas, "tinta": tinta}
    proy.ruta("simulacion.json").write_text(json.dumps(verdad, ensure_ascii=False, indent=1), encoding="utf-8")
    return n
