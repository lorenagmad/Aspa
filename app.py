# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Aspa: aplicación web local para generar, leer y corregir exámenes tipo test.

    python app.py                      # abre el navegador en http://127.0.0.1:5077
    python app.py --carpeta D:\\Examenes  # carpeta donde se guardan los proyectos
    python app.py --puerto 8000 --sin-navegador
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import threading
import webbrowser
from pathlib import Path
from urllib.parse import quote

from flask import (Flask, abort, flash, jsonify, redirect, render_template, request, send_file,
                   url_for)

from examtool import __version__
from examtool import i18n
from examtool.i18n import t
from examtool import layout as L
from examtool.calificar import calificar_hoja, calificar_todo, estadistica
from examtool.exportar import exportar_excel
from examtool.lector import leer_proyecto, texto_error
from examtool.pdf import etiqueta_modelo, generar_pdf, generar_soluciones, vista_previa_png
from examtool.plantillas import (COLUMNAS_PREGUNTAS, EJEMPLOS_ALUMNOS, EJEMPLOS_PREGUNTAS, columnas, ejemplos_alumnos, ejemplos_preguntas,
                                 plantilla_alumnos, plantilla_personalizado, plantilla_preguntas)
from examtool.proyecto import _textos_estandar as textos_estandar
from examtool.proyecto import (CONVOCATORIAS, Proyecto, cabecera_examen, curso_actual, listar_proyectos,
                               mover_a_papelera, validar_curso)

app = Flask(__name__)
app.secret_key = os.environ.get("EXAMTOOL_SECRET", "local-solo")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024
BASE = Path(os.environ.get("EXAMTOOL_DIR", Path.home() / "ExamenesTest"))
LECTURAS: dict[str, dict] = {}  # estado de las lecturas en segundo plano


# --------------------------------------------------------------------- idioma de la aplicación

def _ajustes() -> dict:
    """Preferencias de la instalación (idioma), en <carpeta de exámenes>/ajustes.json."""
    f = BASE / "ajustes.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _guardar_ajustes(d: dict):
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "ajustes.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def idioma_app() -> str:
    return i18n.valido(_ajustes().get("idioma"))


@app.before_request
def _fijar_idioma():
    i18n.usar(idioma_app())


app.jinja_env.globals["_"] = t


@app.post("/idioma")
def cambiar_idioma():
    cod = i18n.valido(request.form.get("idioma"))
    aj = _ajustes()
    aj["idioma"] = cod
    _guardar_ajustes(aj)
    volver = request.form.get("volver") or "/"
    if not volver.startswith("/") or volver.startswith("//"):
        volver = "/"
    return redirect(volver)


@app.template_filter("q")
def _quote(s):
    return quote(str(s), safe="")


@app.template_filter("dec")
def _decimal(x, n=2):
    """Número con el separador decimal del idioma; vacío si no hay valor."""
    if x is None or not isinstance(x, (int, float)):
        return ""
    return f"{x:.{n}f}".replace(".", i18n.decimal())


def _progreso(p: Proyecto) -> dict:
    """Qué pasos del examen están completados, para marcarlos en el menú."""
    gen = p.ruta("generado.json").exists()
    try:
        preguntas = bool(p.fichero_preguntas()) and bool(p.preguntas()[0])
    except ValueError:
        preguntas = False
    corregido = False
    if gen and p.lecturas():
        try:
            corregido = not any(r.get("estado") in ("revisar", "error") for r in calificar_todo(p))
        except Exception:  # noqa: BLE001
            corregido = False
    return {"preguntas": preguntas, "config": gen, "generar": gen, "corregir": corregido}


@app.context_processor
def _globales():
    return {"version": __version__, "carpeta_base": str(BASE), "convocatorias_fijas": CONVOCATORIAS,
            "progreso": _progreso, "cabecera_de": cabecera_examen,
            "idioma": i18n.actual(), "idiomas": i18n.disponibles()}


