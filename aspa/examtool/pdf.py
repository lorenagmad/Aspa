# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generación de los exámenes en PDF (hoja de respuestas + preguntas)."""
from __future__ import annotations

import io
from functools import lru_cache
from xml.sax.saxutils import escape

import cv2
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

from . import layout as L
from . import i18n
from .i18n import t
from .proyecto import cabecera_examen

PW, PH = A4
GRIS = colors.Color(0.45, 0.45, 0.45)
GRIS_CLARO = colors.Color(0.75, 0.75, 0.75)


def Y(y_mm: float) -> float:
    """mm desde arriba -> puntos desde abajo (sistema de ReportLab)."""
    return PH - y_mm * mm


@lru_cache(maxsize=8)
def _bits_marcador(mid: int):
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    img = cv2.aruco.generateImageMarker(d, mid, 6)
    return (img > 127).tolist()


def payload_qr(codigo: str, modelo: int, copia: int, alumno: str = "") -> str:
    """Contenido del QR. Formato: EX1;codigo;modelo;copia[;alumno]"""
    s = f"EX1;{codigo};{modelo};{copia}"
    return s + (f";{alumno}" if alumno else "")


# ------------------------------------------------------------------- hoja de respuestas

def dibujar_hoja(c, cfg: dict, codigo: str, modelo_idx: int, modelo_nombre: str,
                 copia: int, n_preg: int, alumno: dict | None = None, info: dict | None = None):
    c.saveState()
    # Marcadores de posición
    for mid, (x, y) in L.MARKERS.items():
        bits = _bits_marcador(mid)
        cell = L.MARKER / 6
        c.setFillColor(colors.black)
        for r, fila in enumerate(bits):
            for k, blanco in enumerate(fila):
                if not blanco:
                    c.rect((x + k * cell) * mm, Y(y + (r + 1) * cell), cell * mm + 0.05,
                           cell * mm + 0.05, stroke=0, fill=1)

    # QR
    qr = QrCodeWidget(payload_qr(codigo, modelo_idx, copia, (alumno or {}).get("documento", "")),
                      barLevel="M", barBorder=1)
    b = qr.getBounds()
    w, h = b[2] - b[0], b[3] - b[1]
    s = L.QR_SIZE * mm
    dr = Drawing(s, s, transform=[s / w, 0, 0, s / h, 0, 0])
    dr.add(qr)
    renderPDF.draw(dr, c, L.QR_X * mm, Y(L.QR_Y + L.QR_SIZE))

    # Cabecera de la hoja
    x0 = L.LEFT + L.MARKER + 4
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10.5)
    principal, secundaria = cabecera_examen(cfg)
    texto, tam = _ajustar(cfg, "Helvetica-Bold", 10.5, 8.5, (L.QR_X - 3 - x0) * mm)
    c.setFont("Helvetica-Bold", tam)
    c.drawString(x0 * mm, Y(L.TOP + 4.2), texto)
    c.setFont("Helvetica", 8.5)
    if secundaria:
        c.drawString(x0 * mm, Y(L.TOP + 8.6), _recorta(secundaria, 80))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x0 * mm, Y(L.TOP + 15.5), t("Modelo {m}", m=modelo_nombre))
    c.setFont("Helvetica", 8.5)
    c.drawString((x0 + 30) * mm, Y(L.TOP + 15.5), t("Copia nº {n}", n=f"{copia:04d}") + "     " + t("Código {c}", c=codigo))
    if alumno:
        _ficha_alumno(c, alumno, info or {})
    else:
        _casillas_documento(c)
    _bloque_respuestas(c, n_preg)
    _aclaraciones(c)
    c.restoreState()


