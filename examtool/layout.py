# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Geometría de la hoja de respuestas.

Todas las medidas en milímetros, con origen en la esquina superior izquierda
de un A4 vertical (y crece hacia abajo). Este módulo es la única fuente de verdad:
lo usan tanto el generador de PDF como el lector óptico, así que cualquier cambio
de diseño se hace aquí y ambos quedan sincronizados.
"""
from dataclasses import dataclass

PAGE_W, PAGE_H = 210.0, 297.0

# Marcadores ArUco (diccionario 4x4_50), ids 0..3 en sentido horario desde arriba-izquierda
MARKER = 9.0
TOP = 10.0
LEFT = 12.0
RIGHT = PAGE_W - 12.0
GRID_Y = 33.0                 # comienzo de la zona de casillas
ROW_P = 5.6                   # separación vertical entre filas
BOX = 4.2                     # lado de cada casilla
ROWS_Y0 = GRID_Y + 9.0        # primera fila de burbujas (DNI y respuestas alineadas)
BOTTOM_MARKER_Y = ROWS_Y0 + 10 * ROW_P + 3.0

MARKERS = {
    0: (LEFT, TOP),
    1: (RIGHT - MARKER, TOP),
    2: (RIGHT - MARKER, BOTTOM_MARKER_Y),
    3: (LEFT, BOTTOM_MARKER_Y),
}
BLOCK_BOTTOM = BOTTOM_MARKER_Y + MARKER

# Código QR (modelo, número de copia, código de examen)
QR_SIZE = 18.0
QR_X = RIGHT - MARKER - 4.0 - QR_SIZE
QR_Y = TOP

# Identificación: 10 columnas x 10 dígitos (0-9)
ID_COLS = 10
ID_X0 = 20.0
ID_COL_P = 5.2
ID_WRITE_Y = GRID_Y           # casillas para escribir a mano (no se leen)
ID_WRITE_H = 7.0

# Respuestas: columnas de 10 preguntas; 4 opciones + casilla de anular separada
ANS_X0 = 79.0
ANS_COL_P = 38.0
ANS_LABEL_W = 6.0
OPT_P = 5.4
ANNUL_GAP = 3.0
MAX_PREGUNTAS = 30
LETRAS = "ABCD"

# Recuadro de aclaraciones
ACLA_Y = BLOCK_BOTTOM + 3.0
ACLA_H = 26.0


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2


def row_y(r: int) -> float:
    return ROWS_Y0 + r * ROW_P


def id_box(col: int, digit: int) -> Rect:
    """Casilla del dígito `digit` (0-9) en la columna `col` (0-9)."""
    x = ID_X0 + col * ID_COL_P + (ID_COL_P - BOX) / 2
    return Rect(x, row_y(digit), BOX, BOX)


def id_write_box(col: int) -> Rect:
    return Rect(ID_X0 + col * ID_COL_P + 0.3, ID_WRITE_Y, ID_COL_P - 0.6, ID_WRITE_H)


def ans_col_x(q: int) -> float:
    return ANS_X0 + (q // 10) * ANS_COL_P


def ans_box(q: int, k: int) -> Rect:
    """Casilla k (0-3 = A-D, 4 = anular) de la pregunta q (0-based)."""
    x0 = ans_col_x(q) + ANS_LABEL_W
    if k == 4:
        x = x0 + 3 * OPT_P + BOX + ANNUL_GAP
    else:
        x = x0 + k * OPT_P
    return Rect(x, row_y(q % 10), BOX, BOX)


def marker_corners(mid: int):
    """Esquinas del marcador en el orden en que las devuelve OpenCV (TL, TR, BR, BL)."""
    x, y = MARKERS[mid]
    return [(x, y), (x + MARKER, y), (x + MARKER, y + MARKER), (x, y + MARKER)]