@app.post("/apagar")
def apagar():
    """Detiene el programa. Los navegadores no dejan que una página cierre su propia pestaña,
    así que se muestra un aviso para cerrarla a mano."""
    if any(e.get("activo") for e in LECTURAS.values()):
        flash(t("Hay una lectura de escaneos en curso. Espere a que termine antes de cerrar Aspa."), "error")
        return redirect(request.referrer or url_for("inicio"))
    threading.Timer(1.0, lambda: os._exit(0)).start()
    return render_template("apagado.html")


def _datos_examen(form) -> dict:
    """Asignatura, convocatoria y curso del formulario. Lanza ValueError si el curso no es válido."""
    conv = form.get("convocatoria", "").strip()
    if conv == "__otra__":
        conv = form.get("convocatoria_otra", "").strip()
    return {"asignatura": form.get("asignatura", "").strip(), "convocatoria": conv,
            "curso": validar_curso(form.get("curso", ""))}


def proyecto(pid: str) -> Proyecto:
    if not re.fullmatch(r"[a-z0-9\-]+", pid):
        abort(404)
    p = Proyecto(BASE / pid)
    if not p.ruta("proyecto.json").exists():
        abort(404)
    return p


# --------------------------------------------------------------------- inicio

ESTADOS = {  # se traducen al mostrarlos
    "preparacion": "En preparación",
    "generado": "Generado, sin escanear",
    "correccion": "En corrección",
    "corregido": "Corregido",
}


def _estado(x: dict) -> str:
    if not x["generado"]:
        return "preparacion"
    if not x["hojas"]:
        return "generado"
    try:
        res = calificar_todo(Proyecto(BASE / x["id"]))
    except Exception:  # noqa: BLE001 — un examen dañado no debe impedir ver la lista
        return "correccion"
    pendientes = any(r.get("estado") in ("revisar", "error") for r in res)
    return "correccion" if pendientes else "corregido"


@app.get("/")
def inicio():
    proyectos = listar_proyectos(BASE)
    for x in proyectos:
        x["estado"] = _estado(x)
        x["estado_txt"] = t(ESTADOS[x["estado"]])

    def valores(campo):
        return sorted({x[campo] for x in proyectos if x[campo]}, key=str.lower)

    return render_template("inicio.html", proyectos=proyectos, estados={k: t(v) for k, v in ESTADOS.items()},
                           asignaturas=valores("asignatura"), convocatorias=valores("convocatoria"),
                           cursos=valores("curso"), papelera=str(BASE / ".papelera"),
                           nuevo={"curso": curso_actual()})


@app.post("/borrar")
def borrar_examenes():
    ids = request.form.getlist("ids")
    n = 0
    for pid in ids:
        if re.fullmatch(r"[a-z0-9\-]+", pid) and (BASE / pid / "proyecto.json").exists():
            mover_a_papelera(BASE, pid)
            n += 1
    if n:
        flash(t("{n} examen(es) movido(s) a la papelera ({ruta}).", n=n, ruta=BASE / ".papelera") + " " + t(
              "Si fue un error, puede recuperarlos moviendo la carpeta de vuelta."))
    return redirect(url_for("inicio"))


# --------------------------------------------------------------------- plantillas y ayuda

