# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Figures of the SoftwareX article.

    python SoftwareX/experiments/make_figures.py <aspa_home> <omr_results.json> <screenshots_dir>
"""
import json
import random
import sys
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pymupdf as fitz  # noqa: E402
from PIL import Image  # noqa: E402

import common as C  # noqa: E402
import demo_data  # noqa: E402
from examtool import layout as L  # noqa: E402
from examtool import lector  # noqa: E402

OUT = C.RAIZ / "SoftwareX" / "figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, GREEN, RED, AMBER, GREY = "#1f3a93", "#2e7d32", "#c62828", "#e6a700", "#777777"


def render(pdf, page=0, dpi=200, clip_mm=None):
    with fitz.open(pdf) as d:
        pg = d[page]
        clip = None
        if clip_mm:
            k = 72 / 25.4
            clip = fitz.Rect(*(v * k for v in clip_mm))
        pix = pg.get_pixmap(dpi=dpi, clip=clip)
        return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[..., :3].copy()


def fig_sheets(home):
    vers = next(home.glob("software-engineering-final-exam*"))
    pers = next(home.glob("personalised-exam*"))
    a = render(vers / "examenes.pdf", 0, 220, clip_mm=(0, 0, 210, 141))
    with fitz.open(pers / "examenes.pdf") as d:
        page_b = next(i for i, pg in enumerate(d) if "passed" in pg.get_text() and "questions in class" in pg.get_text())
    b = render(pers / "examenes.pdf", page_b, 220, clip_mm=(0, 0, 210, 141))
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.75), gridspec_kw={"width_ratios": [1, 1]})
    ax[0].imshow(a)
    ax[1].imshow(b)
    for x in ax:
        x.set_xticks([]), x.set_yticks([])
        for s in x.spines.values():
            s.set_visible(True), s.set_color("#bbbbbb")
    ax[0].set_title("(a) Answer sheet of a copy of version A", fontsize=8)
    ax[1].set_title("(b) Personalised exam: name printed, no ID grid", fontsize=8)
    K = 220 / 25.4
    notes = [((L.LEFT - 4.5) * K, (L.TOP + 4.5) * K, "1", "ArUco marker"),
             ((L.QR_X - 4.5) * K, (L.QR_Y + 9) * K, "2", "QR: exam, version, copy"),
             ((L.ID_X0 + 26) * K, (L.row_y(5)) * K, "3", "10-digit ID grid"),
             ((L.ans_box(2, 1).cx) * K, (L.row_y(2)) * K, "4", "answers A-D"),
             ((L.ans_box(6, 4).cx) * K, (L.row_y(6)) * K, "5", "«Cancel» box"),
             ((105) * K, (L.ACLA_Y + 12) * K, "6", "clarifications")]
    for x, y, n, _ in notes:
        ax[0].annotate(n, (x, y), color="white", fontsize=7, ha="center", va="center", weight="bold",
                       bbox=dict(boxstyle="circle,pad=0.25", fc=RED, ec="none"))
    ax[0].text(0.0, -0.035, "  ".join(f"{n} {t}" for _, _, n, t in notes), transform=ax[0].transAxes, fontsize=6.2,
               va="top")
    fig.subplots_adjust(left=0.01, right=0.99, wspace=0.04, top=0.92, bottom=0.08)
    fig.savefig(OUT / "fig_sheets.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / "fig_sheets.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_pipeline(home):
    """Phone-like photo -> markers and homography -> local box alignment -> ink ratios."""
    proy = C.Proyecto(next(home.glob("software-engineering-final-exam*")))
    rng = random.Random(8)
    img, truth = C.fill_sheet(proy, 2, demo_data.students()[5], rng, ink=60)
    img = C.warp(img, 1.6, rng)
    img = C.shadow(img, 0.55)
    photo = C.phone_photo(img, 0.18, rng, out_w=2600)
    photo = C.noise(C.blur(photo, 1.0), 5, rng)
    photo = C.jpeg(photo, 70)

    det = lector._detector()
    corners, ids, _ = det.detectMarkers(photo)
    H, n = lector._homografia(photo)
    S = lector.S
    ender = cv2.warpPerspective(photo, H, (lector._px(L.PAGE_W), lector._px(L.PAGE_H)), flags=cv2.INTER_AREA,
                                borderValue=255)
    tinta, norm = lector._mascara_tinta(ender)
    detect = lector._centros_casillas(tinta)
    res = lector.leer_pagina(photo)

    fig = plt.figure(figsize=(7.2, 3.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.15, 1.0], wspace=0.42)
    a0 = fig.add_subplot(gs[0])
    a0.imshow(photo, cmap="gray")
    for c, i in zip(corners, ids.flatten()):
        pts = c.reshape(4, 2)
        a0.add_patch(plt.Polygon(pts, fill=False, ec=RED, lw=1.2))
        a0.text(*pts.mean(0) + [0, -90], f"id {i}", color=RED, fontsize=6, ha="center")
    a0.set_title("(a) photo: 4 ArUco markers found", fontsize=8)
    a0.axis("off")

    # (b) zoom on the first answer column of the rectified, illumination-normalised page
    a1 = fig.add_subplot(gs[1])
    x0, x1, y0, y1 = 74, 125, L.ROWS_Y0 - 5, L.row_y(9) + 7
    a1.imshow(norm[int(y0 * S):int(y1 * S), int(x0 * S):int(x1 * S)], cmap="gray",
              extent=(x0, x1, y1, y0))
    exp = np.array([(L.ans_box(q, k).cx, L.ans_box(q, k).cy) for q in range(10) for k in range(5)])
    fin = np.array(res["centros"]["resp"][:10]).reshape(-1, 2)
    a1.scatter(exp[:, 0], exp[:, 1], s=9, marker="+", c=RED, lw=0.8, label="template position")
    a1.scatter(fin[:, 0], fin[:, 1], s=14, facecolors="none", edgecolors=GREEN, lw=0.8, label="fitted box centre")
    a1.legend(loc="lower center", bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=6, frameon=False)
    a1.set_title("(b) rectified page, local box fitting", fontsize=8)
    a1.set_xticks([]), a1.set_yticks([])
    shift = np.linalg.norm(fin - exp, axis=1)

    # (c) ink ratio of every answer box: empty vs marked, with the adaptive thresholds
    a2 = fig.add_subplot(gs[2])
    ratios = np.array(res["ratios"]["resp"][:len(truth["respuestas"])])
    marked = np.array([[("ABCD"[k] in t["m"]) if k < 4 else t["anular"] for k in range(5)]
                       for t in truth["respuestas"]])
    bins = np.linspace(0, 0.8, 41)
    a2.hist(ratios[~marked], bins=bins, color=GREY, alpha=0.8, label=f"empty ({(~marked).sum()})")
    a2.hist(ratios[marked], bins=bins, color=BLUE, alpha=0.9, label=f"marked ({marked.sum()})")
    u = res["umbrales"]
    a2.axvline(u["marca"], color=RED, lw=1, ls="-")
    a2.axvline(u["duda"], color=AMBER, lw=1, ls="--")
    a2.text(u["marca"] + 0.01, a2.get_ylim()[1] * 0.92, f"mark {u['marca']:.2f}", color=RED, fontsize=6)
    a2.text(u["duda"] + 0.01, a2.get_ylim()[1] * 0.80, f"doubt {u['duda']:.2f}", color="#a07400", fontsize=6)
    a2.set_yscale("log")
    a2.set_xlabel("fraction of ink pixels inside the box")
    a2.set_ylabel("boxes")
    a2.legend(fontsize=6, frameon=False, loc="upper right", bbox_to_anchor=(1, 0.75))
    a2.set_title("(c) ink ratio and adaptive thresholds", fontsize=8)
    fig.savefig(OUT / "fig_pipeline.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / "fig_pipeline.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    ok = sum(r["m"] == t["m"] and r["anular"] == t["anular"] for r, t in zip(res["respuestas"], truth["respuestas"]))
    info = {"markers": int(n), "boxes_found": res["casillas_encontradas"], "max_shift_mm": float(shift.max()),
            "median_shift_mm": float(np.median(shift)), "answers_ok": f"{ok}/{len(truth['respuestas'])}",
            "qr": res["qr"], "id": res["id_leido"] == truth["digitos"], "photo_px": list(photo.shape)}
    print("pipeline:", info)
    return info


LABELS = {
    "rotation_deg": ("Rotation (degrees)", None),
    "perspective": ("Corner displacement (% of width)", 100),
    "phone_tilt": ("Phone tilt (keystone, % of width)", 100),
    "warp_mm": ("Non-linear warp amplitude (mm)", None),
    "blur_sigma_px": ("Gaussian blur σ (px at 220 dpi)", None),
    "noise_sigma": ("Gaussian noise σ (grey levels)", None),
    "jpeg_quality": ("JPEG quality", None),
    "dpi": ("Resolution (dpi)", None),
    "shadow_min_gain": ("Shadow: darkest gain", None),
    "ink_grey_level": ("Ink grey level (0 black, 255 white)", None),
}


def fig_robustness(results):
    sw = results["sweeps"]
    keys = ["phone_tilt", "warp_mm", "blur_sigma_px", "dpi", "jpeg_quality", "noise_sigma", "shadow_min_gain",
            "ink_grey_level"]
    fig, axs = plt.subplots(2, 4, figsize=(7.2, 3.6), sharey=True)
    for ax, k in zip(axs.flat, keys):
        lv = list(sw[k].keys())
        x = np.array([float(v) for v in lv]) * (LABELS[k][1] or 1)
        acc = np.array([sw[k][v]["answer_accuracy"] for v in lv]) * 100
        qr = np.array([sw[k][v]["qr_rate"] for v in lv]) * 100
        silent = np.array([(sw[k][v]["answer_errors"] - sw[k][v]["answer_errors_flagged"]) /
                           max(sw[k][v]["answers"], 1) for v in lv]) * 100
        ax.plot(x, acc, "-o", color=BLUE, ms=2.5, lw=1, label="answers read correctly")
        ax.plot(x, 100 - silent, ":", color=GREEN, lw=1.2, label="answers correct or flagged")
        ax.plot(x, qr, "--s", color=AMBER, ms=2, lw=0.9, label="QR decoded")
        ax.set_xlabel(LABELS[k][0], fontsize=6.5)
        ax.set_ylim(-3, 103)
        ax.grid(alpha=0.25, lw=0.5)
        ax.tick_params(labelsize=6)
        if k in ("jpeg_quality", "dpi", "shadow_min_gain"):
            ax.invert_xaxis()
    axs[0, 0].set_ylabel("%")
    axs[1, 0].set_ylabel("%")
    h, lbl = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, lbl, loc="upper center", ncol=3, fontsize=7, frameon=False, bbox_to_anchor=(0.5, 1.03))
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / "fig_robustness.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_robustness.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def crop(src, dst, box, scale=1.0):
    im = Image.open(src)
    im = im.crop(box)
    if scale != 1:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    im.convert("RGB").save(dst, quality=92)
    return im.size


if __name__ == "__main__":
    home, res_json, shots = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    fig_sheets(home)
    info = fig_pipeline(home)
    (OUT / "pipeline_info.json").write_text(json.dumps(info, indent=1, default=str))
    if res_json.exists():
        fig_robustness(json.loads(res_json.read_text()))
    if shots.exists():
        # review screen without the footer (it shows a local path)
        crop(shots / "ui_review.png", OUT / "fig_review.jpg", (372, 140, 2880, 2380), 0.8)
        crop(shots / "ui_statistics.png", OUT / "fig_statistics.jpg", (440, 100, 2880, 1480), 0.8)
        crop(shots / "ui_prepare.png", OUT / "fig_versions.jpg", (440, 4300, 2880, 5100), 0.8)