def _ficha_alumno(c, alumno: dict, info: dict):
    """Examen personalizado: en lugar de las casillas del documento, el alumno impreso."""
    x0, x1 = L.ID_X0 - 6, L.ID_X0 + L.ID_COLS * L.ID_COL_P
    y0, y1 = L.GRID_Y - 3, L.row_y(9) + L.BOX
    c.setStrokeColor(GRIS)
    c.setLineWidth(0.8)
    c.roundRect(x0 * mm, Y(y1), (x1 - x0) * mm, (y1 - y0) * mm, 2 * mm, stroke=1, fill=0)
    ancho = (x1 - x0 - 6) * mm
    est_n = ParagraphStyle("n", fontName="Helvetica-Bold", fontSize=13, leading=15.5)
    est_t = ParagraphStyle("t", fontName="Helvetica", fontSize=9, leading=12)
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 7.5)
    c.drawString((x0 + 3) * mm, Y(y0 + 5), t("ALUMNO/A"))
    p = Paragraph(escape(alumno.get("nombre", "")), est_n)
    _, h = p.wrap(ancho, 40 * mm)
    p.drawOn(c, (x0 + 3) * mm, Y(y0 + 7) - h)
    yy = y0 + 7 + h / mm + 6
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 7.5)
    c.drawString((x0 + 3) * mm, Y(yy), t("DOCUMENTO"))
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawString((x0 + 3) * mm, Y(yy + 5), alumno.get("documento", ""))
    if info.get("total"):
        sup, total = len(info.get("superadas") or []), info["total"]
        texto = (t("Ha superado en clase <b>{s}</b> de las {total} preguntas, que ya cuentan como "
                   "correctas.<br/>Este examen tiene <b>{n}</b> preguntas.", s=sup, total=total, n=total - sup)
                 if sup else t("Este examen tiene las <b>{total}</b> preguntas.", total=total))
        q = Paragraph(texto, est_t)
        q.wrap(ancho, 30 * mm)
        q.drawOn(c, (x0 + 3) * mm, Y(y1 - 3))


def _casillas_documento(c):
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(L.ID_X0 * mm, Y(L.GRID_Y - 1.4), t("Documento de identidad (solo números)"))
    c.setLineWidth(0.6)
    c.setStrokeColor(colors.black)
    for col in range(L.ID_COLS):
        r = L.id_write_box(col)
        c.setStrokeColor(GRIS)
        c.rect(r.x * mm, Y(r.y + r.h), r.w * mm, r.h * mm, stroke=1, fill=0)
    c.setStrokeColor(colors.black)
    c.setFont("Helvetica", 7)
    for d in range(10):
        ry = L.row_y(d)
        c.setFillColor(GRIS)
        c.drawRightString((L.ID_X0 - 1.2) * mm, Y(ry + L.BOX - 1.0), str(d))
        c.setFillColor(colors.black)
        for col in range(L.ID_COLS):
            _caja(c, L.id_box(col, d))
    # números de columna debajo, para que el alumno se oriente
    c.setFont("Helvetica", 5.5)
    c.setFillColor(GRIS)
    for col in range(L.ID_COLS):
        bx = L.id_box(col, 9)
        c.drawCentredString(bx.cx * mm, Y(bx.y + bx.h + 2.4), str(col + 1))



def _bloque_respuestas(c, n_preg: int):
    c.setFillColor(colors.black)
    ncols = (n_preg + 9) // 10
    for colq in range(ncols):
        q0 = colq * 10
        c.setFont("Helvetica-Bold", 7)
        for k in range(4):
            bx = L.ans_box(q0, k)
            c.drawCentredString(bx.cx * mm, Y(bx.y - 1.3), L.LETRAS[k])
        bx = L.ans_box(q0, 4)
        c.setFont("Helvetica", 5.6)
        c.drawCentredString(bx.cx * mm, Y(bx.y - 1.3), t("Anular"))
        # separador discontinuo entre opciones y anular
        d_box = L.ans_box(q0, 3)
        xs = (d_box.x + d_box.w + bx.x) / 2
        c.setStrokeColor(GRIS_CLARO)
        c.setDash(1, 1.5)
        c.setLineWidth(0.4)
        last = L.ans_box(min(q0 + 9, n_preg - 1), 0)
        c.line(xs * mm, Y(L.ROWS_Y0 - 0.5), xs * mm, Y(last.y + last.h + 0.5))
        c.setDash()
        c.setStrokeColor(colors.black)
    for q in range(n_preg):
        bx = L.ans_box(q, 0)
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString((bx.x - 1.2) * mm, Y(bx.y + L.BOX - 0.9), str(q + 1))
        for k in range(5):
            _caja(c, L.ans_box(q, k), anular=(k == 4))



def _aclaraciones(c):
    c.setLineWidth(0.6)
    c.setStrokeColor(GRIS)
    c.rect(L.LEFT * mm, Y(L.ACLA_Y + L.ACLA_H), (L.RIGHT - L.LEFT) * mm, L.ACLA_H * mm)
    c.setFont("Helvetica", 7)
    c.setFillColor(GRIS)
    c.drawString((L.LEFT + 1.5) * mm, Y(L.ACLA_Y + 3.2),
                 t("Aclaraciones: indique aquí qué respuesta quiere en las preguntas marcadas como «Anular»."))


