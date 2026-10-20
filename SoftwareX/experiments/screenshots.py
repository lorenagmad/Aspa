# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Screenshots of the running web interface (Playwright with the installed Chrome).

    python SoftwareX/experiments/screenshots.py <aspa_home> <out_dir> [port]

Aspa must be running on that port with --carpeta <aspa_home>.
"""
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from examtool.calificar import calificar_todo  # noqa: E402
from examtool.proyecto import Proyecto  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

home, out = Path(sys.argv[1]), Path(sys.argv[2])
port = sys.argv[3] if len(sys.argv) > 3 else "5099"
URL = f"http://127.0.0.1:{port}"
out.mkdir(parents=True, exist_ok=True)

pid = next(d.name for d in home.iterdir() if d.name.startswith("software-engineering-final-exam"))
pid_p = next(d.name for d in home.iterdir() if d.name.startswith("personalised-exam"))
proy = Proyecto(home / pid)
res = [r for r in calificar_todo(proy) if r.get("preguntas") and not r.get("visto")]


def variety(r):
    st = {p["estado"] for p in r["preguntas"]}
    expl = any(p["estado"] in ("mal", "parcial", "blanco") and p["id"] in {"2", "3", "6", "9", "12", "15"}
               for p in r["preguntas"])
    return (len(st) + 2 * expl + ("revisar" in st), r["clave"].startswith("escaneo"))


sheet = max(res, key=variety)
print("sheet:", sheet["clave"], {p["estado"] for p in sheet["preguntas"]})
expl_q = next((i for i, p in enumerate(sheet["preguntas"])
               if p["estado"] in ("mal", "parcial", "blanco") and p["id"] in {"2", "3", "6", "9", "12", "15"}), 0)

with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    pg.goto(URL + "/")
    pg.screenshot(path=str(out / "ui_home.png"), full_page=True)
    pg.goto(f"{URL}/p/{pid}")
    pg.screenshot(path=str(out / "ui_prepare.png"), full_page=True)
    pg.goto(f"{URL}/p/{pid_p}")
    pg.screenshot(path=str(out / "ui_prepare_personalised.png"), full_page=True)
    pg.goto(f"{URL}/p/{pid}/corregir?orden=estado")
    pg.screenshot(path=str(out / "ui_grading.png"), full_page=True)
    pg.goto(f"{URL}/p/{pid}/estadistica")
    pg.screenshot(path=str(out / "ui_statistics.png"), full_page=True)
    pg.goto(f"{URL}/p/{pid}/hoja/{quote(sheet['clave'])}")
    pg.wait_for_timeout(500)
    pg.hover(f"#filas tr[data-i='{expl_q}']")
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(out / "ui_review.png"), full_page=True)
    pg.goto(f"{URL}/p/{pid}/hoja/{quote(sheet['clave'])}?modo=alumno")
    pg.wait_for_timeout(500)
    pg.hover(f"#filas tr[data-i='{expl_q}']")
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(out / "ui_review_student.png"), full_page=True)
    pg.goto(f"{URL}/ayuda/preguntas")
    pg.screenshot(path=str(out / "ui_help_bank.png"), full_page=True)
    b.close()
print("sheet", sheet["clave"], "question", expl_q + 1)
