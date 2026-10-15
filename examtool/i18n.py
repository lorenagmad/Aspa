# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Idiomas de Aspa.

El texto de referencia es el español y sirve de clave: en el código y en las plantillas se
escribe ``t("Texto en español")`` (en las plantillas, ``{{ _("Texto en español") }}``). Cada
idioma adicional es un fichero JSON en la carpeta ``idiomas/`` que asocia cada texto español
con su traducción:

    {
      "_nombre": "English",          <- nombre del idioma en su propia lengua
      "_decimal": ".",               <- separador decimal
      "Texto en español": "Text in English",
      "Hay {n} hojas": "There are {n} sheets"
    }

Si falta una traducción se muestra en inglés (y, si tampoco está, en español), nunca un error.
Para añadir un idioma
basta con copiar ``en.json`` con otro nombre (por ejemplo ``fr.json``), traducir los valores y
reiniciar Aspa. ``python herramientas/revisar_traducciones.py fr`` lista lo que falte.

Las páginas de ayuda, por ser texto largo, son plantillas HTML por idioma en
``templates/ayuda/<idioma>/``; si un idioma no las tiene se muestran las inglesas.
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
import json
from functools import lru_cache
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent / "idiomas"
BASE = "es"
NOMBRE_BASE = "Español"
RESPALDO = "en"   # si a un idioma le falta un texto o una ayuda, se usa el inglés (y si no, el español)

_actual: contextvars.ContextVar[str] = contextvars.ContextVar("idioma", default=BASE)


@lru_cache(maxsize=None)
def catalogo(idioma: str) -> dict:
    if idioma == BASE:
        return {}
    f = CARPETA / f"{idioma}.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


def disponibles() -> dict[str, str]:
    """{código: nombre} de los idiomas instalados, el español primero."""
    out = {BASE: NOMBRE_BASE}
    if CARPETA.exists():
        for f in sorted(CARPETA.glob("*.json")):
            try:
                out[f.stem] = catalogo(f.stem).get("_nombre", f.stem)
            except (OSError, ValueError):
                continue
    return out


def valido(idioma: str | None) -> str:
    return idioma if idioma in disponibles() else BASE


def usar(idioma: str):
    """Fija el idioma del contexto actual (cada petición web tiene el suyo)."""
    _actual.set(valido(idioma))


@contextmanager
def en(idioma: str | None):
    """Usa temporalmente otro idioma (p. ej. el del examen mientras se genera su PDF)."""
    token = _actual.set(valido(idioma) if idioma else _actual.get())
    try:
        yield
    finally:
        _actual.reset(token)


def actual() -> str:
    return _actual.get()


def t(texto: str, idioma: str | None = None, **valores) -> str:
    """Traduce un texto. Con valores, rellena los huecos {nombre} después de traducir.

    Ojo: «idioma» es el idioma de la traducción; un hueco del texto no puede llamarse {idioma}."""
    idioma = idioma or _actual.get()
    tr = catalogo(idioma).get(texto)
    if not tr and idioma != BASE:
        tr = catalogo(RESPALDO).get(texto)
    tr = tr or texto
    if valores:
        try:
            return tr.format(**valores)
        except (KeyError, IndexError, ValueError):
            return texto.format(**valores)
    return tr


def decimal(idioma: str | None = None) -> str:
    idioma = idioma or _actual.get()
    if idioma == BASE:
        return ","
    return catalogo(idioma).get("_decimal") or catalogo(RESPALDO).get("_decimal", ".")


def orden_respaldo(idioma: str | None = None) -> list[str]:
    """Idiomas en los que buscar un recurso (p. ej. una página de ayuda): el pedido, el inglés
    y por último el español."""
    idioma = idioma or _actual.get()
    out = [idioma]
    for x in (RESPALDO, BASE):
        if x not in out:
            out.append(x)
    return out


def recargar():
    catalogo.cache_clear()
