# Comparison table: verified cells (checked 22 October 2026)

Every cell for the other tools comes from the tool's own documentation, repository or website (sources below).
Aspa's row was checked against its code.
Legend: ✓ yes · ◐ partial · ✗ no · ? not documented (do **not** write "no" in the paper) · N/A the tool does not produce exam papers.

## Columns

| ID | Column | Definition used for checking |
|---|---|---|
| C1 | Personalisation by student progress | One exam per student that omits the questions that student passed, which then count as correct when grading, built in |
| C2 | No programming/LaTeX required | The full create → grade workflow works from a GUI or spreadsheets |
| C3 | Images | Images can be included in the exam paper |
| C6 | Scanner + phone reading | Documented reading of both scanner images and phone photographs |
| C7 | Interactive review | GUI showing the scan with detected marks, editable |
| C8 | Real-time recalculation | Changing the key, voiding a question or changing scoring regrades without rescanning |
| C9 | Local processing | Student data and scans are processed on the teacher's machine; no third-party transfer |

## Table

| Tool | C1 | C2 | C3 | C6 | C7 | C8 | C9 | Generates exams | Licence |
|---|---|---|---|---|---|---|---|---|---|
| **Aspa** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | AGPL-3.0 |
| AMC | ✗ (only with hand-written LaTeX) | ◐ (questions in LaTeX/AMC-TXT) | ✓ | ? | ✓ | ✓ | ✓ | ✓ | GPLv2+ |
| R/exams | ✗ (only with R code) | ✗ | ✓ | ? | ◐ (from R) | ◐ (R code) | ✓ | ✓ | GPL-2/3 |
| FormScanner | ✗ | ◐ (cannot create exams) | N/A | ? | ✓ | ? | ✓ | ✗ | GPLv3 |
| OMRChecker | ✗ | ✗ (CLI + JSON) | N/A | ✓ | ✗ | ◐ | ✓ | ✗ | MIT |
| ZipGrade | ✗ | ✓ | N/A | ✓ | ✓ | ? | ✗ (syncs by default; can be disabled) | answer sheets only | proprietary |
| Remark OMR | ✗ | ✓ | N/A | ? | ✓ | ✓ | ✓ (optional cloud OCR add-on) | ✗ | proprietary |
| Eyegrade | ✗ (models A, B, C… only) | ◐ (questions in XML + LaTeX template, or word processor with manual configuration) | ✓ | ◐ (live webcam only; scans/photos not documented) | ✓ | ? | ✓ | ✓ | GPLv3+ |

Eyegrade cells were checked against its user manual (eyegrade.org/doc/user-manual/, §§2, 2.4, 2.8, 4.1.1, 4.2, 5.2) on 22 Oct 2026.

## What this changes in the paper

1. **The unique claim survives, provided it is worded precisely.** No tool checked offers C1 as a **built-in, no-code** feature. AMC can do something similar only if the teacher writes LaTeX: its grading normalises each copy by its own perfect score, so omitted questions are neutral, not credited. R/exams needs an R loop. OMRChecker can give "bonus marks" per folder by editing JSON, but it does not generate exams.
   - Safe wording: "none provides it as a built-in feature that requires no code".
   - Avoid "no tool can".
2. **ZipGrade:** "syncs scores, student information and scan images to its servers by default" (privacy policy, effective 3 June 2021). Teachers can turn the sync off.
   - Do **not** write "ZipGrade users must put student data online".
3. **Phone reading:** only ZipGrade and OMRChecker document it. For AMC, R/exams, FormScanner and Remark it is undocumented. Write "documented support", never "cannot".
4. **Correction to the current draft:** the draft says FormScanner and OMRChecker "neither generate nor grade versioned exams". OMRChecker **does grade** (`evaluation.json`, negative marking, weighted combinations). Rewrite as "read and score answer sheets but do not generate exams".
5. **The draft's AMC claim stands with nuance:** "runs only on Linux and macOS". Windows is possible only through WSL or a VM.

## Columns dropped (author's decision, 22 Oct 2026)

- **C4 Weighting:** dropped, because every tool that grades offers it.
- **C5 Languages:** dropped for the v1.0 comparison. Aspa accepts any number of languages as JSON files, but v1.0 ships es and en, while AMC has 8+ and R/exams about 34.
- **C7 Interactive review** and **C8 Recalculation:** kept, although AMC and Remark OMR match Aspa on both.

The verified C4/C5 cells for the other tools remain in the sources below, in case a reviewer asks.

## How to use the two closest precedents (author to decide)

