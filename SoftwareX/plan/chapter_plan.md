# Aspa — SoftwareX Chapter Plan + INSIGHT Collection

Produced in ARS `plan` mode (Socratic dialogue), 21–22 October 2026.
All claims below are in the author's words or were explicitly confirmed by the author.
This is a plan, not text for the article: the rewrite happens after the February trial.

---

## 1. Configuration

| Item | Decision |
|---|---|
| Journal / type | SoftwareX, Original Software Publication (OSP template) |
| Language | English |
| Structure | The 5 mandatory template sections: Motivation and significance · Software description · Illustrative examples · Impact · Conclusions |
| Length | ≤ 4,000 words (priority) and ≤ 6 pages excluding metadata, tables, figures and references |
| Figures | Max. 6 → plan uses 4 |
| Submission timing | After the February trial; "we have no deadline" — wait until all evidence is in |

## 2. Thesis and contribution

- **Thesis (confirmed):** "Aspa is a programme for generating and marking paper-based multiple-choice exams, which allows teachers to adapt it to the needs of their subject."
- **Thesis type:** comparative, against other paper-based exam tools. Main strength: flexibility; second: efficiency. Moodle and online quizzes are out of scope.
- **Distinguishing feature:** personalisation according to each student's progress. Aspa is criterion-neutral: "it's the teacher who decides which questions the student has passed."
- **Contribution (W1):** "Aspa is a highly flexible tool that is easy to understand, and its configuration enables the continuous assessment required for the modules to be applied to students."
- **Gap value (W2):** without Aspa, the teacher "would have to remove or cross out the questions the student has already completed … and remember, when marking their work, that these have already been completed. … with a large group of students, it is quite likely that there will be confusion and mistakes."
- **Audience (W3):** "Readers may choose to use Aspa in their courses to speed up the marking of exams and improve the efficiency of the marking process."
- **Closing line:** "Aspa: the exam generation and marking tool that can be adapted to assess any subject."

## 3. Chapter Plan

### Section 1 — Motivation and significance (~550–650 words; now ~450)

- **Core argument:** efficiency is the hook and flexibility is the gap. Marking is slow, and "manually tailoring an exam to each student multiplies the work involved in setting and marking it, and in the end it simply doesn't get done." None of the existing tools personalises exams "according to the assessment in the subjects and the student's progress."
- **Evidence:**
  1. MCQ literature already in the draft (Haladyna, Ebel, Burton): the marking burden.
  2. Two rationales for personalisation: mastery/exemption (Bloom 1968) **and** reward for participation in gamified quizzes. Cite **Gutiérrez-Madroñal & Collado Machuca (2018)**, verified: Kahoot quizzes, a ranking per topic, 0–5 questions removed per topic, counted as correct. Aspa is criterion-neutral.
  3. Related software, plus the **comparison table** (see § 5).
  4. Provenance: an in-house Excel-macro tool (created by J. C. Collado Machuca, used by the author since 2019, ≥3 subjects, ~1,300+ students). Personalisation was done by hand from 2017/18. The tool's problems became Aspa's requirements. Comparison is qualitative only.
  5. The 6-step workflow stays here as the template's "experimental setting".
- **Counter-argument → response:** "Existing tools already personalise (AMC)." → "Unlike AMC, Aspa generates the results based on the list of questions that have been answered correctly, counting them as correct without the need for any code."
- **Strength:** Moderate, rising to Strong once the related-software check is done.

### Section 2 — Software description (~850–950 words; now ~1,100)

