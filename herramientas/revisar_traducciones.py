# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Revisa y mantiene los ficheros de idioma (idiomas/<código>.json).

    python herramientas/revisar_traducciones.py en               # qué falta por traducir en inglés
    python herramientas/revisar_traducciones.py en --actualizar  # añade al fichero los textos nuevos (vacíos)
    python herramientas/revisar_traducciones.py fr --nuevo "Français"   # crea un idioma nuevo

Un valor vacío en el JSON significa «sin traducir»: Aspa muestra el texto en inglés.
Recoge los textos de:
  * las plantillas HTML: {{ _('...') }}
  * el código Python: t("..."), incluidas las cadenas partidas en varias líneas
  * los textos de datos que se traducen al mostrarlos (estados, convocatorias, plantillas Excel,
    instrucciones estándar, errores del lector, cabeceras del Excel de notas).
"""
import ast
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from jinja2 import Environment  # noqa: E402


def textos_plantillas() -> dict[str, str]:
    env = Environment(extensions=["jinja2.ext.i18n"])
    out = {}
    for f in sorted((RAIZ / "templates").rglob("*.html")):
        rel = f.relative_to(RAIZ / "templates")
        if rel.parts[0] == "ayuda" and len(rel.parts) > 1 and rel.parts[1] != "es":
            continue  # las ayudas traducidas son plantillas completas por idioma
        fuente = f.read_text(encoding="utf-8")
        try:
            for _, _, msg in env.extract_translations(fuente, gettext_functions=("_",)):
                if isinstance(msg, str):
                    out.setdefault(msg, str(rel))
        except Exception as e:  # noqa: BLE001
            print(f"  aviso: no se pudo analizar {rel}: {e}")
        # el extractor de Jinja ignora _('…', n=…): se buscan también directamente
        for m in re.finditer(r"""_\(\s*('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")""", fuente):
            try:
                out.setdefault(ast.literal_eval(m.group(1)), str(rel))
            except (ValueError, SyntaxError):
                pass
    return out


def textos_python() -> dict[str, str]:
    out = {}
    ficheros = [RAIZ / "app.py"] + sorted((RAIZ / "examtool").glob("*.py"))
    for f in ficheros:
        arbol = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(arbol):
            if not isinstance(n, ast.Call):
                continue
            nombre = getattr(n.func, "id", getattr(n.func, "attr", ""))
            # t("texto", ...) — el primer argumento
            if nombre == "t" and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                out.setdefault(n.args[0].value, f.name)
            # cabeceras del Excel de notas: _cabecera(ws, ["...", ...])
            if nombre == "_cabecera" and len(n.args) > 1 and isinstance(n.args[1], (ast.List, ast.BinOp)):
                listas = [n.args[1]] if isinstance(n.args[1], ast.List) else [
                    x for x in (n.args[1].left, n.args[1].right) if isinstance(x, ast.List)]
                for lista in listas:
                    for elt in lista.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            out.setdefault(elt.value, f.name)
        # filas de la hoja «Configuración» del Excel: for k, v in [("Clave", valor), ...]
        if f.name == "exportar.py":
            for n in ast.walk(arbol):
                if isinstance(n, ast.For) and isinstance(n.iter, ast.List):
                    for tupla in n.iter.elts:
                        if isinstance(tupla, ast.Tuple) and isinstance(tupla.elts[0], ast.Constant):
                            out.setdefault(tupla.elts[0].value, f.name)
    return out


def textos_datos() -> dict[str, str]:
    """Textos guardados como datos y traducidos al mostrarlos."""
    from examtool import lector, plantillas, proyecto
    out = {}
    for c in proyecto.CONVOCATORIAS:
        out.setdefault(c, "proyecto.CONVOCATORIAS")
    out.setdefault(proyecto.DESCRIPCION, "proyecto.DESCRIPCION")
    out.setdefault(proyecto.DESCRIPCION_PERSONALIZADO, "proyecto.DESCRIPCION_PERSONALIZADO")
    for k in lector.ERRORES:
        out.setdefault(k, "lector.ERRORES")
    for c, _, d in plantillas.COLUMNAS_PREGUNTAS:
        out.setdefault(c, "plantillas.COLUMNAS_PREGUNTAS")
        out.setdefault(d, "plantillas.COLUMNAS_PREGUNTAS")
    for fila, expl in plantillas.EJEMPLOS_PREGUNTAS:
        out.setdefault(expl, "plantillas.EJEMPLOS_PREGUNTAS")
        for k in plantillas._TRADUCIBLES:
            if fila.get(k):
                out.setdefault(fila[k], "plantillas.EJEMPLOS_PREGUNTAS")
    for _, expl in plantillas.EJEMPLOS_ALUMNOS:
        out.setdefault(expl, "plantillas.EJEMPLOS_ALUMNOS")
    for lista in (plantillas.INSTRUCCIONES_PREGUNTAS, plantillas.INSTRUCCIONES_ALUMNOS,
                  plantillas.INSTRUCCIONES_PERSONALIZADO):
        for linea in lista:
            if linea.strip() and linea != "__COLUMNAS__":
                out.setdefault(linea, "plantillas.INSTRUCCIONES")
    import app
    for v in app.ESTADOS.values():
        out.setdefault(v, "app.ESTADOS")
    return out


def todos() -> dict[str, str]:
    out = {}
    for fuente in (textos_plantillas(), textos_python(), textos_datos()):
        for k, v in fuente.items():
            if k.strip():
                out.setdefault(k, v)
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cod = sys.argv[1]
    f = RAIZ / "idiomas" / f"{cod}.json"
    claves = todos()
    if "--nuevo" in sys.argv:
        nombre = sys.argv[sys.argv.index("--nuevo") + 1]
        if f.exists():
            sys.exit(f"Ya existe {f}")
        datos = {"_nombre": nombre, "_decimal": ".", **{k: "" for k in sorted(claves)}}
        f.parent.mkdir(exist_ok=True)
        f.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Creado {f} con {len(claves)} textos por traducir.")
        print(f"Para las páginas de ayuda, copie templates/ayuda/en (o es) en templates/ayuda/{cod} y tradúzcalas.")
        print("Mientras falte algo, Aspa lo mostrará en inglés.")
        return
    datos = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    faltan = [k for k in claves if not datos.get(k)]
    sobran = [k for k in datos if not k.startswith("_") and k not in claves]
    print(f"{cod}: {len(claves)} textos, {len(claves) - len(faltan)} traducidos, {len(faltan)} sin traducir, "
          f"{len(sobran)} que ya no se usan.")
    for k in faltan[:200]:
        print(f"  FALTA [{claves[k]}] {k!r}")
    for k in sobran[:50]:
        print(f"  SOBRA {k!r}")
    ayudas = RAIZ / "templates" / "ayuda"
    for nombre in sorted(p.name for p in (ayudas / "es").glob("*.html")):
        if not (ayudas / cod / nombre).exists():
            print(f"  FALTA la página de ayuda templates/ayuda/{cod}/{nombre}")
    if "--actualizar" in sys.argv:
        for k in faltan:
            datos.setdefault(k, "")
        f.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Actualizado {f}.")


if __name__ == "__main__":
    main()
