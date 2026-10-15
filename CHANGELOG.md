# Changelog

All notable changes to Aspa are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-15

First public release.

### Added
- Exam generation in PDF from a question bank in Excel or CSV: several versions, shuffled
  questions and options (options such as «All of the above» stay in place), images printed at
  the end of the exam and answer keys by version.
- Personalised exams: one exam per student, with their name printed and without the questions
  they have already passed in class, which count as correct. Spare non-personalised exams.
- Answer sheet with four ArUco fiducial markers, a QR code identifying exam, version and copy,
  a 10-digit ID grid (national ID, residence card or passport digits) and a separate «Cancel» box.
- Optical mark recognition with OpenCV from scanners or mobile-phone photos: perspective
  correction, local alignment to the printed boxes (paper curvature, lens distortion),
  illumination normalisation and adaptive thresholds. Blank and question pages are ignored.
- Grading with configurable scoring, partial credit for multiple-answer questions, voided
  questions and corrected answer keys, all recalculated instantly.
- Review screen with the scan overlaid with the result, click-to-correct, «review with the
  student» mode and optional explanations of the correct answer.
- Statistics by question and export of grades to Excel.
- Interface in Spanish and English, with an independent language for the printed exam.
  New languages can be added with a JSON file (`herramientas/revisar_traducciones.py`).
- Templates and help pages for the question bank, the student list and personalised exams.
