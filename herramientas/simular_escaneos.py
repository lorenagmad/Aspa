# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Crea escaneos simulados de un proyecto ya generado, para probar el lector sin imprimir.

    python herramientas/simular_escaneos.py <carpeta_proyecto> [n_hojas] [semilla]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from examtool.proyecto import Proyecto  # noqa: E402
from examtool.simulacion import simular  # noqa: E402

if __name__ == "__main__":
    p = Proyecto(Path(sys.argv[1]))
    n = simular(p, int(sys.argv[2]) if len(sys.argv) > 2 else 12, int(sys.argv[3]) if len(sys.argv) > 3 else 3)
    print(f"{n} escaneos simulados en {p.ruta('escaneos')}")