def _caja(c, r: L.Rect, anular=False):
    c.setLineWidth(0.7 if anular else 0.6)
    c.rect(r.x * mm, Y(r.y + r.h), r.w * mm, r.h * mm, stroke=1, fill=0)


def _ajustar(cfg: dict, fuente: str, tam: float, minimo: float, ancho: float) -> tuple[str, float]:
    """«Asignatura · Título» ajustado a un ancho: primero se reduce la letra y, si aun así
    no cabe, se abrevia la asignatura (el título del examen se conserva siempre)."""
    asig, tit = cfg.get("asignatura", "").strip(), cfg.get("titulo", "").strip()
    texto = cabecera_examen(cfg)[0]
    while tam > minimo and stringWidth(texto, fuente, tam) > ancho:
        tam -= 0.5
    while asig and stringWidth(texto, fuente, tam) > ancho:
        asig = asig[:-1]
        texto = f"{asig.rstrip()}… · {tit}" if asig else tit
    while len(texto) > 8 and stringWidth(texto, fuente, tam) > ancho:
        texto = texto[:-2] + "…"
    return texto, tam


def _recorta(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - 1] + "…"


# ------------------------------------------------------------------- documento completo

def _estilos(cfg):
    tp, tr = float(cfg.get("tam_pregunta", 10)), float(cfg.get("tam_respuesta", 9.5))
    return {
        "preg": ParagraphStyle("preg", fontName="Helvetica-Bold", fontSize=tp, leading=tp * 1.2,
                               leftIndent=14, firstLineIndent=-14, spaceBefore=6, spaceAfter=1.5),
        "resp": ParagraphStyle("resp", fontName="Helvetica", fontSize=tr, leading=tr * 1.2,
                               leftIndent=26, firstLineIndent=-11),
        "desc": ParagraphStyle("desc", fontName="Helvetica", fontSize=9.5, leading=12),
        "tit": ParagraphStyle("tit", fontName="Helvetica-Bold", fontSize=13, leading=16),
    }


