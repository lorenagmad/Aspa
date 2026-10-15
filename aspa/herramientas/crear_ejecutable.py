# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Crea un ejecutable de Aspa que no necesita tener Python instalado.

    python herramientas/crear_ejecutable.py

El resultado queda en dist/: Aspa.exe en Windows, Aspa en macOS y Linux.
PyInstaller solo genera ejecutables para el sistema en el que se ejecuta: para obtener el de
Windows hay que ejecutar este script en Windows (por ejemplo, con crear_ejecutable.bat).
"""
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    datos = []
    for carpeta in ("templates", "static", "idiomas", "ejemplos"):
        datos += ["--add-data", f"{RAIZ / carpeta}{os.pathsep}{carpeta}"]
    orden = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
             "--name", "Aspa", "--distpath", str(RAIZ / "dist"), "--workpath", str(RAIZ / "build"),
             "--specpath", str(RAIZ / "build"), *datos,
             # módulos que se cargan de forma dinámica y PyInstaller no detecta solo
             "--collect-submodules", "reportlab.graphics.barcode",
             "--collect-submodules", "reportlab.pdfbase",
             str(RAIZ / "app.py")]
    subprocess.check_call(orden, cwd=RAIZ)
    print("\nEjecutable creado en", RAIZ / "dist")


if __name__ == "__main__":
    main()
