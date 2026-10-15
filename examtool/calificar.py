# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Calificación: combina lo leído, los cambios manuales y la configuración.

Nada de esto se guarda: se recalcula cada vez, así que cambiar un valor de la
configuración (penalización, anular una pregunta, corregir una clave...) actualiza
al momento todas las notas sin perder las revisiones manuales.

Reglas de puntuación por pregunta (valor_bien = b, valor_mal = m, negativo):
  * En blanco: 0.
  * Casilla «Anular» marcada y sin revisar: 0 y queda pendiente de revisión.
  * Marca exactamente las correctas: b.
  * Una sola correcta y marca otra cosa: m.
  * Varias correctas (modo «parcial»):
        aciertos = correctas marcadas, errores = incorrectas marcadas
        si aciertos == 0                 -> m
        si no                            -> b * max(0, aciertos - errores) / nº correctas
    En modo «exacta» todo lo que no sea exacto vale m.
"""
from __future__ import annotations

from .banco import LETRAS, Alumno, buscar_alumno
from .i18n import t
from .lector import texto_error


def puntuar(marcadas: str, correctas: str, cfg: dict) -> tuple[float, str]:
    b, m = float(cfg["valor_bien"]), float(cfg["valor_mal"])
    M, C = set(marcadas), set(correctas)
    if not M:
        return 0.0, "blanco"
    if M == C:
        return b, "bien"
    if len(C) <= 1 or cfg.get("multiples", "parcial") == "exacta":
        return m, "mal"
    aciertos, errores = len(M & C), len(M - C)
    if aciertos == 0:
        return m, "mal"
    pts = b * max(0, aciertos - errores) / len(C)
    return round(pts, 4), "parcial"


def clave_impresa(item: dict, cfg: dict) -> str:
    """Letras correctas tal como se imprimieron, aplicando una corrección de clave si la hay."""
    nueva = (cfg.get("claves") or {}).get(item["id"])
    if not nueva:
        return item["correctas"]
    orig = {LETRAS.index(c) for c in nueva if c in LETRAS}
    return "".join(LETRAS[pos] for pos, o in enumerate(item["perm"]) if o in orig)


def calificar_hoja(lectura: dict, rev: dict, gen: dict, cfg: dict, alumnos: list[Alumno]) -> dict:
    """Resultado completo de una hoja. `rev` son los cambios manuales de esa hoja."""
    rev = rev or {}
    out = {"clave": lectura.get("clave"), "archivo": lectura.get("archivo"),
           "vista": lectura.get("vista"), "incidencias": [], "ok": bool(lectura.get("ok"))}
    if not lectura.get("ok"):
        out["incidencias"].append(texto_error(lectura))
        out["estado"] = "vacia" if lectura.get("vacia") else "error"
        return out

    # Modelo y copia
    qr = lectura.get("qr") or {}
    midx = rev.get("modelo", qr.get("modelo"))
    out["copia"] = qr.get("copia")
    if qr and qr.get("codigo") != gen["codigo"] and "modelo" not in rev:
        out["incidencias"].append(t("El QR es de otro examen (código {codigo})", codigo=qr.get("codigo")))
        midx = None
    personalizado = gen.get("tipo") == "personalizado"
    if midx is None or not (0 <= int(midx) < len(gen["modelos"])):
        out["incidencias"].append(t("No se ha podido leer el QR: indique de qué examen se trata") if personalizado
                                  else t("No se ha podido leer el QR: indique el modelo"))
        out["modelo"] = None
        midx = None
    else:
        midx = int(midx)
        out["modelo"] = midx
        out["modelo_nombre"] = gen["modelos"][midx]["nombre"]

    # Alumno
    out["id_leido"] = lectura.get("id_leido", "")
    al_qr = qr.get("alumno")
    impreso = gen["modelos"][midx].get("alumno") if midx is not None else None
    if impreso and not rev.get("documento"):
        # examen personalizado: el alumno va impreso en la hoja
        out["alumno"] = dict(impreso)
        out["id_tipo"] = "impreso"
    elif personalizado and midx is None and not rev.get("documento"):
        # sin QR no se sabe de quién es; lo leído en la zona del nombre no es un documento
        out["alumno"], out["id_tipo"] = None, "vacio"
    elif rev.get("documento"):
        doc = rev["documento"]
        al = next((a for a in alumnos if a.documento == doc), None)
        out["alumno"] = {"documento": doc, "nombre": al.nombre if al else ""}
        out["id_tipo"] = "manual"
    else:
        al, tipo = buscar_alumno(al_qr or out["id_leido"], alumnos)
        out["id_tipo"] = "qr" if al_qr and al else tipo
        out["alumno"] = {"documento": al.documento, "nombre": al.nombre} if al else None
        if tipo in ("comodin", "aproximado"):
            out["incidencias"].append(t("Documento deducido con dígitos dudosos: compruebe el alumno"))
        elif tipo == "no_encontrado":
            out["incidencias"].append(t("Documento {doc} no está en la lista", doc=out["id_leido"]))
        elif tipo == "vacio":
            out["incidencias"].append(t("No ha marcado el documento"))
    if lectura.get("id_dudas") and out["id_tipo"] not in ("manual", "qr", "impreso", "vacio"):
        out["incidencias"].append(t("Hay columnas del documento con marcas dudosas"))

    if midx is None:
        out["estado"] = "revisar"
        return out

    modelo = gen["modelos"][midx]
    anuladas = set(cfg.get("anuladas") or [])
    cambios = rev.get("respuestas", {})
    preguntas, total, n_validas = [], 0.0, 0
    cuenta = {"bien": 0, "mal": 0, "parcial": 0, "blanco": 0, "revisar": 0, "anulada": 0}
    for i, item in enumerate(modelo["preguntas"]):
        leida = lectura["respuestas"][i]
        corr = clave_impresa(item, cfg)
        manual = cambios.get(str(i))
        marcadas = manual if manual is not None else leida["m"]
        p = {"n": i + 1, "id": item["id"], "leida": leida["m"], "marcadas": marcadas,
             "correctas": corr, "anular": leida["anular"], "dudas": leida.get("dudas", ""),
             "manual": manual is not None}
        if item["id"] in anuladas:
            p.update(puntos=0.0, estado="anulada")
        elif leida["anular"] and manual is None:
            p.update(puntos=0.0, estado="revisar")
            n_validas += 1
        else:
            pts, est = puntuar(marcadas, corr, cfg)
            p.update(puntos=pts, estado=est)
            n_validas += 1
            total += pts
        if p["dudas"] and manual is None and p["estado"] != "anulada":
            p["aviso_duda"] = True
        cuenta[p["estado"]] += 1
        preguntas.append(p)
    # Personalizado: las preguntas superadas en clase cuentan como acierto completo
    superadas = [q for q in modelo.get("superadas") or [] if q not in anuladas]
    total += len(superadas) * float(cfg["valor_bien"])
    n_validas += len(superadas)
    cuenta["superadas"] = len(superadas)
    out["superadas"] = superadas
    out["preguntas"] = preguntas
    out["cuenta"] = cuenta
    out["puntos"] = round(total, 3)
    maximo = n_validas * float(cfg["valor_bien"])
    nota = (total / maximo * float(cfg["nota_maxima"])) if maximo else 0.0
    if not cfg.get("permitir_negativa"):
        nota = max(0.0, nota)
    out["nota"] = round(nota, 2)
    if cuenta["revisar"]:
        out["incidencias"].append(t("{n} pregunta(s) con «Anular» por revisar", n=cuenta["revisar"]))
    dudosas = sum(1 for p in preguntas if p.get("aviso_duda"))
    if dudosas:
        out["incidencias"].append(t("{n} pregunta(s) con marcas dudosas", n=dudosas))
    out["estado"] = "revisar" if out["incidencias"] and not rev.get("visto") else "ok"
    out["visto"] = bool(rev.get("visto"))
    return out


def calificar_todo(proyecto) -> list[dict]:
    gen = proyecto.generado()
    if not gen:
        return []
    cfg = proyecto.config()
    alumnos = proyecto.alumnos()
    lect = proyecto.lecturas()
    rev = proyecto.revision()
    res = [calificar_hoja(l, rev.get(k), gen, cfg, alumnos) for k, l in lect.items()]
    # Documento repetido en varias hojas
    vistos = {}
    for r in res:
        a = r.get("alumno")
        if a:
            vistos.setdefault(a["documento"], []).append(r)
    for doc, hojas in vistos.items():
        if len(hojas) > 1:
            for r in hojas:
                r["incidencias"].append(t("Este alumno aparece en más de una hoja"))
                r["estado"] = "revisar"
    return res


def estadistica(proyecto, resultados=None) -> list[dict]:
    """Por pregunta del banco: veces que sale, % de acierto, reparto de respuestas."""
    gen = proyecto.generado()
    cfg = proyecto.config()
    resultados = resultados if resultados is not None else calificar_todo(proyecto)
    datos = {}
    for r in resultados:
        for p in r.get("preguntas", []):
            d = datos.setdefault(p["id"], {"n": 0, "bien": 0, "parcial": 0, "mal": 0, "blanco": 0,
                                           "revisar": 0, "anulada": 0, "elecciones": [0, 0, 0, 0],
                                           "puntos": 0.0})
            d["n"] += 1
            d[p["estado"]] += 1
            d["puntos"] += p["puntos"]
            # elecciones en el orden ORIGINAL del banco, para comparar entre modelos
            item = gen["modelos"][r["modelo"]]["preguntas"][p["n"] - 1]
            for letra in p["marcadas"]:
                orig = item["perm"][LETRAS.index(letra)]
                if orig is not None:
                    d["elecciones"][orig] += 1
    out = []
    for qid, q in gen["banco"].items():
        d = datos.get(qid)
        if not d:
            continue
        validas = d["n"] - d["anulada"]
        out.append({
            "id": qid, "texto": q["texto"], "opciones": q["opciones"],
            "correctas_banco": q["correctas"],
            "correctas": (cfg.get("claves") or {}).get(qid, q["correctas"]),
            "clave_cambiada": qid in (cfg.get("claves") or {}),
            **d,
            "anulada": qid in (cfg.get("anuladas") or []),
            "acierto": round(100 * d["bien"] / validas, 1) if validas else None,
            "media": round(d["puntos"] / validas, 3) if validas else None,
        })
    out.sort(key=lambda x: (x["acierto"] is None, x["acierto"] if x["acierto"] is not None else 0))
    return out
