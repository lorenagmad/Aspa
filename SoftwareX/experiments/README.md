# Experiments of the SoftwareX article

Scripts that reproduce the examples, tests and figures of the article
(`SoftwareX/softwarex-osp-template.tex`). All data are synthetic: the question bank is in
`demo_data.py` and the students are fictitious.

Install the dependencies of Aspa plus `matplotlib`, `pillow` and, for the screenshots,
`playwright` (it uses the installed Google Chrome). Run everything from the root of the repository:

```
pip install -r requirements.txt matplotlib pillow playwright

# 1. End-to-end functional tests through the web interface (67 checks)
python SoftwareX/experiments/run_functional.py work/func

# 2. Accuracy and robustness of the optical reader (500 + 125 sheets, 30 sheets per level)
python SoftwareX/experiments/run_omr.py work/omr 500 30

# 3. Screenshots: start Aspa on the projects created in step 1, then capture
python app.py --carpeta work/func/aspa_home --puerto 5099 --sin-navegador
python SoftwareX/experiments/screenshots.py work/func/aspa_home work/shots 5099

# 4. Figures (written to SoftwareX/figures)
python SoftwareX/experiments/make_figures.py work/func/aspa_home work/omr/omr_results.json work/shots
```

| Script | Purpose |
|---|---|
| `demo_data.py` | 40-question bank on software engineering and 40 fictitious students |
| `common.py` | demo projects, sheets filled with known answers, image degradations |
| `run_functional.py` | creates, configures, generates, reads, reviews, adjusts and exports exams through the Flask test client |
| `run_omr.py` | reads degraded synthetic sheets with `examtool.lector.leer_pagina` and compares with the ground truth |
| `screenshots.py` | screenshots of the running interface |
| `make_figures.py` | figures of the article |
