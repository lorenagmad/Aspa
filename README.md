# Aspa · multiple-choice exams

*[Versión en español](README.es.md)*

**Aspa** is a local web application to **generate, print, read and grade multiple-choice
exams**. It runs on the teacher's own computer (Windows, macOS or Linux), opens in the browser and
needs neither Excel nor an internet connection once installed. Scans and grades never leave the
computer.

![License: AGPL-3.0-or-later](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue)

## Features

- **Exams from a question bank** in Excel or CSV: several versions (A, B, C…) built from question
  groups, shuffled questions and options («All of the above» / «None of the above» stay in place),
  images printed at the end of the exam, and answer keys by version.
- **Personalised exams**: one exam per student, with their name printed on the sheet and without
  the questions they have already passed in class (quizzes, activities…), which count as correct.
  Spare non-personalised copies for students not on the list.
- **Robust answer sheet**: four ArUco fiducial markers, a QR code with exam, version and copy,
  a 10-digit ID grid that works with national IDs, residence cards and passports, and a separate
  «Cancel» box to void or change an answer.
- **Optical mark recognition** with OpenCV from scanners or **mobile-phone photos**: perspective
  correction, local alignment to the printed boxes (paper curvature and lens distortion),
  illumination normalisation and per-sheet adaptive thresholds. Blank and question pages are
  ignored; doubtful marks are flagged for review.
- **Grading**: configurable scoring, partial credit for multiple-answer questions, voided questions
  and corrected answer keys, all recalculated instantly without losing manual corrections.
- **Review screen**: the straightened scan with the result overlaid, click-to-correct, a clean
  «review with the student» mode and optional **explanations of the correct answer**.
- **Statistics by question** and export of grades to Excel.
- **Multilingual**: interface in Spanish and English, plus an independent language for the
  printed exam. New languages are added with a single JSON file.

## Installation

1. Install **Python 3.9 or later** from <https://www.python.org/downloads/>
   (on Windows, tick «Add Python to PATH»).
2. Download or clone this repository.
3. Start Aspa:
   - **Windows:** double-click `iniciar.bat`.
   - **macOS:** double-click `iniciar.command` (if blocked: right-click → Open).
   - **Linux:** `./iniciar.sh`.

The first run installs the dependencies (a couple of minutes); then the browser opens at
`http://127.0.0.1:5077`. To stop Aspa, click **Close Aspa** at the top right.

Exams are stored in the `ExamenesTest` folder of the user's home directory. Another folder can be
used with `--carpeta`, for example `iniciar.bat --carpeta "D:\Exams"`.

## Workflow

1. **Create the exam** (optionally starting from a previous one).
2. **Step 1:** upload the question bank and the class list (and images, if any).
3. **Step 2:** settings: exam type, printed-exam language, scoring and versions.
4. **Step 3:** generate the PDF to print and the answer keys.
5. **Step 4:** drag the scans into the browser; they are read and graded automatically. Review
   and correct each sheet, or show it to the student.
6. **Step 5:** statistics by question; void questions or fix keys.
7. **Step 6:** export grades to Excel.

Templates (blank and with examples) and help pages for the question bank, the student list and
personalised exams are available from the home screen, and also in the `ejemplos/` folder.

## Adding a language

```
python herramientas/revisar_traducciones.py fr --nuevo "Français"
```

This creates `idiomas/fr.json` with every text of the program. Fill in the translations, set the
decimal separator in `"_decimal"`, and copy `templates/ayuda/en` to `templates/ayuda/fr` to
translate the three help pages. Anything not yet translated is shown in English.

## Project structure

```
app.py                  web application (Flask)
examtool/layout.py      answer-sheet geometry, shared by the PDF generator and the reader
examtool/lector.py      optical mark recognition (OpenCV: ArUco, QR, ink measurement)
examtool/pdf.py         exams and answer keys in PDF (ReportLab)
examtool/proyecto.py    projects, settings, versions and personalised exams
examtool/calificar.py   scoring and statistics
examtool/banco.py       question bank and student list
examtool/exportar.py    Excel export
examtool/plantillas.py  Excel templates
examtool/i18n.py        languages (translations in idiomas/*.json)
examtool/simulacion.py  simulated filled-in scans for testing
herramientas/           development tools (simulation, evaluation, translations)
```

The reader can be tested without printing anything:

```
python herramientas/simular_escaneos.py <exam_folder> 40
python herramientas/evaluar_simulacion.py <exam_folder>
```

## License

Aspa is free software: you can redistribute it and/or modify it under the terms of the
**GNU Affero General Public License** as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version. See [`LICENSE`](LICENSE).

In practice, anyone can use, study and modify Aspa, but whoever distributes a modified version,
or offers it as a service over a network, must publish its source code under the same license.

Third-party libraries, all with compatible licenses: Flask (BSD-3-Clause), OpenCV (Apache-2.0),
NumPy (BSD-3-Clause), ReportLab (BSD), openpyxl (MIT) and PyMuPDF (AGPL-3.0).

## Authors

- Lorena Gutiérrez Madroñal
- Rubén Baena Pérez
- José Miguel Mota Macías

## Citation

If you use Aspa in your teaching or research, please cite it using the metadata in
[`CITATION.cff`](CITATION.cff) (GitHub shows it under «Cite this repository»).
