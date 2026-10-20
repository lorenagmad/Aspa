# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""End-to-end functional tests of Aspa through its web interface (Flask test client).

    python SoftwareX/experiments/run_functional.py <work_dir>

Every feature described in the article is exercised as a teacher would use it: create an exam,
upload bank and class list, configure, generate, upload scans (images and multi-page PDF), read,
review and correct, void questions and fix keys, export to Excel, personalised exams, templates,
languages, copies of previous exams and the recycle bin. Writes <work_dir>/functional_results.json.
"""
import io
import json
import os
import random
import shutil
import sys
import time
from pathlib import Path

WORK = Path(sys.argv[1]).resolve()
BASE = WORK / "aspa_home"
shutil.rmtree(BASE, ignore_errors=True)
BASE.mkdir(parents=True)
os.environ["EXAMTOOL_DIR"] = str(BASE)

import common as C  # noqa: E402
import demo_data  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pymupdf as fitz  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

import app as aspa  # noqa: E402
from examtool import i18n  # noqa: E402
from examtool.banco import Alumno, buscar_alumno, cargar_alumnos, cargar_preguntas  # noqa: E402
from examtool.calificar import calificar_todo, estadistica, puntuar  # noqa: E402
from examtool.lector import leer_proyecto  # noqa: E402
from examtool.proyecto import Proyecto, validar_curso  # noqa: E402
from examtool.simulacion import simular  # noqa: E402

RESULTS = {"checks": [], "data": {}}


def check(name, cond, detail=""):
    RESULTS["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)})
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)


def xlsx_bytes(writer, *args):
    tmp = WORK / "_tmp.xlsx"
    writer(tmp, *args)
    return tmp.read_bytes()


def main():
    cl = aspa.app.test_client()

    # ------------------------------------------------------------ interface language
    r = cl.post("/idioma", data={"idioma": "en", "volver": "/"})
    home = cl.get("/").get_data(as_text=True)
    check("UI switches to English", r.status_code == 302 and "New exam" in home, "")
    check("Installed languages", set(i18n.disponibles()) >= {"es", "en"}, i18n.disponibles())

    # ------------------------------------------------------------ templates (blank and with examples)
    for tipo in ("preguntas", "alumnos", "personalizado"):
        for ver in ("limpia", "ejemplo"):
            r = cl.get(f"/plantillas/{tipo}-{ver}.xlsx")
            f = WORK / f"tpl_{tipo}_{ver}.xlsx"
            f.write_bytes(r.data)
            ok = r.status_code == 200
            if ver == "ejemplo" and tipo != "alumnos":
                qs, _ = cargar_preguntas(f)
                ok = ok and len(qs) == 7
            if ver == "ejemplo" and tipo != "preguntas":
                ok = ok and len(cargar_alumnos(f)) == 4
            check(f"Template {tipo}/{ver} downloads and parses back", ok, f.stat().st_size)
    for h in ("preguntas", "alumnos", "personalizado"):
        check(f"Help page {h}", cl.get(f"/ayuda/{h}").status_code == 200)

    # ------------------------------------------------------------ bank parsing features
    qs, avisos = cargar_preguntas(WORK / "tpl_preguntas_ejemplo.xlsx")
    by = {q.id: q for q in qs}
    check("Multiple correct answers parsed (AB)", by["2"].correctas == {0, 1})
    check("Numeric key parsed (1 = A)", by["4"].correctas == {0})
    check("'All/None of the above' detected as fixed", 3 in by["3"].fijas and 3 in by["4"].fijas)
    check("Explicit fixed column (ABC)", {0, 1, 2} <= by["6"].fijas)
    check("True/false question with two options", by["5"].opciones[2:] == ["", ""])
    csv = WORK / "bank.csv"
    csv.write_text("num;Preg;Resp 1;Resp 2;Resp 3;Resp 4;Corr;Selec\n1;Q one?;a;b;c;d;13;1\n1;Q dup?;a;b;;;2;\n",
                   encoding="utf-8")
    qs2, av2 = cargar_preguntas(csv)
    check("CSV with legacy headers, numeric multi-key and duplicate id warning",
          len(qs2) == 2 and qs2[0].correctas == {0, 2} and qs2[1].id != "1" and av2, av2)
    check("Academic year validation", validar_curso("2025/26") == "2025-2026"
          and _raises(lambda: validar_curso("2025-2027")))

    # ------------------------------------------------------------ student matching
    al = [Alumno("12345678Z", "A"), Alumno("X1234567L", "B"), Alumno("C01X00T47", "C"), Alumno("87654321X", "D")]
    cases = {"12345678": ("exacto", "A"), "1234567": ("exacto", "B"), "010047": ("exacto", "C"),
             "1234?678": ("comodin", "A"), "12345679": ("aproximado", "A"), "55555555": ("no_encontrado", None),
             "": ("vacio", None)}
    res_m = {}
    for leido, (tipo, quien) in cases.items():
        a, t_ = buscar_alumno(leido, al)
        res_m[leido] = (t_, a.nombre if a else None)
    check("Student matching (exact, NIE, passport, wildcard, one-digit, not found, empty)",
          all(res_m[k] == v for k, v in cases.items()), res_m)
    RESULTS["data"]["matching"] = res_m

    # ------------------------------------------------------------ scoring rules
    cfg = {"valor_bien": 1, "valor_mal": -0.25, "multiples": "parcial"}
    table = {m: puntuar(m, "AB", cfg) for m in ["AB", "A", "B", "ABC", "AC", "C", "CD", "ABCD", ""]}
    table_exact = {m: puntuar(m, "AB", dict(cfg, multiples="exacta")) for m in table}
    single = {m: puntuar(m, "C", cfg) for m in ["C", "A", "AC", ""]}
    exp = {"AB": 1, "A": 0.5, "B": 0.5, "ABC": 0.5, "AC": 0, "C": -0.25, "CD": -0.25, "ABCD": 0, "": 0}
    check("Partial-credit rule b*max(0,hits-errors)/|C|", all(abs(table[k][0] - v) < 1e-9 for k, v in exp.items()), table)
    check("Exact mode: anything but the exact key is a wrong answer",
          all(table_exact[k][0] == (1 if k == "AB" else 0 if k == "" else -0.25) for k in table_exact))
    check("Single-answer questions", single == {"C": (1, "bien"), "A": (-0.25, "mal"), "AC": (-0.25, "mal"),
                                                 "": (0, "blanco")}, single)
    RESULTS["data"]["scoring_partial"] = table
    RESULTS["data"]["scoring_exact"] = table_exact

    # ------------------------------------------------------------ create exam through the UI
    r = cl.post("/nuevo", data={"titulo": "Final exam", "asignatura": "Software Engineering",
                                "convocatoria": "Junio", "curso": "2025-2026", "tipo": "modelos",
                                "idioma_examen": "en"})
    pid = r.headers["Location"].rsplit("/", 1)[-1]
    p = Proyecto(BASE / pid)
    check("Exam created from the home page", r.status_code == 302 and p.ruta("proyecto.json").exists(), pid)
    r = cl.post(f"/p/{pid}/subir/preguntas", data={"fichero": (io.BytesIO(xlsx_bytes(demo_data.write_bank)), "bank.xlsx")},
                content_type="multipart/form-data")
    check("Question bank uploaded (40 questions)", len(p.preguntas()[0]) == 40)
    r = cl.post(f"/p/{pid}/subir/alumnos", data={"fichero": (io.BytesIO(xlsx_bytes(demo_data.write_students)), "class.xlsx")},
                content_type="multipart/form-data")
    check("Class list uploaded (40 students)", len(p.alumnos()) == 40)
    # images printed at the end of the exam
    img = np.full((400, 700, 3), 255, np.uint8)
    cv2.rectangle(img, (40, 40), (300, 200), (200, 80, 30), -1)
    cv2.circle(img, (500, 220), 120, (30, 140, 30), -1)
    cv2.putText(img, "Figure for Q21", (180, 370), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 3)
    ok, png = cv2.imencode(".png", img)
    cl.post(f"/p/{pid}/imagenes", data={"imagenes": [(io.BytesIO(png.tobytes()), "diagram.png")]},
            content_type="multipart/form-data")
    cl.post(f"/p/{pid}/imagenes/0", data={"accion": "pie", "pie": "Figure 1. UML diagram"})
    check("Image attached with caption", p.config()["imagenes"][0]["pie"] == "Figure 1. UML diagram")
    form = {"titulo": "Final exam", "subtitulo": "Group 1", "asignatura": "Software Engineering",
            "convocatoria": "Junio", "curso": "2025-2026", "descripcion": "", "n_preguntas": "20", "copias": "40",
            "reserva": "0", "tipo": "modelos", "idioma_examen": "en", "valor_bien": "1", "valor_mal": "0,25",
            "nota_maxima": "10", "multiples": "parcial", "desordenar_preguntas": "1", "desordenar_respuestas": "1",
            "tam_pregunta": "10", "tam_respuesta": "9.5",
            "modelo_nombre": ["A", "B", "C", "D"], "modelo_grupos": ["T", "R", "T,R", ""]}
    cl.post(f"/p/{pid}/config", data=form)
    cfg = p.config()
    check("Settings saved (decimal comma accepted, penalty stored negative)",
          cfg["valor_mal"] == -0.25 and cfg["modelos"][2]["grupos"] == "T,R")
    chk = p.comprobar()
    RESULTS["data"]["plan"] = [(m["nombre"], m["texto"], m["estado"]) for m in chk["modelos"]]
    check("Question-availability check per version", chk["ok"], RESULTS["data"]["plan"])

    # ------------------------------------------------------------ generation
    t0 = time.perf_counter()
    cl.post(f"/p/{pid}/generar")
    t_gen = time.perf_counter() - t0
    gen = p.generado()
    with fitz.open(p.ruta("examenes.pdf")) as d:
        pages = d.page_count
        text_p1 = d[0].get_text()
    RESULTS["data"]["generation"] = {"copies": gen["copias"], "pages": pages, "seconds": round(t_gen, 2),
                                     "code": gen["codigo"]}
    check("PDF with 40 copies generated (duplex-ready)", gen["copias"] == 40 and pages % 2 == 0,
          f"{pages} pages in {t_gen:.1f} s")
    check("Printed exam in English", "Answer sheet" in text_p1 or "Version" in text_p1 or "Clarifications" in text_p1,
          text_p1[:80].replace("\n", " "))
    check("Answer keys PDF generated", p.ruta("soluciones.pdf").exists())
    m = gen["modelos"]
    ids_A = {q["id"] for q in m[0]["preguntas"]}
    ids_B = {q["id"] for q in m[1]["preguntas"]}
    ids_C = {q["id"] for q in m[2]["preguntas"]}
    check("Version A contains all 10 testing questions + 10 ungrouped",
          {str(i) for i in range(1, 11)} <= ids_A and all(int(i) > 20 for i in ids_A - {str(i) for i in range(1, 11)}))
    check("Version B contains all 10 requirements questions", {str(i) for i in range(11, 21)} <= ids_B)
    check("Version C = groups T and R", ids_C == {str(i) for i in range(1, 21)})
    check("Interleaved distribution A,B,C,D,A,...", gen["impresion"][:8] == [0, 1, 2, 3, 0, 1, 2, 3])
    fixed_ok = True
    for mod in m:
        for item in mod["preguntas"]:
            q = gen["banco"][item["id"]]
            if q["opciones"][3].startswith(("All of", "None of")):
                fixed_ok &= item["perm"][3] == 3
            if item["id"] == "15":
                fixed_ok &= item["perm"][:3] == [0, 1, 2]
    check("Fixed options stay in place after shuffling", fixed_ok)
    tf_ok = all(item["perm"][2:] == [None, None] for mod in m for item in mod["preguntas"]
                if gen["banco"][item["id"]]["opciones"][2] == "")
    check("True/false questions keep two boxes (gaps at the end)", tf_ok)
    shuffled = sum(item["perm"] != [0, 1, 2, 3] for mod in m for item in mod["preguntas"])
    check("Options shuffled", shuffled > 40, shuffled)
    check("Preview image", cl.get(f"/p/{pid}/vista-previa.png").status_code == 200)

    # ------------------------------------------------------------ scans: images + multi-page PDF
    simular(p, 36, semilla=4)
    esc = p.ruta("escaneos")
    files = sorted(esc.glob("*.jpg"))
    truth = json.loads(p.ruta("simulacion.json").read_text(encoding="utf-8"))
    # Move them out and upload through the web interface: 30 as images, 6 inside one PDF
    # together with a blank page and a question page, as a sheet-feed scanner would produce.
    staging = WORK / "staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    for f in files:
        shutil.move(str(f), staging / f.name)
    doc = fitz.open()
    for f in sorted(staging.glob("*.jpg"))[30:]:
        im = fitz.open(f)
        rect = im[0].rect
        pdfbytes = im.convert_to_pdf()
        doc.insert_pdf(fitz.open("pdf", pdfbytes))
    doc.new_page(width=595, height=842)  # blank page
    with fitz.open(p.ruta("examenes.pdf")) as ex:
        doc.insert_pdf(ex, from_page=1, to_page=1)  # a question page
    doc.save(staging / "batch.pdf")
    uploads = [(io.BytesIO(f.read_bytes()), f.name) for f in sorted(staging.glob("*.jpg"))[:30]]
    uploads.append((io.BytesIO((staging / "batch.pdf").read_bytes()), "batch.pdf"))
    uploads.append((io.BytesIO(b"not an exam"), "notes.txt"))
    t0 = time.perf_counter()
    cl.post(f"/p/{pid}/escaneos", data={"ficheros": uploads, "leer": "1"}, content_type="multipart/form-data")
    for _ in range(600):
        if not aspa.LECTURAS.get(pid, {}).get("activo"):
            break
        time.sleep(0.3)
    t_read = time.perf_counter() - t0
    lect = p.lecturas()
    check("Unsupported files are skipped on upload", not (esc / "notes.txt").exists())
    check("All pages read (30 images + 8-page PDF)", len(lect) == 38, f"{len(lect)} pages in {t_read:.1f} s")
    res = calificar_todo(p)
    ignored = [r for r in res if r["estado"] == "vacia"]
    check("Blank page and question page ignored", len(ignored) == 2, [r["clave"] for r in ignored])
    RESULTS["data"]["reading"] = {"pages": len(lect), "seconds": round(t_read, 2)}

    # accuracy against the simulation ground truth
    pdf_names = sorted(staging.glob("*.jpg"))[30:]
    key_of = {f.name: f.name for f in sorted(staging.glob("*.jpg"))[:30]}
    for i, f in enumerate(pdf_names):
        key_of[f.name] = f"batch.pdf#p{i + 1}"
    wrong = flagged = total = 0
    for name, v in truth.items():
        rl = lect[key_of[name]]
        for rv, a in zip(v["respuestas"], rl["respuestas"]):
            total += 1
            if rv["m"] != a["m"] or rv["anular"] != a["anular"]:
                wrong += 1
                flagged += bool(a.get("dudas"))
                print("   misread", name, rv, a, "ink", v["tinta"])
    check("Answers read as filled in (>= 99.5 %)", wrong <= total * 0.005,
          f"{wrong}/{total} wrong, {flagged} of them flagged as doubtful")
    RESULTS["data"]["reading"].update(answers=total, wrong=wrong, wrong_flagged=flagged)
    hojas = [r for r in res if r["estado"] != "vacia"]
    ident = sum(1 for r in hojas if r.get("alumno"))
    check("Students identified from the ID grid", ident == 36, ident)
    RESULTS["data"]["sheet_states"] = {s: sum(1 for r in hojas if r["estado"] == s) for s in ("ok", "revisar", "error")}
    RESULTS["data"]["incidences"] = sorted({i for r in hojas for i in r["incidencias"]})

    # ------------------------------------------------------------ review screen and manual corrections
    from urllib.parse import quote
    k = next(r["clave"] for r in hojas if r["clave"].startswith("batch"))
    kq = quote(k)
    page = cl.get(f"/p/{pid}/hoja/{kq}").get_data(as_text=True)
    page_st = cl.get(f"/p/{pid}/hoja/{kq}?modo=alumno").get_data(as_text=True)
    check("Review screen and student mode render", "svg" in page and "modo-alumno" in page_st)
    before = next(r for r in calificar_todo(p) if r["clave"] == k)
    q0 = before["preguntas"][0]
    target = q0["correctas"] if q0["estado"] != "bien" else ("A" if q0["correctas"] != "A" else "B")
    after = cl.post(f"/api/p/{pid}/hoja/{kq}", json={"respuesta": {"n": 0, "valor": target}}).get_json()
    check("Click-to-correct changes the answer and the grade immediately",
          after["preguntas"][0]["manual"] and after["nota"] != before["nota"], f"{before['nota']} -> {after['nota']}")
    other = next(a for a in p.alumnos() if a.documento != (before.get("alumno") or {}).get("documento"))
    after2 = cl.post(f"/api/p/{pid}/hoja/{kq}", json={"documento": other.documento}).get_json()
    check("Student reassigned manually", after2["alumno"]["documento"] == other.documento and after2["id_tipo"] == "manual")
    after3 = cl.post(f"/api/p/{pid}/hoja/{kq}", json={"modelo": 3}).get_json()
    check("Version overridden manually", after3["modelo"] == 3)
    cl.post(f"/api/p/{pid}/hoja/{kq}", json={"modelo": None, "documento": None})
    after4 = cl.post(f"/api/p/{pid}/hoja/{kq}", json={"visto": True}).get_json()
    check("Sheet marked as reviewed", after4["visto"] and after4["estado"] == "ok")
    # re-reading keeps manual revisions
    leer_proyecto(p, forzar=True)
    kept = next(r for r in calificar_todo(p) if r["clave"] == k)
    check("Re-reading all scans keeps manual corrections", kept["preguntas"][0]["manual"]
          and kept["preguntas"][0]["marcadas"] == target)
    # duplicate student
    k2 = next(r["clave"] for r in hojas if r["clave"] != k)
    dup_doc = next(r for r in calificar_todo(p) if r["clave"] == k)["alumno"]["documento"]
    cl.post(f"/api/p/{pid}/hoja/{quote(k2)}", json={"documento": dup_doc})
    dup = [r for r in calificar_todo(p) if any("more than one" in i or "más de una" in i for i in r["incidencias"])]
    check("Duplicate student flagged on both sheets", len(dup) >= 2)
    cl.post(f"/api/p/{pid}/hoja/{quote(k2)}", json={"documento": None})

    # ------------------------------------------------------------ statistics, voiding and key correction
    est = estadistica(p)
    check("Statistics per bank question", len(est) > 20 and all("elecciones" in e for e in est), len(est))
    RESULTS["data"]["stats_sample"] = [{x: e[x] for x in ("id", "n", "acierto", "elecciones", "bien", "parcial", "mal",
                                                         "blanco")} for e in est[:5]]
    cl.get(f"/p/{pid}/estadistica")
    notes0 = {r["clave"]: r["nota"] for r in calificar_todo(p) if r.get("nota") is not None}
    qid = est[0]["id"]
    cl.post(f"/p/{pid}/pregunta/{qid}", data={"accion": "anular"})
    notes1 = {r["clave"]: r["nota"] for r in calificar_todo(p) if r.get("nota") is not None}
    changed = sum(notes0[c] != notes1[c] for c in notes0)
    check("Voiding a question recalculates every grade", qid in p.config()["anuladas"] and changed > 0,
          f"question {qid}: {changed} grades changed")
    kept2 = next(r for r in calificar_todo(p) if r["clave"] == k)
    check("Manual corrections survive voiding", kept2["preguntas"][0]["manual"])
    cl.post(f"/p/{pid}/pregunta/{qid}", data={"accion": "anular"})
    qid2 = next(e["id"] for e in est if e["correctas_banco"] == "A")
    cl.post(f"/p/{pid}/pregunta/{qid2}", data={"accion": "clave", "clave": "B"})
    notes2 = {r["clave"]: r["nota"] for r in calificar_todo(p) if r.get("nota") is not None}
    printed = [(item["perm"], item["correctas"]) for mod in p.generado()["modelos"] for item in mod["preguntas"]
               if item["id"] == qid2]
    from examtool.calificar import clave_impresa
    remap_ok = all(clave_impresa({"id": qid2, "perm": perm, "correctas": c}, p.config()) == "ABCD"[perm.index(1)]
                   for perm, c in printed)
    check("Corrected key mapped to each version's printed order", remap_ok and notes2 != notes0)
    cl.post(f"/p/{pid}/pregunta/{qid2}", data={"accion": "clave", "clave": "A"})
    check("Restoring the key restores the grades",
          {r["clave"]: r["nota"] for r in calificar_todo(p) if r.get("nota") is not None} == notes0)

    # ------------------------------------------------------------ export
    r = cl.get(f"/p/{pid}/descargar/notas.xlsx")
    xf = WORK / "grades.xlsx"
    xf.write_bytes(r.data)
    wb = load_workbook(xf)
    check("Excel export with all sheets", wb.sheetnames == ["Grades", "Class list", "Answers", "Points per question",
                                                            "Statistics", "Settings"] or len(wb.sheetnames) == 6,
          wb.sheetnames)
    RESULTS["data"]["excel_sheets"] = wb.sheetnames
    cls = wb.worksheets[1]
    np_count = sum(1 for row in cls.iter_rows(min_row=2, values_only=True) if row[2] in ("NP", "Absent", "NS"))
    check("Absent students marked in the class list", np_count == 4, np_count)

    # ------------------------------------------------------------ regenerate protection
    g0 = p.generado()["codigo"]
    cl.post(f"/p/{pid}/generar")
    check("Regeneration blocked once scans exist (without confirmation)", p.generado()["codigo"] == g0)

    # ------------------------------------------------------------ independent exam language
    r = cl.post("/nuevo", data={"titulo": "Examen final", "tipo": "modelos", "idioma_examen": "es", "copiar_de": pid})
    pid_es = r.headers["Location"].rsplit("/", 1)[-1]
    pe = Proyecto(BASE / pid_es)
    check("New exam copied from a previous one (bank, list and settings)",
          len(pe.preguntas()[0]) == 40 and len(pe.alumnos()) == 40 and pe.config()["modelos"][2]["grupos"] == "T,R"
          and not pe.config()["anuladas"])
    cl.post(f"/p/{pid_es}/generar")
    with fitz.open(pe.ruta("examenes.pdf")) as d:
        txt = d[0].get_text()
    check("Printed exam in Spanish while the interface is in English", "Modelo" in txt and "Anular" in txt)

    # ------------------------------------------------------------ personalised exams
    r = cl.post("/nuevo", data={"titulo": "Personalised exam", "tipo": "personalizado", "idioma_examen": "en"})
    pid_p = r.headers["Location"].rsplit("/", 1)[-1]
    pp = Proyecto(BASE / pid_p)
    rng = random.Random(3)
    passed = {i: ", ".join(sorted(rng.sample([str(x) for x in range(1, 11)], rng.choice([0, 2, 4, 6])), key=int))
              for i in range(40)}
    cl.post(f"/p/{pid_p}/subir/preguntas", data={"fichero": (io.BytesIO(xlsx_bytes(demo_data.write_bank)), "b.xlsx")},
            content_type="multipart/form-data")
    cl.post(f"/p/{pid_p}/subir/alumnos",
            data={"fichero": (io.BytesIO(xlsx_bytes(demo_data.write_students, passed)), "c.xlsx")},
            content_type="multipart/form-data")
    form_p = dict(form, tipo="personalizado", reserva="3", modelo_nombre=["A", "B"], modelo_grupos=["T", "R"],
                  titulo="Personalised exam")
    cl.post(f"/p/{pid_p}/config", data=form_p)
    cl.post(f"/p/{pid_p}/generar")
    gp = pp.generado()
    per = [mm for mm in gp["modelos"] if mm.get("alumno")]
    spare = [mm for mm in gp["modelos"] if mm.get("reserva")]
    excl_ok = all(not ({q["id"] for q in mm["preguntas"]} & set(mm["superadas"])) and
                  len(mm["preguntas"]) + len(mm["superadas"]) == 20 for mm in per)
    check("One exam per student plus 3 spare copies", len(per) == 40 and len(spare) == 3)
    check("Passed questions removed from each personalised exam", excl_ok)
    sizes = sorted(len(mm["preguntas"]) for mm in per)
    RESULTS["data"]["personalised_sizes"] = {"min": sizes[0], "max": sizes[-1], "spare": len(spare)}
    with fitz.open(pp.ruta("examenes.pdf")) as d:
        t1 = d[0].get_text()
    check("Student name printed on the personalised sheet", per[0]["alumno"]["nombre"].split(",")[0] in t1)
    simular(pp, 12, semilla=9)
    leer_proyecto(pp)
    rp = [r for r in calificar_todo(pp) if r["estado"] != "vacia"]
    ok_p = True
    for r in rp:
        mod = gp["modelos"][r["modelo"]]
        n_valid = len(r["preguntas"]) + r["cuenta"]["superadas"]
        same = (r.get("alumno") or {}).get("documento") == mod["alumno"]["documento"] if mod.get("alumno") else True
        ok_p &= n_valid == 20 and same
    check("Personalised sheets identified by QR and passed questions counted as correct", ok_p and len(rp) == 12)
    RESULTS["data"]["personalised_example"] = [{"student": r["alumno"]["nombre"], "passed": r["cuenta"]["superadas"],
                                                "on_sheet": len(r["preguntas"]), "grade": r["nota"]} for r in rp[:5]]

    # ------------------------------------------------------------ recycle bin
    r = cl.post("/borrar", data={"ids": [pid_es]})
    check("Deleted exams go to the recycle bin", not (BASE / pid_es).exists()
          and any((BASE / ".papelera").glob(pid_es + "-*")))

    # ------------------------------------------------------------ translations
    import subprocess
    out = subprocess.run([sys.executable, str(C.RAIZ / "herramientas" / "revisar_traducciones.py"), "en"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    check("English translation complete", " 0 sin traducir" in out, out.splitlines()[0] if out else "")
    RESULTS["data"]["translations"] = out.splitlines()[0] if out else ""

    passed_n = sum(c["ok"] for c in RESULTS["checks"])
    RESULTS["summary"] = f"{passed_n}/{len(RESULTS['checks'])} checks passed"
    print(RESULTS["summary"])
    (WORK / "functional_results.json").write_text(json.dumps(RESULTS, indent=1, ensure_ascii=False, default=str),
                                                 encoding="utf-8")
    return BASE, pid, pid_p


def _raises(f):
    try:
        f()
    except ValueError:
        return True
    return False


if __name__ == "__main__":
    main()