@app.get("/plantillas/<tipo>-<version>.xlsx")
def descargar_plantilla(tipo, version):
    if tipo not in ("preguntas", "alumnos", "personalizado") or version not in ("limpia", "ejemplo"):
        abort(404)
    gen = {"preguntas": plantilla_preguntas, "alumnos": plantilla_alumnos,
           "personalizado": plantilla_personalizado}[tipo]
    datos = gen(version == "ejemplo")
    nombre = "_".join([t("plantilla"), t(tipo)] + ([t("ejemplo")] if version == "ejemplo" else [])) + ".xlsx"
    return send_file(io.BytesIO(datos), as_attachment=True, download_name=nombre,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _plantilla_ayuda(nombre: str) -> str:
    """Las ayudas son texto largo: una plantilla por idioma; si falta, la inglesa (y si no, la española)."""
    for cod in i18n.orden_respaldo():
        if (Path(app.root_path) / "templates" / "ayuda" / cod / f"{nombre}.html").exists():
            return f"ayuda/{cod}/{nombre}.html"
    return f"ayuda/es/{nombre}.html"


@app.get("/ayuda/preguntas")
def ayuda_preguntas():
    from examtool.banco import Pregunta, parse_correctas, PATRON_FIJA
    from examtool.calificar import puntuar
    from examtool.proyecto import CONFIG_DEFECTO, plan_modelo
    preguntas = []
    for fila, _ in EJEMPLOS_PREGUNTAS:
        ops = [fila.get(L, "") for L in "ABCD"]
        preguntas.append(Pregunta(
            id=fila["id"], texto=fila["pregunta"], opciones=ops,
            correctas=parse_correctas(fila["correcta"]), grupo=fila.get("grupo", ""),
            fijas={i for i, o in enumerate(ops) if o and PATRON_FIJA.match(o)} | parse_correctas(fila.get("fija", ""))))
    n = 4
    modelos = [(m, g, plan_modelo(preguntas, g, n)["texto"]) for m, g in
               [("A", "1"), ("B", "1,2"), ("C", "2"), ("D", "")]]
    cfg = dict(CONFIG_DEFECTO)
    parcial = [(m, puntuar(m, "AB", cfg)) for m in ["AB", "A", "B", "AC", "ABC", "C", "CD", ""]]
    cfg_exacta = dict(cfg, multiples="exacta")
    exacta = {m: puntuar(m, "AB", cfg_exacta)[0] for m, _ in parcial}
    return render_template(_plantilla_ayuda("preguntas"), columnas=columnas(), ejemplos=ejemplos_preguntas(),
                           claves=[c for c, _a, _d in COLUMNAS_PREGUNTAS],
                           modelos=modelos, n_ejemplo=n, parcial=parcial, exacta=exacta, cfg=cfg)


def _banco_ejemplo():
    from examtool.banco import PATRON_FIJA, Alumno, Pregunta, parse_correctas, parse_superadas
    preguntas = []
    for fila, _ in EJEMPLOS_PREGUNTAS:
        ops = [fila.get(L, "") for L in "ABCD"]
        preguntas.append(Pregunta(
            id=fila["id"], texto=fila["pregunta"], opciones=ops,
            correctas=parse_correctas(fila["correcta"]), grupo=fila.get("grupo", ""),
            fijas={i for i, o in enumerate(ops) if o and PATRON_FIJA.match(o)}
            | parse_correctas(fila.get("fija", ""))))
    alumnos = [Alumno(f["documento"], f["nombre"], parse_superadas(f["superadas"])) for f, _ in EJEMPLOS_ALUMNOS]
    return preguntas, alumnos


@app.get("/ayuda/personalizado")
def ayuda_personalizado():
    import random as _r
    from examtool.proyecto import CONFIG_DEFECTO, plan_personalizado
    preguntas, alumnos = _banco_ejemplo()
    n = 4
    modelos = [{"nombre": "A", "grupos": "1"}, {"nombre": "B", "grupos": "2"}]
    cfg = dict(CONFIG_DEFECTO, n_preguntas=n, modelos=modelos)
    plan = plan_personalizado(preguntas, alumnos, cfg, _r.Random(1))
    # ejemplo de nota: Ana (2 superadas) acierta 1 y falla 1 de las 2 de su examen
    b, m = cfg["valor_bien"], cfg["valor_mal"]
    puntos = 2 * b + 1 * b + 1 * m
    ejemplo_nota = {"superadas": 2, "bien": 1, "mal": 1, "puntos": puntos, "total": n,
                    "nota": round(puntos / (n * b) * cfg["nota_maxima"], 2), "valor_mal": m}
    return render_template(_plantilla_ayuda("personalizado"), plan=plan, modelos=modelos, n=n,
                           ejemplo=ejemplo_nota, cfg=cfg, ej_preguntas=ejemplos_preguntas(),
                           ej_alumnos=ejemplos_alumnos())


@app.get("/ayuda/alumnos")
def ayuda_alumnos():
    return render_template(_plantilla_ayuda("alumnos"), ejemplos=ejemplos_alumnos())


@app.post("/nuevo")
def nuevo():
    nombre = request.form.get("titulo", "").strip() or "Examen"
    try:
        datos = _datos_examen(request.form)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("inicio"))
    BASE.mkdir(parents=True, exist_ok=True)
    p = Proyecto.crear(BASE, " ".join(x for x in (datos["asignatura"], nombre, datos["convocatoria"],
                                                   datos["curso"]) if x))
    origen = request.form.get("copiar_de")
    if origen:
        o = proyecto(origen)
        cfg = o.config()
        cfg.update(titulo=nombre, anuladas=[], claves={})
    else:
        cfg = p.config()
    cfg["titulo"] = nombre
    cfg.update(datos)
    if request.form.get("tipo") in ("modelos", "personalizado"):
        cfg["tipo"] = request.form["tipo"]
    cfg["idioma_examen"] = i18n.valido(request.form.get("idioma_examen") or i18n.actual())
    p.guardar_config(cfg)
    if origen:
        for tipo in ("preguntas", "alumnos"):
            f = o.fichero_preguntas() if tipo == "preguntas" else o.fichero_alumnos()
            if f:
                p.guardar_fichero(tipo, f.name, f.read_bytes())
    return redirect(url_for("preparar", pid=p.id))