- **O'Malley (2025)** *supports* the method: an instructor at another university arrived independently at "omit what the student already passed", from 2016. His tooling is a Word mail merge plus grading by hand, which illustrates the author's W2 point: without software, the teacher has to assemble each exam and keep track of what each student already passed.
- **Alonso-Fernandez & Bigun (2022)** is the closest *system*: passing weekly paper quizzes exempts students from the final exam or from the matching part of it. Its granularity is the exam or part, not the question, and its software is not released.
- Aspa's position against both: it automates the whole cycle at question level (generate → read → credit the passed questions → grade), with no code and as released open software.

## Moodle Offline quiz: excluded (author's decision, 22 Oct 2026)

Left out of the table and the paper. Verified cells, kept here in case a reviewer asks:
- C1 ✗: up to 6 groups, no per-student exams.
- C2 ✓, C3 ✓, C4 ✓, C5 ◐, C6 ? (scanned images only).
- C7 ✓, C8 ✓ ("existing results were regraded automatically").
- C9 ◐: processing on the institution's Moodle server.
- GPLv3.

Answer if raised: it needs a Moodle server and works with groups, not with per-student exams based on progress.

## New related work found by the search

| Ref | Why it matters | Status |
|---|---|---|
| F. Alonso-Fernandez, J. Bigun, "Continuous Examination by Automatic Quiz Assessment Using Spiral Codes and Image Processing", IEEE EDUCON 2022, arXiv:2201.11228 | **Closest prior art.** Paper weekly quizzes; passing them lets a student skip the final exam or the matching part of it; individualised quizzes; automatic reading. No per-question removal credited as correct; code not released. | Full text checked; the exemption is stated in Sections I, IV and V |
| J. Arias Fisteus, A. Pardo, N. Fernández García, "Grading Multiple Choice Exams with Low-Cost and Portable Computer-Vision Techniques", J. Sci. Educ. Technol. 22(4) (2013) 560–571, doi:10.1007/s10956-012-9414-8 (Eyegrade) | Closest open-source system: Python, computer vision, webcam, a Spanish university, GPLv3. Exams are generated from LaTeX. | Cells verified against the user manual |
| F. Teubl, V. Batista, F. Zampirolli, "MakeTests: Generate and Correct Individualized Questions with Many Styles", CSEDU 2021, 245–253, doi:10.5220/0010337902450253 | Open-source individualised (parametric) exams, not based on progress | Found by the search |
| Gradescope bubble sheets (Turnitin) | The dominant cloud alternative; expect "why not Gradescope?" | Checked through university guides only |
| P. O'Malley, "Individualized Optional Retake Method for Final Exams", ASEE Midwest 2025, doi:10.18260/1-2-1153-57848 | **Independent pedagogical precedent** (used since 2016; Statics and Dynamics, 38 and 35 students). Each student gets an individualised final exam containing only the topics where they lost points. A topic already solved correctly does not appear ("would not see a truss problem on the final"), and its mid-semester score stands. Retakes are optional, and the new score replaces the old one. Open-ended problems, graded by hand; exams built by **Word mail merge from the gradebook**; no OMR, no software release. | DOI verified in Crossref; full text read (PDF supplied by the author, 22 Oct 2026) |
| Y. Hernández-Mier et al., J. Imaging 11(9):308 (2025), doi:10.3390/jimaging11090308 | Recent OMR accuracy baseline (99.95%) | Optional |

The search found no SoftwareX or JOSS paper on a paper-exam OMR/generation tool. Do not claim "first in SoftwareX" without checking again just before submission.

## Sources (other tools)

- AMC: auto-multiple-choice.net/doc/specific/, /doc/usage/, /doc/amc-txt/, /doc/scoring/, /doc/latex/, /install/
- R/exams: CRAN `exams` man pages (exams2nops, exams_eval, nops_scan, nops_fix, nops_eval), r-exams.org/templates/
- FormScanner: sourceforge.net/projects/formscanner/ and its CHANGELOG wiki; sites.google.com/site/examgrader
- OMRChecker: github.com/Udayraj123/OMRChecker (README; wiki "[v2] About Evaluation")
- ZipGrade: zipgrade.com/privacy/ (effective 3 June 2021; checked again 22 Oct 2026); support.zipgrade.com articles 360047612211, 21880513310989, 45705262770445, 201168729, 37328081315981, 201168769
- Remark OMR: Remark Office OMR User's Guide (2025), 12.1 release notes, products/office-omr/test-grading/
- Moodle Offline quiz: github.com/academic-moodle-cooperation/moodle-mod_offlinequiz (lang/en strings); docs.moodle.org Multiple Choice question type
- Eyegrade: eyegrade.org (home) and eyegrade.org/doc/user-manual/
- O'Malley: api.crossref.org/works/10.18260/1-2-1153-57848
- Aspa: `examtool/calificar.py:141-145` (passed questions credited), `examtool/pdf.py` (images), no outbound network calls in `app.py`/`examtool`