- **Core argument:** each limitation of the predecessor is solved by a visible design decision:

  | Predecessor problem (author's words, condensed) | Aspa design decision |
  |---|---|
  | Configuration by editing cells, running macros from the Developer tab, deleting parts manually, worksheets of unclear purpose | One configuration form; question bank and class list uploaded as spreadsheets with example templates |
  | Grading errors caused by misconfiguration | (1) simplified configuration; (2) grades never stored, always recomputed from plain files |
  | Students wrote their ID on the outer border, so the sheet could not be read | **Reading:** QR code + clean fiducial border. **Identification:** redesigned digit grid, matched to the class list with wildcards and one-digit suggestions. In personalised exams the QR code also identifies the student |
  | Multiple answers only via a workaround, and only 2 correct answers | Native multiple-answer keys (any subset of A–D), with template and explanation; partial or exact credit |

- **Structure:** architecture (figure) → functionalities in workflow order: bank and class list → **Settings** (versions or personalised, images, 2–4 options, multiple answers, exam language independent of the interface, global weighting for correct and wrong answers) → answer sheet → reading → identification and flags → grading → review, statistics, export.
- **Rewrite instructions (accepted, to apply in the later review):**
  - Condense the reading (OMR) paragraph to 2–3 sentences and move the parameters (CLAHE, 7 mm kernel, thresholds, 220 dpi, 8 px/mm) to the README.
  - State the grading rule in words and keep Table 2.
  - Add images; state 2–4 options. Weighting is global; no per-question weights.
- **No code snippet.**
- **Strength:** Strong.

### Section 3 — Illustrative examples (~600–700 words; now ~500)

- **Core argument:** a teacher can run a whole continuous-assessment course, up to a personalised final exam, on paper, with reliable automatic reading.
- **3.1 Teaching scenario** (fictitious data, the author's subject): bank with blocks → quizzes outside Aspa (Moodle) → teacher decides the passed questions → versioned **and** personalised final exams → scan → review → void or rekey → export. Timings on an **Intel Core i5-7600K @ 3.80 GHz**, an ordinary 2017 PC, which supports the efficiency claim.
- **Phone example:** marks published the same day for a small sitting. The broader claim ("any exam session") depends on the paired February scan.
- **3.2 Reading accuracy:** synthetic stress test (Table 3, 12,066 answers) **plus** February real sheets (anonymised): sheets read, flags by reason, manual corrections (`lecturas.json` vs `revision.json`).
- **Screencast:** MP4 of the 6-step workflow, using fictitious data.
- **Boundary with Section 4:** Section 3 = how Aspa performed; Section 4 = who uses it and what changed.
- **Strength:** Strong (synthetic); real-data part pending February.

### Section 4 — Impact (~600–700 words; now ~300)

- **Core argument:** "Fewer mistakes, and consequently less stress and time saved." Personalisation that would not be done by hand becomes routine.
- **Evidence:**
  1. Teaching-innovation project since 2017/18, with a citable publication (2018, verified). Personalisation done by hand until the predecessor existed.
  2. Author-approved sentence: "in most sittings some sheets had to be corrected by hand because of ID errors."
  3. February trial: 2–3 subjects, different degrees, 3 teachers. Expected needs: different question counts, no personalisation, possibly multiple answers. The trial itself demonstrates the thesis.
  4. Daily practice: preparation time, sheets reviewed by hand, flags by reason (measured in Section 3, interpreted here). Aspa removes the manual recalculation and re-entering of marks; the teacher only checks the sheets Aspa flags, each with a stated reason.
  5. Research enabled: effects of rank-based personalisation on participation and grades; item analysis from exported per-option data. Keep only what is really planned.
  6. Spread, stated honestly: early adoption; presentation at the UCA teaching-innovation call; AGPL; no commercial use.
- **Strength:** Moderate. Impact is still mostly prospective and there are no external users yet.

### Section 5 — Conclusions (~150–200 words)

- **Core argument:** "Aspa: the exam generation and marking tool that can be adapted to assess any subject."
- Recall: simpler configuration, a wider range of exam types, reliability and time saved, continuous assessment made routine. No new evidence.
- **Limits:** up to 30 questions and 2–4 options, sized to the exams of these subjects ("the number of questions does not exceed 30 and we provide up to 4 answer options").
- **Future work:** more questions; more options; use at other universities. "Validation on real scans" stays provisionally and is decided after February.
- **Remove:** Moodle export; "eliminate manual corrections" wording.

### Acknowledgements

- J. C. Collado Machuca, creator of the Excel predecessor and co-author of the 2018 project.

## 4. Argument stress test — final ratings

| # | Sub-argument | Defence agreed with the author | Rating |
|---|---|---|---|
| A1 | No paper-based tool personalises by student progress | Targeted related-software check + table; AMC needs code | Moderate → Strong after the check |
| A2 | Easiest | Both: "requires no programming or LaTeX" (table) **and** February usability data | Weak → Moderate |
| A3 | Most comprehensive | Comparison table; drop columns every tool ticks | Moderate, pending verification |
| A4 | Reader is reliable | Synthetic 12,066 answers + real February sheets | Strong |
| A5 | Fewer mistakes, time saved | Qualitative sentence + February measures | Moderate |
| A6 | Impact | 2018 publication + predecessor + multi-subject trial | Moderate |
| — | "Why not ZipGrade, if I only want speed?" | "Anyone using ZipGrade will be posting their students' data online" (verify ZipGrade's data storage) | — |

**Message order for the abstract:** flexibility (lead) → efficiency → local processing (no data leaves the teacher's computer). Do not write "GDPR-compliant".

## 5. Comparison table

Columns: personalisation by student progress · no programming/LaTeX required · images · scanner + phone reading · intuitive marking/review · real-time recalculation · local processing (no third-party data transfer). Weighting and languages dropped (author's decision, 22 Oct 2026).

Rows: Aspa, AMC, R/exams, FormScanner, OMRChecker, ZipGrade, Remark OMR, plus any tool found by the targeted search. Drop any column that every tool ticks. Every cell must be checked against the tool's documentation.

**Verified 22 Oct 2026 → see [comparison_table.md](comparison_table.md)** (cells, sources, wording consequences, new related work).

## 6. Word budget

| Section | Target | Current |
|---|---|---|
| 1 Motivation and significance | 550–650 | ~450 |
| 2 Software description | 850–950 | ~1,100 |
| 3 Illustrative examples | 600–700 | ~500 |
| 4 Impact | 600–700 | ~300 |
| 5 Conclusions | 150–200 | ~150 |
| **Total** | **2,750–3,200** (limit 4,000) | ~2,500 |

## 7. Pending tasks

**Now (before February)**
- [ ] Request the university's consent for the trial data, and find out whether individual student consent is also required.
- [ ] Confirm the two colleagues' participation and what each subject needs.
- [x] Targeted related-software search and cell verification (22 Oct 2026; see comparison_table.md). Eyegrade cells and O'Malley DOI verified; C4/C5 dropped, C7/C8 kept. Moodle Offline quiz: excluded (author's decision).
- [ ] Regenerate the Settings screenshots (a)(b) with fictitious data if needed.
- [ ] Record the screencast (fictitious data).
- [ ] Add the 2018 proceedings paper to the bibliography: pp. 54–59 (confirmed by the author), ISBN 978-84-09-04190-9.
- [ ] Fill `\todo`s: processor model (i5-7600K @ 3.80 GHz), address/department, link to an executable release.
- [ ] README: add the OMR parameters moved out of the paper.

**February trial (≥ 40 sheets per group)**
- [ ] Scan the same sheets with the scanner **and** the phone (paired comparison).
- [ ] Check every sheet by hand once (ground truth); compare `lecturas.json` with `revision.json`.
- [ ] Record preparation time, flags by reason, manual corrections, and the settings each subject used.

**Applied to the .tex on 22 Oct 2026 (changes that don't depend on February):** Motivation (bridge sentence, two rationales + 2018/O'Malley/Alonso-Fernandez citations, related work corrected, Eyegrade, predecessor), comparison Table 2, settings Figure 2, images and 2–4 options, design fixes (recomputed grades, QR/grid), processor, Use paragraph (Feb data still `\todo`), Conclusions (limits, future work, Moodle removed), Acknowledgements (Collado). No cuts yet.

**Rewrite (after February)**
- [ ] Apply the section plans above, the rewrite instructions in Section 2, and the removals in Section 5.
- [ ] Declarations required by Elsevier: competing interests, CRediT, ethics/consent statement for the trial data.

## 8. INSIGHT Collection

- `thesis_statement`: see § 2 (confirmed).
- `provenance`: Excel-macro predecessor by J. C. Collado Machuca; author's use since 2019; ≥3 subjects; ~1,300+ students.
- `origin_personalisation`: gamified quizzes (Kahoot, later Moodle) → ranking per block → best students get questions counted as correct; published 2018.
- `predecessor_failures`: complex configuration; occasional grading failures; personalisation as a separate version; multiple answers patched in, max. 2; students' ID errors.
- `requirement_to_design`: § 3, Section 2 table.
- `gap`: "None has the option to personalise exams according to the assessment in the subjects and the student's progress."
- `mobile_use_case`: special or second sittings; publish marks the same day.
- `personalisation_v1`: confirmed in v1.0; the teacher removes the questions of any block a student has passed.
- `trial_measures`: preparation time; exams marked by hand; sheets reviewed in Aspa by reason (ID not on the list, doubtful ID marks, doubtful answer marks); perceived simplicity.
- `scope_decisions`: Moodle out; images in; global weighting; 2–4 options; limits in Conclusions; no code snippet; old vs. new sheet comparison as text only.
- `contribution_claim`, `contribution_gap_value`, `contribution_audience`: § 2.
- `future_work`: >30 questions; >4 options; other universities; real-scan validation decided after February.