# --------------------------------------------------------------------- preparar

@app.get("/p/<pid>")
def preparar(pid):
    p = proyecto(pid)
    cfg = p.config()
    try:
        preguntas, avisos = p.preguntas()
        error_banco = None
    except ValueError as e:
        preguntas, avisos, error_banco = [], [], str(e)
    gen = p.generado()
    return render_template(
        "preparar.html", p=p, cfg=cfg, preguntas=preguntas, avisos=avisos, error_banco=error_banco,
        alumnos=p.alumnos(), chk=p.comprobar() if preguntas else None, gen=gen,
        hay_pdf=p.ruta("examenes.pdf").exists(), hay_lecturas=bool(p.lecturas()),
        descripcion=p.descripcion(personalizado=cfg.get("tipo") == "personalizado"),
        descripcion_defecto=p.descripcion_estandar(personalizado=cfg.get("tipo") == "personalizado"),
        paso="preparar", cabecera=cabecera_examen(cfg),
        asignaturas=sorted({x["asignatura"] for x in listar_proyectos(BASE) if x["asignatura"]}, key=str.lower))


@app.post("/p/<pid>/subir/<tipo>")
def subir(pid, tipo):
    p = proyecto(pid)
    if tipo not in ("preguntas", "alumnos"):
        abort(404)
    f = request.files.get("fichero")
    if not f or not f.filename:
        flash(t("Elija un fichero."), "error")
        return redirect(url_for("preparar", pid=pid))
    try:
        p.guardar_fichero(tipo, f.filename, f.read())
        if tipo == "preguntas":
            pr, _ = p.preguntas()
            flash(t("Banco cargado: {n} preguntas.", n=len(pr)))
        else:
            flash(t("Lista cargada: {n} alumnos.", n=len(p.alumnos())))
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("preparar", pid=pid) + f"#{tipo}")


def _num(v, defecto):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return defecto