def _pdf_copia(proy_cfg: dict, descripcion: str, gen: dict, midx: int, copia: int,
               imagenes: list | None = None) -> bytes:
    buf = io.BytesIO()
    est = _estilos(proy_cfg)
    modelo = gen["modelos"][midx]
    alumno = modelo.get("alumno")
    info = {"total": modelo.get("total"), "superadas": modelo.get("superadas")} if "total" in modelo else {}
    n_preg = len(modelo["preguntas"])
    margen = 12 * mm
    ancho = PW - 2 * margen
    gap = 7 * mm
    colw = (ancho - gap) / 2

    # Altura de la cabecera de la primera página (título + datos + descripción)
    tit_y = L.ACLA_Y + L.ACLA_H + 4
    desc_p = Paragraph(escape(descripcion), est["desc"])
    _, dh = desc_p.wrap(ancho, PH)
    datos_h = 12 * mm
    top_preg = Y(tit_y) - 18 - datos_h - 4 - dh - 8

    principal, secundaria = cabecera_examen(proy_cfg)

    def primera(c, doc):
        dibujar_hoja(c, proy_cfg, gen["codigo"], midx, modelo["nombre"], copia, n_preg, alumno, info)
        # el título se reduce (hasta 9 pt) para no pisar la convocatoria a la derecha
        sec = _recorta(secundaria, 55)
        libre = ancho - (stringWidth(sec, "Helvetica", 9.5) + 6 * mm if sec else 0)
        texto, tam = _ajustar(proy_cfg, "Helvetica-Bold", 13.0, 9.5, libre)
        c.setFont("Helvetica-Bold", tam)
        c.drawString(margen, Y(tit_y) - 13, texto)
        if sec:
            c.setFont("Helvetica", 9.5)
            c.drawRightString(PW - margen, Y(tit_y) - 13, sec)
        tabla = Table([[t("Apellidos y nombre"), t("Documento"), t("Fecha")],
                   [(alumno or {}).get("nombre", ""), (alumno or {}).get("documento", ""), ""]],
                  colWidths=[ancho * 0.52, ancho * 0.26, ancho * 0.22],
                  rowHeights=[4.2 * mm, datos_h - 4.2 * mm])
        tabla.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
            ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.black),
            ("FONT", (0, 0), (-1, 0), "Helvetica", 7),
            ("FONT", (0, 1), (-1, 1), "Helvetica-Bold", 10),
            ("TEXTCOLOR", (0, 0), (-1, 0), GRIS),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
        ]))
        tabla.wrapOn(c, ancho, datos_h)
        tabla.drawOn(c, margen, Y(tit_y) - 18 - datos_h)
        desc_p.drawOn(c, margen, Y(tit_y) - 18 - datos_h - 4 - dh)
        c.setStrokeColor(GRIS_CLARO)
        c.setLineWidth(0.5)
        c.line(margen, top_preg + 4, PW - margen, top_preg + 4)
        pie(c, doc)

    def pie(c, doc):
        c.setFont("Helvetica", 7)
        c.setFillColor(GRIS)
        c.drawCentredString(PW / 2, 7 * mm,
                            f"{_recorta(principal, 60)}  ·  " + t("Modelo {m}", m=modelo["nombre"]) + "  ·  "
                            + t("Copia {n}", n=f"{copia:04d}") + "  ·  " + t("Página {n}", n=doc.page))

    f1 = [Frame(margen, 12 * mm, colw, top_preg - 12 * mm, id="a1", leftPadding=0, rightPadding=0),
          Frame(margen + colw + gap, 12 * mm, colw, top_preg - 12 * mm, id="b1",
                leftPadding=0, rightPadding=0)]
    f2 = [Frame(margen, 12 * mm, colw, PH - 24 * mm, id="a2", leftPadding=0, rightPadding=0),
          Frame(margen + colw + gap, 12 * mm, colw, PH - 24 * mm, id="b2",
                leftPadding=0, rightPadding=0)]
    f3 = [Frame(margen, 12 * mm, ancho, PH - 24 * mm, id="img", leftPadding=0, rightPadding=0)]
    doc = BaseDocTemplate(buf, pagesize=A4, title=principal, author="Aspa")
    doc.addPageTemplates([PageTemplate("primera", f1, onPage=primera),
                          PageTemplate("resto", f2, onPage=pie),
                          PageTemplate("imagenes", f3, onPage=pie)])

    banco = gen["banco"]
    story = [NextPageTemplate("resto")]
    for i, item in enumerate(modelo["preguntas"], 1):
        q = banco[item["id"]]
        partes = [Paragraph(f"{i}.- {escape(q['texto'])}", est["preg"])]
        for pos, orig in enumerate(item["perm"]):
            if orig is None:
                continue
            partes.append(Paragraph(f"{L.LETRAS[pos]}.&nbsp;&nbsp;{escape(q['opciones'][orig])}",
                                    est["resp"]))
        story.append(KeepTogether(partes))
    story.append(Spacer(1, 1))
    if imagenes:
        story += [NextPageTemplate("imagenes"), PageBreak()] + _flujo_imagenes(imagenes, ancho, est)
    doc.build(story)
    return buf.getvalue()


def _flujo_imagenes(imagenes: list, ancho: float, est) -> list:
    """Imágenes al final del examen, cada una ajustada al ancho de la página, con su pie."""
    pie = ParagraphStyle("pie", fontName="Helvetica", fontSize=14, leading=17, alignment=1)
    out = []
    alto_max = 205 * mm
    for ruta, texto in imagenes:
        try:
            ir = ImageReader(str(ruta))
            w, h = ir.getSize()
        except Exception:  # noqa: BLE001 — una imagen dañada no debe impedir generar el examen
            continue
        esc = min(ancho / w, alto_max / h)
        partes = [Image(str(ruta), width=w * esc, height=h * esc)]
        if texto:
            partes += [Spacer(1, 3), Paragraph(escape(texto), pie)]
        partes.append(Spacer(1, 9))
        out.append(KeepTogether(partes))
    return out


def rutas_imagenes(proyecto) -> list:
    cfg = proyecto.config()
    out = []
    for im in cfg.get("imagenes") or []:
        r = proyecto.ruta("imagenes") / im["fichero"]
        if r.exists():
            out.append((r, im.get("pie", "")))
    return out


