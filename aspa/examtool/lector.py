# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lectura óptica de las hojas de respuesta escaneadas.

Pasos para cada página:
 1. Localizar los 4 marcadores ArUco y calcular la homografía imagen -> plantilla.
    (Corrige giro, inclinación, escala y perspectiva; también hojas escaneadas del revés.)
 2. Enderezar la página a una resolución fija (S píxeles por mm).
 3. Leer el QR (código de examen, modelo y copia).
 4. Afinar la posición de cada bloque de casillas buscando su borde impreso.
 5. Medir la fracción de tinta en el interior de cada casilla y clasificarla.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from . import layout as L

S = 8  # píxeles por mm en la imagen enderezada
S_VISTA = 5  # resolución de la imagen guardada para la revisión
EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}

_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


def _detector():
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    params.adaptiveThreshWinSizeMax = 53
    return cv2.aruco.ArucoDetector(_DICT, params)


# ------------------------------------------------------------------ carga de páginas

def paginas_de(ruta: Path):
    """Genera (sufijo, imagen_gris) para cada página de una imagen o PDF."""
    ruta = Path(ruta)
    ext = ruta.suffix.lower()
    if ext == ".pdf":
        try:
            import pymupdf as fitz
        except ImportError:  # versiones antiguas
            import fitz
        with fitz.open(ruta) as doc:
            for i, pag in enumerate(doc):
                pix = pag.get_pixmap(dpi=220, colorspace=fitz.csGRAY)
                img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
                yield f"p{i + 1}", img.copy()
    elif ext in EXT_IMAGEN:
        datos = np.fromfile(str(ruta), np.uint8)  # admite rutas con acentos en Windows
        img = cv2.imdecode(datos, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"No se puede abrir la imagen {ruta.name}")
        yield "", img


# ------------------------------------------------------------------ geometría

def _homografia(gris):
    det = _detector()
    esquinas, ids, _ = det.detectMarkers(gris)
    if ids is None or len(ids) < 3:
        # segundo intento con contraste realzado (fotocopias claras, escáner oscuro)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        esquinas, ids, _ = det.detectMarkers(clahe.apply(gris))
    if ids is None:
        return None, 0
    src, dst = [], []
    vistos = set()
    for c, i in zip(esquinas, ids.flatten()):
        i = int(i)
        if i not in L.MARKERS or i in vistos:
            continue
        vistos.add(i)
        src.extend(c.reshape(4, 2).tolist())
        dst.extend([(x * S, y * S) for x, y in L.marker_corners(i)])
    if len(vistos) < 3:
        return None, len(vistos)
    H, _ = cv2.findHomography(np.float32(src), np.float32(dst), cv2.RANSAC, 4.0)
    return H, len(vistos)


def _px(v: float) -> int:
    return int(round(v * S))


# ------------------------------------------------------------------ localización de casillas
#
# Las cuatro esquinas corrigen giro y perspectiva, pero no la curvatura del papel ni la
# distorsión de la lente de un móvil, que puede desplazar un bloque 1-2 mm. Por eso, tras
# enderezar, se buscan las casillas impresas reales y cada bloque se ajusta a ellas.

FONDO_MM = 7.0     # tamaño del filtro que estima la iluminación del papel
TINTA = 0.66       # un píxel es tinta si es más oscuro que el 66 % del papel de alrededor
MARGEN_MM = 1.05   # se mide el interior de la casilla dejando este margen respecto al borde


def _mascara_tinta(ender):
    """Iguala la iluminación (sombras del móvil, escáner irregular) y devuelve la máscara de tinta."""
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (_px(FONDO_MM), _px(FONDO_MM)))
    fondo = cv2.morphologyEx(ender, cv2.MORPH_CLOSE, k)
    fondo = cv2.GaussianBlur(fondo, (0, 0), _px(2.0))
    norm = cv2.divide(ender, np.maximum(fondo, 1), scale=255)
    return (norm < 255 * TINTA).astype(np.uint8), norm