@app.post("/p/<pid>/config")
def guardar_config(pid):
    p = proyecto(pid)
    cfg = p.config()
    f = request.form
    cfg["titulo"] = f.get("titulo", cfg["titulo"]).strip()
    cfg["subtitulo"] = f.get("subtitulo", "").strip()
    try:
        cfg.update(_datos_examen(f))
    except ValueError as e:
        flash(f"{e} " + t("Se mantiene el curso anterior."), "error")
        d = _datos_examen({**f.to_dict(), "curso": ""})
        cfg.update(asignatura=d["asignatura"], convocatoria=d["convocatoria"])
    desc = f.get("descripcion", cfg.get("descripcion", "")).strip()
    # si coincide con el texto estándar de algún idioma, se guarda vacío (= automático)
    cfg["descripcion"] = "" if desc in textos_estandar() else desc
    cfg["n_preguntas"] = max(1, min(30, int(_num(f.get("n_preguntas"), cfg["n_preguntas"]))))
    cfg["copias"] = max(1, min(999, int(_num(f.get("copias"), cfg["copias"]))))
    cfg["reserva"] = max(0, min(200, int(_num(f.get("reserva"), cfg.get("reserva", 0)))))
    if f.get("tipo") in ("modelos", "personalizado"):
        cfg["tipo"] = f["tipo"]
    if f.get("idioma_examen"):
        cfg["idioma_examen"] = i18n.valido(f["idioma_examen"])
    cfg["valor_bien"] = _num(f.get("valor_bien"), cfg["valor_bien"])
    cfg["valor_mal"] = -abs(_num(f.get("valor_mal"), cfg["valor_mal"]))
    cfg["nota_maxima"] = _num(f.get("nota_maxima"), cfg["nota_maxima"])
    cfg["multiples"] = "exacta" if f.get("multiples") == "exacta" else "parcial"
    cfg["permitir_negativa"] = f.get("permitir_negativa") == "1"
    cfg["desordenar_preguntas"] = f.get("desordenar_preguntas") == "1"
    cfg["desordenar_respuestas"] = f.get("desordenar_respuestas") == "1"
    cfg["tam_pregunta"] = _num(f.get("tam_pregunta"), cfg["tam_pregunta"])
    cfg["tam_respuesta"] = _num(f.get("tam_respuesta"), cfg["tam_respuesta"])
    nombres = f.getlist("modelo_nombre")
    grupos = f.getlist("modelo_grupos")
    modelos = [{"nombre": n.strip()[:12], "grupos": g.strip()} for n, g in zip(nombres, grupos) if n.strip()]
    if modelos:
        cfg["modelos"] = modelos[:15]
    p.guardar_config(cfg)
    flash(t("Configuración guardada."))
    return redirect(url_for("preparar", pid=pid) + "#config")


EXT_IMG = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")


@app.post("/p/<pid>/imagenes")
def subir_imagenes(pid):
    p = proyecto(pid)
    cfg = p.config()
    carpeta = p.ruta("imagenes")
    carpeta.mkdir(exist_ok=True)
    n = 0
    for fich in request.files.getlist("imagenes"):
        nombre = Path((fich.filename or "").replace("\\", "/")).name
        if Path(nombre).suffix.lower() not in EXT_IMG:
            continue
        base = re.sub(r"[^\w.\-]+", "_", Path(nombre).stem)[:40] or "imagen"
        destino = carpeta / f"{base}{Path(nombre).suffix.lower()}"
        k = 2
        while destino.exists():
            destino = carpeta / f"{base}_{k}{Path(nombre).suffix.lower()}"
            k += 1
        fich.save(destino)
        cfg.setdefault("imagenes", []).append(
            {"fichero": destino.name, "pie": f"Imagen {len(cfg['imagenes']) + 1}"})
        n += 1
    p.guardar_config(cfg)
    flash(t("{n} imagen(es) añadida(s).", n=n) if n else t("No se ha añadido ninguna imagen (PNG o JPG)."),
          None if n else "error")
    return redirect(url_for("preparar", pid=pid) + "#imagenes")


@app.post("/p/<pid>/imagenes/<int:i>")
def editar_imagen(pid, i):
    p = proyecto(pid)
    cfg = p.config()
    ims = cfg.get("imagenes") or []
    if not 0 <= i < len(ims):
        abort(404)
    accion = request.form.get("accion")
    if accion == "borrar":
        (p.ruta("imagenes") / ims[i]["fichero"]).unlink(missing_ok=True)
        ims.pop(i)
    elif accion == "subir" and i > 0:
        ims[i - 1], ims[i] = ims[i], ims[i - 1]
    elif accion == "pie":
        ims[i]["pie"] = request.form.get("pie", "").strip()[:120]
    cfg["imagenes"] = ims
    p.guardar_config(cfg)
    return redirect(url_for("preparar", pid=pid) + "#imagenes")


@app.get("/p/<pid>/imagenes/<nombre>")
def ver_imagen(pid, nombre):
    p = proyecto(pid)
    f = p.ruta("imagenes") / Path(nombre).name
    if not f.exists():
        abort(404)
    return send_file(f, max_age=600)