def generar_pdf(proyecto, destino=None, doble_cara=True) -> str:
    """Genera examenes.pdf en el idioma del examen (puede ser distinto del de Aspa)."""
    with i18n.en(proyecto.config().get("idioma_examen")):
        return _generar_pdf(proyecto, destino, doble_cara)


def _generar_pdf(proyecto, destino=None, doble_cara=True) -> str:
    """Genera examenes.pdf con todas las copias, repartiendo modelos A, B, C, D, A, B...
    Así, al repartir en orden, alumnos contiguos reciben modelos distintos."""
    cfg = proyecto.config()
    gen = proyecto.generado()
    if not gen:
        raise ValueError(t("Primero hay que generar los modelos."))
    desc = proyecto.descripcion()
    desc_pers = proyecto.descripcion(personalizado=True)
    imagenes = rutas_imagenes(proyecto)
    salida = fitz.open()
    nmod = len(gen["modelos"])
    impresion = gen.get("impresion") or [(c - 1) % nmod for c in range(1, int(gen["copias"]) + 1)]
    for copia, midx in enumerate(impresion, 1):
        d = desc_pers if gen["modelos"][midx].get("alumno") else desc
        parte = fitz.open(stream=_pdf_copia(cfg, d, gen, midx, copia, imagenes), filetype="pdf")
        salida.insert_pdf(parte)
        if doble_cara and parte.page_count % 2:
            salida.new_page(width=PW, height=PH)
    destino = destino or proyecto.ruta("examenes.pdf")
    salida.save(str(destino), deflate=True, garbage=3)
    return str(destino)


def etiqueta_modelo(m: dict, largo: int = 60) -> str:
    """«A» en exámenes por modelos; «A · Apellidos, Nombre» o «A · reserva» en personalizados."""
    if m.get("alumno"):
        return _recorta(f"{m['nombre']} · {m['alumno'].get('nombre', '')}", largo)
    if m.get("reserva"):
        return f"{m['nombre']} · " + t("reserva")
    return m["nombre"] if largo < 30 else t("Modelo {m}", m=m["nombre"])


def generar_soluciones(proyecto, destino=None) -> str:
    with i18n.en(proyecto.config().get("idioma_examen")):
        return _generar_soluciones(proyecto, destino)


def _generar_soluciones(proyecto, destino=None) -> str:
    """PDF para el profesor con la clave de cada modelo."""
    gen = proyecto.generado()
    cfg = proyecto.config()
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, title=t("Soluciones"))
    doc.addPageTemplates([PageTemplate("p", [Frame(15 * mm, 15 * mm, PW - 30 * mm, PH - 30 * mm)])])
    est = _estilos(cfg)
    story = [Paragraph(escape(t("Soluciones") + " · " + " · ".join(x for x in cabecera_examen(cfg) if x)
                              + " · " + t("código {c}", c=gen["codigo"])), est["tit"]),
             Spacer(1, 6)]
    n = max([gen["n_preguntas"]] + [len(m["preguntas"]) for m in gen["modelos"]])
    cab = [t("Examen")] + [str(i) for i in range(1, n + 1)]
    filas = [cab]
    for m in gen["modelos"]:
        claves = [p["correctas"] for p in m["preguntas"]]
        filas.append([etiqueta_modelo(m, 24)] + claves + [""] * (n - len(claves)))
    primera = 42 * mm if gen.get("tipo") == "personalizado" else 16 * mm
    cw = [primera] + [(PW - 30 * mm - primera) / n] * n
    tabla = Table(filas, colWidths=cw)
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONT", (0, 0), (-1, -1), "Helvetica", 7.5),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.5),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story += [tabla, Spacer(1, 10)]
    for m in gen["modelos"]:
        story.append(Paragraph(escape(etiqueta_modelo(m) + ": " + t("correspondencia con el banco")), est["preg"]))
        txt = "; ".join(f"{i}→{p['id']} ({p['correctas']})" for i, p in enumerate(m["preguntas"], 1))
        story.append(Paragraph(escape(txt), est["resp"]))
    doc.build(story)
    destino = destino or proyecto.ruta("soluciones.pdf")
    with open(destino, "wb") as f:
        f.write(buf.getvalue())
    return str(destino)


def vista_previa_png(pdf_path, pagina=0, zoom=1.5) -> bytes:
    with fitz.open(pdf_path) as d:
        pix = d[pagina].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        return pix.tobytes("png")
