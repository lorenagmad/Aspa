# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Compara las lecturas con la solución de simular_escaneos.py."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from examtool.proyecto import Proyecto
from examtool.lector import leer_proyecto

proy = Proyecto(Path(sys.argv[1]))
t = time.time()
leer_proyecto(proy, forzar=True)
print(f"lectura: {time.time() - t:.1f} s")
verdad = json.loads(proy.ruta("simulacion.json").read_text(encoding="utf-8"))
lect = proy.lecturas()
err_c = err_id = err_qr = total = 0
for nombre, v in verdad.items():
    r = lect[nombre]
    if not r.get("ok"):
        print(nombre, "ERROR", r["error"]); continue
    if not r["qr"] or r["qr"]["modelo"] != v["modelo"]:
        err_qr += 1; print(nombre, "QR", r.get("qr_texto"))
    if v["digitos"] and r["id_leido"] != v["digitos"]:
        err_id += 1; print(nombre, "ID", r["id_leido"], "!=", v["digitos"])
    for q, (rv, rl) in enumerate(zip(v["respuestas"], r["respuestas"])):
        total += 1
        if rv["m"] != rl["m"] or rv["anular"] != rl["anular"]:
            err_c += 1
            print(nombre, f"P{q+1}", "real", rv, "leído", rl, r["ratios"]["resp"][q], "tinta", v["tinta"])
print(f"QR fallidos {err_qr}/{len(verdad)}  ID fallidos {err_id}/{len(verdad)}  preguntas mal leídas {err_c}/{total}")