@app.post("/p/<pid>/generar")
def generar(pid):
    p = proyecto(pid)
    if p.lecturas() and request.form.get("confirmar") != "1":
        flash(t("Ya hay escaneos leídos de este examen. Volver a generar cambia el orden de las preguntas "
                "y las hojas ya impresas dejarían de corregirse bien."), "error")
        return redirect(url_for("preparar", pid=pid) + "#generar")
    try:
        p.generar()
        generar_pdf(p)
        generar_soluciones(p)
        flash(t("Exámenes generados. Descargue el PDF para imprimir."))
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("preparar", pid=pid) + "#generar")


@app.get("/p/<pid>/descargar/<nombre>")
def descargar(pid, nombre):
    p = proyecto(pid)
    if nombre == "notas.xlsx":
        exportar_excel(p)
    if nombre not in ("examenes.pdf", "soluciones.pdf", "notas.xlsx"):
        abort(404)
    f = p.ruta(nombre)
    if not f.exists():
        abort(404)
    nombre_desc = f"{p.id}-{nombre}"
    return send_file(f, as_attachment=request.args.get("ver") != "1", download_name=nombre_desc)


@app.get("/p/<pid>/vista-previa.png")
def vista_previa(pid):
    p = proyecto(pid)
    f = p.ruta("examenes.pdf")
    if not f.exists():
        abort(404)
    return send_file(io.BytesIO(vista_previa_png(f, 0, 1.6)), mimetype="image/png")


# --------------------------------------------------------------------- corregir

@app.get("/p/<pid>/corregir")
def corregir(pid):
    p = proyecto(pid)
    res = calificar_todo(p)
    orden = request.args.get("orden", "archivo")
    if orden == "nombre":
        res.sort(key=lambda r: ((r.get("alumno") or {}).get("nombre") or "~"))
    elif orden == "nota":
        res.sort(key=lambda r: -(r.get("nota") or -1))
    elif orden == "estado":
        res.sort(key=lambda r: {"error": 0, "revisar": 1, "ok": 2, "vacia": 3}.get(r.get("estado"), 4))
    escaneos = sorted(x.name for x in p.ruta("escaneos").glob("*")) if p.ruta("escaneos").exists() else []
    leidos = {l.get("archivo") for l in p.lecturas().values()}
    pendientes = [e for e in escaneos if e not in leidos]
    notas = [r["nota"] for r in res if r.get("nota") is not None]
    resumen = {
        "hojas": sum(1 for r in res if r.get("estado") != "vacia"),
        "revisar": sum(1 for r in res if r.get("estado") in ("revisar", "error")),
        "media": round(sum(notas) / len(notas), 2) if notas else None,
        "aprobados": sum(1 for n in notas if n >= p.config()["nota_maxima"] / 2),
    }
    return render_template("corregir.html", p=p, cfg=p.config(), res=res, gen=p.generado(),
                           pendientes=pendientes, resumen=resumen, orden=orden,
                           leyendo=LECTURAS.get(pid, {}).get("activo"), paso="corregir")


@app.post("/p/<pid>/escaneos")
def subir_escaneos(pid):
    p = proyecto(pid)
    carpeta = p.ruta("escaneos")
    carpeta.mkdir(exist_ok=True)
    n = 0
    for f in request.files.getlist("ficheros"):
        if not f.filename:
            continue
        nombre = Path(f.filename.replace("\\", "/")).name
        if Path(nombre).suffix.lower() not in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp",
                                               ".webp", ".pdf"):
            continue
        destino = carpeta / nombre
        k = 2
        while destino.exists():
            destino = carpeta / f"{Path(nombre).stem}_{k}{Path(nombre).suffix}"
            k += 1
        f.save(destino)
        n += 1
    flash(t("{n} fichero(s) añadidos.", n=n) if n else t("No se ha añadido ningún fichero válido."),
          None if n else "error")
    if n and request.form.get("leer") == "1":
        return lanzar_lectura(pid)
    return redirect(url_for("corregir", pid=pid))