def _centros_casillas(tinta):
    """Centros (en píxeles) de los cuadrados del tamaño de una casilla que aparecen impresos."""
    cnts, _ = cv2.findContours(tinta, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    lo, hi = L.BOX * 0.72 * S, L.BOX * 1.35 * S
    out = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if lo <= w <= hi and lo <= h <= hi and 0.8 < w / h < 1.25:
            out.append((x + w / 2, y + h / 2))
    return np.array(out, np.float32).reshape(-1, 2)


def _vecino(puntos, detectados, radio):
    """Para cada punto, índice del detectado más cercano (o -1 si está más lejos que radio)."""
    if len(detectados) == 0:
        return np.full(len(puntos), -1), np.full(len(puntos), np.inf)
    d = np.linalg.norm(puntos[:, None, :] - detectados[None, :, :], axis=2)
    idx = d.argmin(axis=1)
    dist = d[np.arange(len(puntos)), idx]
    return np.where(dist <= radio, idx, -1), dist


def _ajustar_bloque(esperados_mm, detectados):
    """Ajusta un bloque de casillas a las casillas realmente impresas.

    Devuelve (centros en píxeles, nº de casillas encontradas).
    """
    exp = np.asarray(esperados_mm, np.float32) * S
    pred = exp.copy()
    if len(detectados) == 0:
        return pred, 0
    # 1) desplazamiento global aproximado del bloque
    idx, dist = _vecino(pred, detectados, 2.6 * S)
    ok = idx >= 0
    if ok.sum() >= 4:
        pred = pred + np.median(detectados[idx[ok]] - pred[ok], axis=0)
    # 2) transformación afín del bloque (traslación, giro, escala, cizalla) con RANSAC
    idx, _ = _vecino(pred, detectados, 1.6 * S)
    ok = idx >= 0
    if ok.sum() >= 6:
        M, _ = cv2.estimateAffine2D(exp[ok], detectados[idx[ok]], method=cv2.RANSAC,
                                    ransacReprojThreshold=0.5 * S)
        if M is not None:
            pred = exp @ M[:, :2].T + M[:, 2]
    # 3) cada casilla se ajusta a la impresa más cercana si está muy cerca
    idx, _ = _vecino(pred, detectados, 0.8 * S)
    final = np.where((idx >= 0)[:, None], detectados[np.maximum(idx, 0)], pred)
    return final, int((idx >= 0).sum())


def _ratio(tinta, centro):
    h = max(int(round((L.BOX / 2 - MARGEN_MM) * S)), 2)
    cx, cy = int(round(centro[0])), int(round(centro[1]))
    sub = tinta[max(cy - h, 0):cy + h, max(cx - h, 0):cx + h]
    return float(sub.mean()) if sub.size else 0.0


# ------------------------------------------------------------------ QR

def _leer_qr(enderezada, gris_original):
    qr = cv2.QRCodeDetector()
    m = 3
    x0, y0 = _px(L.QR_X - m), _px(L.QR_Y - m)
    x1, y1 = _px(L.QR_X + L.QR_SIZE + m), _px(L.QR_Y + L.QR_SIZE + m)
    recorte = enderezada[max(y0, 0):y1, max(x0, 0):x1]
    intentos = [recorte, cv2.resize(recorte, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)]
    _, bn = cv2.threshold(recorte, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    intentos.append(cv2.resize(bn, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST))
    for img in intentos:
        try:
            txt, _, _ = qr.detectAndDecode(img)
        except cv2.error:
            txt = ""
        if txt:
            return txt
    try:
        txt, _, _ = qr.detectAndDecode(gris_original)
        return txt or ""
    except cv2.error:
        return ""


def interpretar_qr(txt: str):
    partes = (txt or "").split(";")
    if len(partes) >= 4 and partes[0] == "EX1":
        try:
            return {"codigo": partes[1], "modelo": int(partes[2]), "copia": int(partes[3]),
                    "alumno": partes[4] if len(partes) > 4 else ""}
        except ValueError:
            return None
    return None


# ------------------------------------------------------------------ lectura completa

def leer_pagina(gris, umbral_marca=0.11, umbral_duda=0.04, guardar_vista: Path | None = None):
    res = {"ok": False, "error": "", "marcadores": 0}
    if float(np.mean(gris < 128)) < 0.004:
        res.update(error="Página en blanco", error_k="Página en blanco", vacia=True)
        return res
    H, n = _homografia(gris)
    res["marcadores"] = n
    if H is None and n == 0:
        res.update(error="Sin marcadores: no es una hoja de respuestas (se ignora)",
                   error_k="Sin marcadores: no es una hoja de respuestas (se ignora)", vacia=True)
        return res
    if H is None:
        clave = ("Solo se han encontrado {n} de los 4 marcadores de las esquinas. "
                 "¿Está la hoja recortada, doblada o tapada al escanear?")
        res.update(error=clave.format(n=n), error_k=clave, error_p={"n": n})
        return res
    W, Hh = _px(L.PAGE_W), _px(L.PAGE_H)
    ender = cv2.warpPerspective(gris, H, (W, Hh), flags=cv2.INTER_AREA, borderValue=255)

    tinta, norm = _mascara_tinta(ender)
    detectados = _centros_casillas(tinta)

    # QR
    txt = _leer_qr(ender, gris)
    res["qr_texto"] = txt
    res["qr"] = interpretar_qr(txt)

    # Identificación (un bloque) y respuestas (un bloque por columna de 10 preguntas)
    exp_id = [(L.id_box(c, d).cx, L.id_box(c, d).cy) for c in range(L.ID_COLS) for d in range(10)]
    cen_id, enc_id = _ajustar_bloque(exp_id, detectados)
    cen_resp = np.zeros((L.MAX_PREGUNTAS * 5, 2), np.float32)
    encontradas = enc_id
    for colq in range(3):
        qs = range(colq * 10, colq * 10 + 10)
        exp = [(L.ans_box(q, k).cx, L.ans_box(q, k).cy) for q in qs for k in range(5)]
        cen, enc = _ajustar_bloque(exp, detectados)
        cen_resp[colq * 50:(colq + 1) * 50] = cen
        encontradas += enc

    ratios_id = [[round(_ratio(tinta, cen_id[c * 10 + d]), 3) for d in range(10)] for c in range(L.ID_COLS)]
    ratios_resp = [[round(_ratio(tinta, cen_resp[q * 5 + k]), 3) for k in range(5)]
                   for q in range(L.MAX_PREGUNTAS)]

    # Umbrales adaptados a la hoja: si las casillas vacías ya dan algo de «tinta»
    # (borde engordado, papel gris), se suben en la misma medida.
    impresas = _vecino(cen_resp, detectados, 0.8 * S)[0] >= 0
    planos = np.array(ratios_resp, np.float32).reshape(-1)
    base = float(np.median(planos[impresas])) if impresas.sum() >= 10 else 0.0
    base_id = float(np.median(np.array(ratios_id).reshape(-1)))
    u_marca, u_duda = max(umbral_marca, base + 0.10), max(umbral_duda, base + 0.04)
    ui_marca, ui_duda = max(umbral_marca, base_id + 0.10), max(umbral_duda, base_id + 0.04)
    res["umbrales"] = {"marca": round(u_marca, 3), "duda": round(u_duda, 3),
                       "marca_id": round(ui_marca, 3), "base": round(base, 3)}
    res["casillas_encontradas"] = encontradas
    res["centros"] = {
        "id": [[[round(float(v) / S, 2) for v in cen_id[c * 10 + d]] for d in range(10)]
               for c in range(L.ID_COLS)],
        "resp": [[[round(float(v) / S, 2) for v in cen_resp[q * 5 + k]] for k in range(5)]
                 for q in range(L.MAX_PREGUNTAS)],
    }

    # Interpretación
    cols, dudas_id = [], []
    for c, rs in enumerate(ratios_id):
        marc = [d for d, r in enumerate(rs) if r >= ui_marca]
        dud = [d for d, r in enumerate(rs) if ui_duda <= r < ui_marca]
        if len(marc) == 1:
            cols.append(str(marc[0]))
        elif len(marc) > 1:
            cols.append("?")
            dudas_id.append(c)
        elif len(dud) == 1:
            cols.append(str(dud[0]))
            dudas_id.append(c)
        else:
            cols.append("")
    while cols and cols[-1] == "":
        cols.pop()
    while cols and cols[0] == "":
        cols.pop(0)
    res["id_leido"] = "".join(c if c else "?" for c in cols)
    res["id_dudas"] = dudas_id

    respuestas = []
    for rs in ratios_resp:
        marcadas = "".join(L.LETRAS[k] for k in range(4) if rs[k] >= u_marca)
        dudas = "".join(L.LETRAS[k] for k in range(4) if u_duda <= rs[k] < u_marca)
        respuestas.append({"m": marcadas, "anular": rs[4] >= u_marca,
                           "dudas": dudas + ("X" if u_duda <= rs[4] < u_marca else "")})
    res.update(ok=True, respuestas=respuestas, ratios={"id": ratios_id, "resp": ratios_resp})

    if guardar_vista:
        f = S_VISTA / S
        vista = cv2.resize(ender, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", vista, [cv2.IMWRITE_JPEG_QUALITY, 82])
        Path(guardar_vista).parent.mkdir(parents=True, exist_ok=True)
        buf.tofile(str(guardar_vista))
    return res


# Errores que se guardan en lecturas.json en español y se traducen al mostrarlos
ERRORES = (
    "Página en blanco",
    "Sin marcadores: no es una hoja de respuestas (se ignora)",
    "Solo se han encontrado {n} de los 4 marcadores de las esquinas. "
    "¿Está la hoja recortada, doblada o tapada al escanear?",
    "No se pudo leer: {e}",
    "No se pudo leer",
)


def texto_error(lectura: dict) -> str:
    """El error de una lectura en el idioma actual (se guarda la clave en español)."""
    from .i18n import t
    if lectura.get("error_k"):
        return t(lectura["error_k"], **(lectura.get("error_p") or {}))
    return t(lectura.get("error") or "No se pudo leer")


def leer_proyecto(proyecto, forzar=False, progreso=None):
    """Lee todos los escaneos del proyecto que aún no se hayan leído."""
    cfg = proyecto.config()
    lect = {} if forzar else proyecto.lecturas()
    carpeta = proyecto.ruta("escaneos")
    ficheros = sorted(p for p in carpeta.glob("*") if p.is_file()) if carpeta.exists() else []
    nuevas = 0
    for i, f in enumerate(ficheros):
        try:
            for suf, gris in paginas_de(f):
                clave = f.name + (f"#{suf}" if suf else "")
                if clave in lect:
                    continue
                vista = proyecto.ruta("procesadas") / (clave.replace("#", "_") + ".jpg")
                r = leer_pagina(gris, cfg["umbral_marca"], cfg["umbral_duda"], vista)
                r["archivo"] = f.name
                r["clave"] = clave
                if r.get("ok"):
                    r["vista"] = vista.name
                lect[clave] = r
                nuevas += 1
        except Exception as e:  # un fichero corrupto no debe parar el resto
            lect[f.name] = {"ok": False, "error": f"No se pudo leer: {e}", "error_k": "No se pudo leer: {e}",
                            "error_p": {"e": str(e)}, "archivo": f.name,
                            "clave": f.name}
        if progreso:
            progreso(i + 1, len(ficheros))
    proyecto.guardar_lecturas(lect)
    return nuevas
