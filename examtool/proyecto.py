# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Un proyecto = una carpeta con todo lo de un examen (una convocatoria).

    proyecto.json     configuración editable
    preguntas.xlsx    banco de preguntas (o .csv)
    alumnos.xlsx      lista de clase (opcional; si no, se busca la hoja 'nombres' en preguntas)
    generado.json     modelos generados (orden de preguntas y respuestas, claves) — se congela al generar
    examenes.pdf      PDF para imprimir
    escaneos/         imágenes o PDF escaneados
    procesadas/       páginas enderezadas para la revisión
    lecturas.json     lo que ha leído el lector óptico
    revision.json     cambios manuales del profesor (nunca se pisan al volver a leer)
"""
from __future__ import annotations

import json
import random
import re
import secrets
import shutil
import time
from pathlib import Path

from . import i18n
from .banco import LETRAS, Pregunta, cargar_alumnos, cargar_preguntas
from .i18n import t

DESCRIPCION = (
    "Este test consta de {n} preguntas. Las respuestas correctas están valoradas con {bien} "
    "punto y las incorrectas restan {mal} puntos. En primer lugar, escriba nombre, documento y "
    "fecha. Escriba su documento de identidad (DNI, NIE o pasaporte, solo los números) en las "
    "casillas superiores, un dígito por columna empezando por la izquierda, y marque en cada "
    "columna la casilla de ese dígito. Conteste marcando con una X la casilla o casillas "
    "correspondientes (puede haber más de una respuesta correcta). Para anular o modificar una "
    "respuesta, marque su casilla «Anular» y escriba la aclaración en el recuadro."
)

DESCRIPCION_PERSONALIZADO = (
    "El examen consta de {n} preguntas. Las preguntas que haya superado en clase ya cuentan como "
    "correctas y no aparecen en este examen. Las respuestas correctas están valoradas con {bien} punto "
    "y las incorrectas restan {mal} puntos. Conteste marcando con una X la casilla o casillas "
    "correspondientes (puede haber más de una respuesta correcta). Para anular o modificar una "
    "respuesta, marque su casilla «Anular» y escriba la aclaración en el recuadro."
)

CONFIG_DEFECTO = {
    "titulo": "Examen tipo test",
    "subtitulo": "",
    # datos para organizar y filtrar los exámenes en la pantalla de inicio
    "asignatura": "",
    "convocatoria": "",
    "curso": "",
    "descripcion": "",              # vacío = texto estándar en el idioma del examen
    "idioma_examen": "es",          # idioma de la hoja impresa (puede ser distinto del de Aspa)
    "n_preguntas": 20,
    "valor_bien": 1.0,
    "valor_mal": -0.1,
    "multiples": "parcial",          # 'parcial' o 'exacta'
    "nota_maxima": 10.0,
    "permitir_negativa": False,
    "desordenar_preguntas": True,
    "desordenar_respuestas": True,
    "modelos": [
        {"nombre": "A", "grupos": ""},
        {"nombre": "B", "grupos": ""},
        {"nombre": "C", "grupos": ""},
        {"nombre": "D", "grupos": ""},
    ],
    "copias": 40,
    # tipo de examen: «modelos» (copias iguales por modelo) o «personalizado» (uno por alumno,
    # sin las preguntas que ya tiene superadas)
    "tipo": "modelos",
    "reserva": 3,                    # personalizado: exámenes completos sin personalizar
    "imagenes": [],                  # [{"fichero": ..., "pie": "Imagen 1"}] se imprimen al final
    "tam_pregunta": 10.0,
    "tam_respuesta": 9.5,
    "umbral_marca": 0.11,
    "umbral_duda": 0.04,
    # ajustes posteriores a la generación (desde la pantalla de estadística)
    "anuladas": [],                  # ids de pregunta anuladas para todos
    "claves": {},                    # id -> letras correctas (orden original del banco)
}


def slug(texto: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:50] or "examen"


def _fmt_num(x: float, idioma: str | None = None) -> str:
    return f"{x:g}".replace(".", i18n.decimal(idioma))


def _textos_estandar() -> set[str]:
    """Instrucciones estándar en todos los idiomas instalados (para reconocerlas)."""
    out = set()
    for cod in i18n.disponibles():
        for base in (DESCRIPCION, DESCRIPCION_PERSONALIZADO):
            out.add(t(base, idioma=cod).strip())
    return out


class Proyecto:
    def __init__(self, carpeta: Path):
        self.dir = Path(carpeta)

    # ---------------------------------------------------------------- creación
    @classmethod
    def crear(cls, base: Path, nombre: str) -> "Proyecto":
        s = slug(nombre)
        d = Path(base) / s
        n = 2
        while d.exists():
            d = Path(base) / f"{s}-{n}"
            n += 1
        d.mkdir(parents=True)
        p = cls(d)
        cfg = dict(CONFIG_DEFECTO)
        cfg["titulo"] = nombre
        p.guardar_config(cfg)
        return p

    @property
    def id(self) -> str:
        return self.dir.name

    # ---------------------------------------------------------------- ficheros
    def ruta(self, nombre: str) -> Path:
        return self.dir / nombre

    def _leer_json(self, nombre, defecto):
        f = self.ruta(nombre)
        if not f.exists():
            return defecto
        return json.loads(f.read_text(encoding="utf-8"))

    def _guardar_json(self, nombre, datos):
        f = self.ruta(nombre)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(f)

    def config(self) -> dict:
        cfg = dict(CONFIG_DEFECTO)
        cfg.update(self._leer_json("proyecto.json", {}))
        return cfg

    def guardar_config(self, cfg: dict):
        self._guardar_json("proyecto.json", cfg)

    def fichero_preguntas(self) -> Path | None:
        for ext in (".xlsx", ".xlsm", ".csv"):
            f = self.ruta("preguntas" + ext)
            if f.exists():
                return f
        return None

    def fichero_alumnos(self) -> Path | None:
        for ext in (".xlsx", ".xlsm", ".csv"):
            f = self.ruta("alumnos" + ext)
            if f.exists():
                return f
        return None

    def guardar_fichero(self, tipo: str, origen_nombre: str, datos: bytes):
        ext = Path(origen_nombre).suffix.lower()
        if ext not in (".xlsx", ".xlsm", ".csv"):
            raise ValueError(t("Formato no admitido: use .xlsx o .csv"))
        for e in (".xlsx", ".xlsm", ".csv"):
            self.ruta(tipo + e).unlink(missing_ok=True)
        self.ruta(tipo + ext).write_bytes(datos)

    def preguntas(self):
        f = self.fichero_preguntas()
        if not f:
            return [], [t("Todavía no se ha subido el banco de preguntas.")]
        return cargar_preguntas(f)

    def alumnos(self):
        for f in (self.fichero_alumnos(), self.fichero_preguntas()):
            if f:
                try:
                    al = cargar_alumnos(f)
                    if al:
                        return al
                except ValueError:
                    pass
        return []

    def generado(self) -> dict | None:
        return self._leer_json("generado.json", None)

    def lecturas(self) -> dict:
        return self._leer_json("lecturas.json", {})

    def guardar_lecturas(self, d):
        self._guardar_json("lecturas.json", d)

    def revision(self) -> dict:
        return self._leer_json("revision.json", {})

    def guardar_revision(self, d):
        self._guardar_json("revision.json", d)

    # ---------------------------------------------------------------- comprobación
    def comprobar(self) -> dict:
        """Equivalente a 'Comprobar preguntas': cuántas preguntas hay disponibles por modelo."""
        cfg = self.config()
        try:
            preguntas, avisos = self.preguntas()
        except ValueError as e:
            return {"ok": False, "avisos": [str(e)], "modelos": []}
        res, ok = [], bool(preguntas)
        for m in cfg["modelos"]:
            plan = plan_modelo(preguntas, m.get("grupos", ""), cfg["n_preguntas"])
            if plan["falta"]:
                ok = False
            res.append({"nombre": m["nombre"], "grupos": m.get("grupos", ""), "texto": plan["texto"],
                        "estado": plan["estado"], "del_modelo": plan["de_especificas"],
                        "al_azar": plan["al_azar"], "falta": plan["falta"]})
        if cfg["n_preguntas"] > 30:
            ok = False
            avisos = avisos + [t("La hoja de respuestas admite como máximo 30 preguntas.")]
        out = {"ok": ok, "avisos": avisos, "modelos": res, "total_banco": len(preguntas)}
        if cfg.get("tipo") == "personalizado":
            alumnos = self.alumnos()
            if not alumnos:
                out["ok"] = False
                out["avisos"] = out["avisos"] + [t("El examen personalizado necesita la lista de alumnos.")]
            if ok and alumnos:
                plan = plan_personalizado(preguntas, alumnos, cfg, random.Random(0))
                out["personalizado"] = plan
                for i, m in enumerate(res):
                    m["alumnos"] = sum(1 for a in plan if a["modelo"] == i)
        return out

    # ---------------------------------------------------------------- generación
    def generar(self, semilla: int | None = None) -> dict:
        cfg = self.config()
        preguntas, _ = self.preguntas()
        chk = self.comprobar()
        if not chk["ok"]:
            raise ValueError(t("Revise la comprobación de preguntas antes de generar."))
        semilla = semilla if semilla is not None else secrets.randbelow(10**9)
        rng = random.Random(semilla)
        n = cfg["n_preguntas"]

        def items_de(orden):
            orden = list(orden)
            if cfg["desordenar_preguntas"]:
                rng.shuffle(orden)
            items = []
            for q in orden:
                perm = permutar(q, rng) if cfg["desordenar_respuestas"] else _identidad(q)
                items.append({
                    "id": q.id,
                    "perm": perm,  # perm[pos_impresa] = índice original (None = hueco)
                    "correctas": "".join(LETRAS[pos] for pos, o in enumerate(perm) if o in q.correctas),
                })
            return items

        modelos = []
        if cfg.get("tipo") == "personalizado":
            # Un «modelo» por examen impreso: uno por alumno de la lista y después los de reserva
            for a in plan_personalizado(preguntas, self.alumnos(), cfg, rng):
                m = cfg["modelos"][a["modelo"]]
                pool = a["pool"]
                sup = set(a["superadas"])
                modelos.append({
                    "nombre": m["nombre"], "preguntas": items_de([q for q in pool if q.id not in sup]),
                    "alumno": {"documento": a["documento"], "nombre": a["nombre"]},
                    "superadas": a["superadas"], "total": len(pool),
                })
            nmod = len(cfg["modelos"])
            for k in range(int(cfg.get("reserva", 0))):
                m = cfg["modelos"][k % nmod]
                pool = elegir_preguntas(preguntas, m.get("grupos", ""), n, rng)
                modelos.append({"nombre": m["nombre"], "preguntas": items_de(pool), "alumno": None,
                                "superadas": [], "total": len(pool), "reserva": True})
            impresion = list(range(len(modelos)))
        else:
            for m in cfg["modelos"]:
                orden = elegir_preguntas(preguntas, m.get("grupos", ""), n, rng)
                modelos.append({"nombre": m["nombre"], "preguntas": items_de(orden)})
            impresion = [(c - 1) % len(modelos) for c in range(1, int(cfg["copias"]) + 1)]
        gen = {
            "codigo": secrets.token_hex(3).upper(),
            "tipo": cfg.get("tipo", "modelos"),
            "semilla": semilla,
            "fecha": time.strftime("%Y-%m-%d %H:%M"),
            "idioma": cfg.get("idioma_examen", "es"),
            "n_preguntas": n,
            "copias": len(impresion),
            "impresion": impresion,     # índice de modelo de cada copia impresa, en orden
            "banco": {q.id: q.to_dict() for q in preguntas},
            "modelos": modelos,
        }
        self._guardar_json("generado.json", gen)
        return gen

    def descripcion(self, personalizado: bool = False) -> str:
        """Instrucciones impresas, en el idioma del examen.

        Si el profesor no ha escrito las suyas (o las guardadas son el texto estándar de algún
        idioma, como en los exámenes creados antes de haber idiomas), se usa el texto estándar
        en el idioma del examen. En los personalizados (alumno ya impreso), el estándar no pide
        marcar el documento."""
        cfg = self.config()
        plantilla = (cfg.get("descripcion") or "").strip()
        if not plantilla or plantilla in _textos_estandar():
            return self.descripcion_estandar(personalizado)
        return self._rellenar(plantilla)

    def descripcion_estandar(self, personalizado: bool = False) -> str:
        cfg = self.config()
        base = DESCRIPCION_PERSONALIZADO if personalizado else DESCRIPCION
        return self._rellenar(t(base, idioma=cfg.get("idioma_examen")))

    def _rellenar(self, plantilla: str) -> str:
        cfg = self.config()
        idioma = cfg.get("idioma_examen")
        try:
            return plantilla.format(
                n=cfg["n_preguntas"], bien=_fmt_num(cfg["valor_bien"], idioma),
                mal=_fmt_num(abs(cfg["valor_mal"]), idioma))
        except (KeyError, IndexError, ValueError):
            return plantilla

    def borrar_correccion(self):
        for n in ("lecturas.json", "revision.json"):
            self.ruta(n).unlink(missing_ok=True)
        for d in ("escaneos", "procesadas"):
            shutil.rmtree(self.ruta(d), ignore_errors=True)


CONVOCATORIAS = ["Febrero", "Junio", "Septiembre", "Diciembre"]


def curso_actual(hoy=None) -> str:
    """Curso académico en curso: de septiembre a agosto (p. ej. 2026-2027)."""
    hoy = hoy or time.localtime()
    y = hoy.tm_year if hoy.tm_mon >= 9 else hoy.tm_year - 1
    return f"{y}-{y + 1}"


def validar_curso(texto: str) -> str:
    """Normaliza el curso a AAAA-AAAA. Vacío está permitido. Lanza ValueError si no es válido."""
    limpio = (texto or "").strip()
    if not limpio:
        return ""
    m = re.fullmatch(r"(\d{4})\s*[-/]\s*(\d{2}|\d{4})", limpio)
    if not m:
        raise ValueError(t("El curso debe tener el formato AAAA-AAAA, por ejemplo 2026-2027."))
    a = int(m.group(1))
    b = m.group(2)
    b = int(b) if len(b) == 4 else (a // 100) * 100 + int(b) + (100 if int(b) < a % 100 else 0)
    if b != a + 1:
        raise ValueError(t("El curso {curso} no es válido: el segundo año debe ser el siguiente al primero.",
                           curso=limpio))
    return f"{a}-{b}"


def cabecera_examen(cfg: dict) -> tuple[str, str]:
    """Textos impresos en el examen: (línea principal, línea secundaria).

    Principal: «Asignatura · Título». Secundaria: «Convocatoria Curso · Subtítulo».
    """
    idioma = cfg.get("idioma_examen")
    principal = " · ".join(x for x in (cfg.get("asignatura", "").strip(), cfg.get("titulo", "").strip()) if x)
    convocatoria = cfg.get("convocatoria", "").strip()
    conv = " ".join(x for x in (t(convocatoria, idioma=idioma) if convocatoria else "",
                                cfg.get("curso", "").strip()) if x)
    secundaria = " · ".join(x for x in (conv, cfg.get("subtitulo", "").strip()) if x)
    return principal or t("Examen tipo test", idioma=idioma), secundaria


def _grupos(texto: str) -> set[str]:
    return {g.strip() for g in re.split(r"[,;\s]+", texto or "") if g.strip()}


def plan_modelo(preguntas: list[Pregunta], grupos: str, n: int) -> dict:
    """Decide de dónde salen las n preguntas de un modelo.

    * especificas: preguntas cuyo grupo está en la lista del modelo.
    * libres: preguntas sin grupo en el banco, que completan al azar lo que falte.
    Si el modelo no tiene grupos, todas sus preguntas salen al azar de todo el banco.
    """
    gs = _grupos(grupos)
    if not gs:
        esp, libres = [], list(preguntas)
    else:
        esp = [q for q in preguntas if q.grupo.strip() in gs]
        libres = [q for q in preguntas if not q.grupo.strip()]
    de_esp = min(len(esp), n)
    al_azar = n - de_esp
    falta = max(0, al_azar - len(libres))
    if not gs:
        texto = (t("{n} al azar de {m}", n=n, m=len(libres)) if len(libres) > n
                 else t("las {m} del banco", m=len(libres)))
    elif len(esp) >= n:
        texto = t("{n} del modelo", n=n) + (" " + t("(al azar entre {m})", m=len(esp)) if len(esp) > n else "")
    elif al_azar <= len(libres):
        texto = t("{n} del modelo + {a} al azar (de {m} sin grupo)", n=de_esp, a=al_azar, m=len(libres))
    else:
        texto = t("{n} del modelo + {m} sin grupo: faltan {f}", n=de_esp, m=len(libres), f=falta)
    estado = "faltan" if falta else ("ok" if len(esp) == n or (not gs and len(libres) == n) else "azar")
    return {"especificas": esp, "libres": libres, "de_especificas": de_esp,
            "al_azar": al_azar, "falta": falta, "texto": texto, "estado": estado}


def elegir_preguntas(preguntas: list[Pregunta], grupos: str, n: int, rng: random.Random) -> list[Pregunta]:
    """Las del modelo primero (al azar si sobran) y el resto al azar entre las que no tienen grupo."""
    plan = plan_modelo(preguntas, grupos, n)
    if plan["falta"]:
        raise ValueError(t("No hay preguntas suficientes para el modelo."))
    esp = plan["especificas"]
    elegidas = rng.sample(esp, n) if len(esp) > n else list(esp)
    elegidas += rng.sample(plan["libres"], plan["al_azar"]) if plan["al_azar"] else []
    orden = {id(q): i for i, q in enumerate(preguntas)}
    return sorted(elegidas, key=lambda q: orden[id(q)])  # orden del banco si no se desordena


def plan_personalizado(preguntas: list[Pregunta], alumnos, cfg: dict, rng: random.Random) -> list[dict]:
    """Decide el modelo y las preguntas de cada alumno de la lista.

    Regla: cada alumno va a un modelo que pueda contener todas sus preguntas superadas; si
    caben en varios, al que lleve menos alumnos (así se reparten). Su examen son las preguntas de
    ese modelo menos las superadas, que cuentan como acierto. Si alguna superada no cabe en
    ningún modelo, se elige el que contenga más y se avisa (esas no se descuentan).
    """
    n = cfg["n_preguntas"]
    por_id = {q.id: q for q in preguntas}
    candidatos = []
    for m in cfg["modelos"]:
        plan = plan_modelo(preguntas, m.get("grupos", ""), n)
        esp = plan["especificas"]
        # preguntas que pueden llegar a estar en el modelo
        posibles = esp if len(esp) >= n else esp + [q for q in plan["libres"] if q not in esp]
        candidatos.append((plan, {q.id for q in posibles}))
    cuenta = [0] * len(candidatos)
    out = []
    for al in sorted(alumnos, key=lambda a: a.nombre.lower()):
        sup = [s for s in al.superadas]
        desconocidas = [s for s in sup if s not in por_id]
        sup = [s for s in sup if s in por_id]
        caben = [i for i, (_, ids) in enumerate(candidatos) if set(sup) <= ids]
        avisos = []
        if desconocidas:
            avisos.append(t("Superadas que no existen en el banco: {lista}", lista=", ".join(desconocidas)))
        if caben:
            midx = min(caben, key=lambda i: (cuenta[i], i))
        else:
            midx = max(range(len(candidatos)), key=lambda i: (len(set(sup) & candidatos[i][1]), -cuenta[i]))
            fuera = [s for s in sup if s not in candidatos[midx][1]]
            avisos.append(t("Ningún modelo contiene todas sus superadas; no se descuentan: {lista}",
                            lista=", ".join(fuera)))
        cuenta[midx] += 1
        plan, ids = candidatos[midx]
        sup = [s for s in sup if s in ids]
        pool = _pool_con(plan, n, [por_id[s] for s in sup], rng)
        out.append({"documento": al.documento, "nombre": al.nombre, "modelo": midx,
                    "superadas": sup, "pool": pool, "n_examen": len(pool) - len(sup),
                    "avisos": avisos})
    return out


def _pool_con(plan: dict, n: int, obligatorias: list[Pregunta], rng: random.Random) -> list[Pregunta]:
    """Las n preguntas del modelo, asegurando que estén las obligatorias (las superadas)."""
    esp, libres = plan["especificas"], plan["libres"]
    obl_esp = [q for q in obligatorias if q in esp]
    if len(esp) > n:
        resto = [q for q in esp if q not in obl_esp]
        elegidas = obl_esp + rng.sample(resto, n - len(obl_esp))
    else:
        elegidas = list(esp)
        faltan = n - len(elegidas)
        obl_lib = [q for q in obligatorias if q not in esp and q in libres]
        resto = [q for q in libres if q not in esp and q not in obl_lib]
        elegidas += obl_lib + rng.sample(resto, max(0, faltan - len(obl_lib)))
    orden = {id(q): i for i, q in enumerate(esp + libres)}
    return sorted(elegidas, key=lambda q: orden.get(id(q), 0))


def _identidad(q: Pregunta):
    return [i if q.opciones[i] else None for i in range(4)]


def permutar(q: Pregunta, rng: random.Random):
    """Desordena las opciones dejando en su sitio las fijas ('Todas son correctas'...)
    y los huecos (preguntas con menos de 4 opciones quedan con huecos al final)."""
    usadas = [i for i in range(4) if q.opciones[i]]
    moviles = [i for i in usadas if i not in q.fijas]
    barajadas = moviles[:]
    rng.shuffle(barajadas)
    it = iter(barajadas)
    perm = []
    for i in usadas:
        perm.append(i if i in q.fijas else next(it))
    perm += [None] * (4 - len(perm))
    return perm


def listar_proyectos(base: Path) -> list[dict]:
    base = Path(base)
    out = []
    if not base.exists():
        return out
    for d in sorted(base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if d.name.startswith(".") or not (d / "proyecto.json").exists():
            continue
        p = Proyecto(d)
        cfg = p.config()
        out.append({
            "id": p.id, "titulo": cfg["titulo"],
            "asignatura": cfg.get("asignatura", ""), "convocatoria": cfg.get("convocatoria", ""),
            "curso": cfg.get("curso", ""),
            "generado": p.ruta("generado.json").exists(),
            "hojas": len(p.lecturas()),
            "modificado": time.strftime("%d/%m/%Y", time.localtime(d.stat().st_mtime)),
            "orden": d.stat().st_mtime,
        })
    return out


def mover_a_papelera(base: Path, pid: str) -> Path:
    """No se borra nada de verdad: la carpeta se mueve a <base>/.papelera/ por si hiciera falta recuperarla."""
    origen = Path(base) / pid
    papelera = Path(base) / ".papelera"
    papelera.mkdir(exist_ok=True)
    destino = papelera / f"{pid}-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.move(str(origen), str(destino))
    return destino