@app.post("/p/<pid>/leer")
def lanzar_lectura(pid):
    p = proyecto(pid)
    if not p.generado():
        flash(t("Este proyecto no tiene exámenes generados."), "error")
        return redirect(url_for("corregir", pid=pid))
    forzar = request.form.get("forzar") == "1"
    if LECTURAS.get(pid, {}).get("activo"):
        return redirect(url_for("corregir", pid=pid))
    estado = {"activo": True, "hechos": 0, "total": 0, "error": None}
    LECTURAS[pid] = estado

    def tarea():
        try:
            def prog(i, n):
                estado.update(hechos=i, total=n)
            leer_proyecto(p, forzar=forzar, progreso=prog)
        except Exception as e:  # noqa: BLE001
            estado["error"] = str(e)
        finally:
            estado["activo"] = False

    threading.Thread(target=tarea, daemon=True).start()
    return redirect(url_for("corregir", pid=pid))


@app.get("/p/<pid>/leer/estado")
def estado_lectura(pid):
    return jsonify(LECTURAS.get(pid, {"activo": False}))


@app.post("/p/<pid>/borrar-correccion")
def borrar_correccion(pid):
    p = proyecto(pid)
    if request.form.get("confirmar", "").strip().upper() in ("BORRAR", t("BORRAR").upper()):
        p.borrar_correccion()
        flash(t("Escaneos, lecturas y revisiones borrados. El examen generado se conserva."))
    else:
        flash(t("Escriba {palabra} para confirmar.", palabra=t("BORRAR")), "error")
    return redirect(url_for("corregir", pid=pid))


@app.get("/p/<pid>/img/<nombre>")
def imagen(pid, nombre):
    p = proyecto(pid)
    f = p.ruta("procesadas") / Path(nombre).name
    if not f.exists():
        abort(404)
    return send_file(f, max_age=3600)


@app.get("/p/<pid>/original/<path:nombre>")
def original(pid, nombre):
    p = proyecto(pid)
    f = p.ruta("escaneos") / Path(nombre).name
    if not f.exists():
        abort(404)
    return send_file(f)


# --------------------------------------------------------------------- hoja

def _datos_hoja(p, clave):
    lect = p.lecturas()
    if clave not in lect:
        abort(404)
    rev = p.revision().get(clave, {})
    return calificar_hoja(lect[clave], rev, p.generado(), p.config(), p.alumnos()), lect[clave], rev


@app.get("/p/<pid>/hoja/<path:clave>")
def hoja(pid, clave):
    p = proyecto(pid)
    datos, lectura, rev = _datos_hoja(p, clave)
    claves = list(p.lecturas().keys())
    i = claves.index(clave)
    gen = p.generado()
    geometria = {
        "resp": [[[b.x, b.y, b.w] for b in (L.ans_box(q, k) for k in range(5))]
                 for q in range(L.MAX_PREGUNTAS)],
        "id": [[[b.x, b.y, b.w] for b in (L.id_box(c, d) for d in range(10))] for c in range(L.ID_COLS)],
        "alto": L.ACLA_Y + L.ACLA_H + 32,
    }
    # Si el lector localizó las casillas reales (papel curvado, foto con móvil), se dibuja sobre ellas
    centros = lectura.get("centros") if lectura.get("ok") else None
    if centros:
        w = L.BOX
        geometria["resp"] = [[[x - w / 2, y - w / 2, w] for x, y in fila] for fila in centros["resp"]]
        geometria["id"] = [[[x - w / 2, y - w / 2, w] for x, y in col] for col in centros["id"]]
    banco = gen["banco"]
    # Las explicaciones se toman del banco actual (se pueden añadir después de generar el examen,
    # antes de la revisión); si no, de la copia guardada al generar.
    try:
        explicaciones = {q.id: q.explicacion for q in p.preguntas()[0] if q.explicacion}
    except (ValueError, OSError):
        explicaciones = {}
    textos = []
    if datos.get("modelo") is not None:
        for item in gen["modelos"][datos["modelo"]]["preguntas"]:
            q = banco[item["id"]]
            textos.append({"t": q["texto"], "o": [q["opciones"][o] if o is not None else ""
                                                  for o in item["perm"]],
                           "e": explicaciones.get(item["id"]) or q.get("explicacion", "")})
    return render_template(
        "hoja.html", p=p, cfg=p.config(), datos=datos, error_lectura=texto_error(lectura), gen_tipo=gen.get("tipo", "modelos"), lectura=lectura, rev=rev, textos=textos,
        geometria=geometria, modelos=[etiqueta_modelo(m) for m in gen["modelos"]],
        alumnos=[{"d": a.documento, "n": a.nombre} for a in p.alumnos()],
        anterior=claves[i - 1] if i > 0 else None, siguiente=claves[i + 1] if i + 1 < len(claves) else None,
        posicion=(i + 1, len(claves)), modo=request.args.get("modo", "profesor"), paso="corregir")


@app.post("/api/p/<pid>/hoja/<path:clave>")
def api_hoja(pid, clave):
    p = proyecto(pid)
    if clave not in p.lecturas():
        abort(404)
    cambios = request.get_json(force=True) or {}
    revs = p.revision()
    rev = revs.setdefault(clave, {})
    if "modelo" in cambios:
        if cambios["modelo"] in (None, ""):
            rev.pop("modelo", None)
        else:
            rev["modelo"] = int(cambios["modelo"])
    if "documento" in cambios:
        if cambios["documento"]:
            rev["documento"] = str(cambios["documento"])
        else:
            rev.pop("documento", None)
    if "respuesta" in cambios:  # {"n": índice 0-based, "valor": "AC" | null}
        i = str(int(cambios["respuesta"]["n"]))
        v = cambios["respuesta"]["valor"]
        r = rev.setdefault("respuestas", {})
        if v is None:
            r.pop(i, None)
        else:
            r[i] = "".join(c for c in "ABCD" if c in str(v).upper())
    if "visto" in cambios:
        rev["visto"] = bool(cambios["visto"])
    if not rev:
        revs.pop(clave, None)
    p.guardar_revision(revs)
    datos, _, _ = _datos_hoja(p, clave)
    return jsonify(datos)


# --------------------------------------------------------------------- estadística

@app.get("/p/<pid>/estadistica")
def ver_estadistica(pid):
    p = proyecto(pid)
    return render_template("estadistica.html", p=p, cfg=p.config(), est=estadistica(p),
                           gen=p.generado(), paso="estadistica")


@app.post("/p/<pid>/pregunta/<qid>")
def ajustar_pregunta(pid, qid):
    p = proyecto(pid)
    cfg = p.config()
    accion = request.form.get("accion")
    anuladas = set(cfg.get("anuladas") or [])
    claves = dict(cfg.get("claves") or {})
    if accion == "anular":
        anuladas ^= {qid}
    elif accion == "clave":
        nueva = "".join(c for c in "ABCD" if c in request.form.get("clave", "").upper())
        banco = p.generado()["banco"]
        if not nueva or nueva == banco[qid]["correctas"]:
            claves.pop(qid, None)
        else:
            claves[qid] = nueva
    cfg["anuladas"] = sorted(anuladas)
    cfg["claves"] = claves
    p.guardar_config(cfg)
    flash(t("Cambio aplicado: todas las notas se han recalculado."))
    return redirect(url_for("ver_estadistica", pid=pid) + f"#q{quote(qid)}")


# --------------------------------------------------------------------- arranque

def main():
    global BASE
    ap = argparse.ArgumentParser(description="Aspa: exámenes tipo test")
    ap.add_argument("--carpeta", help="carpeta de proyectos (por defecto ~/ExamenesTest)")
    ap.add_argument("--puerto", type=int, default=5077)
    ap.add_argument("--sin-navegador", action="store_true")
    a = ap.parse_args()
    if a.carpeta:
        BASE = Path(a.carpeta).expanduser()
    BASE.mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{a.puerto}"
    import socket
    with socket.socket() as sk:
        sk.settimeout(0.5)
        if sk.connect_ex(("127.0.0.1", a.puerto)) == 0:
            print(f"\n  Aspa ya estaba abierto. Abriendo {url} en el navegador…\n")
            webbrowser.open(url)
            return
    print(f"\n  Aspa {__version__}\n  Proyectos en: {BASE}\n  Abra {url} en el navegador"
          "\n  (para terminar, pulse «Cerrar Aspa» en la página o cierre esta ventana)\n")
    if not a.sin_navegador:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=a.puerto, debug=False, threaded=True)


if __name__ == "__main__":
    main()
