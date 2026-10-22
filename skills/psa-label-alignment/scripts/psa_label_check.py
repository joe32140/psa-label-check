#!/usr/bin/env python3
"""
psa_label_check.py - compare the text layout of a PSA slab label in a seller's
photo against PSA's official cert image of the same certificate.

Idea: a genuine re-photograph of the SAME printed label can only differ from
PSA's image by a smooth, whole-label distortion (camera angle, lens). Every
text line moves together. A counterfeit slab with a re-typeset / re-printed
label shows line-specific shifts: neighbouring lines drift in different
directions at the same horizontal position, because the kerning differs.

Usage:
  python psa_label_check.py --ref psa_front.png --test listing_front.jpg --out out/
  python psa_label_check.py --ref psa_front.png --test listing_front.jpg \
      --test-back listing_back.jpg --cert 134699919 --out out/

Manual corner override (TL;TR;BR;BL of the red label frame, in pixels):
  --ref-corners "29,22;349,24;349,121;29,119"

Outputs in --out: report.json, overlay.png, displacement.png,
                  label_ref.png, label_test.png
Exit code: 0 = CONSISTENT, 1 = MISMATCH, 2 = INCONCLUSIVE, 3 = error.
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

CANON_W, CANON_H = 960, 291          # rectified label size (aspect ~3.3)
LABEL_ASPECT = CANON_W / CANON_H

# Provisional thresholds (calibrated on the two bundled examples; see
# references/method.md). Max disagreement, in canonical pixels, between the
# horizontal shift of two adjacent text lines at the same x position.
CONSISTENT_MAX = 4.0
MISMATCH_MIN = 8.0
MIN_GLYPHS = 40
MIN_MEDIAN_CORR = 0.70


# ----------------------------------------------------------------- geometry
def parse_corners(s):
    pts = [tuple(float(v) for v in p.split(",")) for p in s.split(";")]
    if len(pts) != 4:
        raise ValueError("corners must be 4 points: 'x,y;x,y;x,y;x,y' (TL;TR;BR;BL)")
    return np.float32(pts)


def order_quad(pts):
    pts = np.float32(pts).reshape(-1, 2)
    s = pts.sum(1)
    d = np.diff(pts, axis=1).ravel()
    return np.float32([pts[np.argmin(s)], pts[np.argmin(d)],
                       pts[np.argmax(s)], pts[np.argmax(d)]])


def _looks_like_label(img, q):
    """A PSA label frame encloses a bright, nearly white card. Reject red-ish
    backgrounds (wood tables, playmats) that only happen to be the right shape."""
    M = cv2.getPerspectiveTransform(
        np.float32(q), np.float32([[0, 0], [CANON_W, 0], [CANON_W, CANON_H], [0, CANON_H]]))
    lab = cv2.warpPerspective(img, M, (CANON_W, CANON_H))
    hsv = cv2.cvtColor(lab[45:250, 45:915], cv2.COLOR_BGR2HSV)
    whitish = (hsv[..., 1] < 80) & (hsv[..., 2] > 120)
    return float(whitish.mean()) > 0.35


def detect_label_frame(img):
    """Find the red outer frame of a standard PSA label. Returns 4 corners."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h_img, w_img = img.shape[:2]
    best = None
    for s_min, v_min in [(120, 120), (90, 110), (70, 90), (60, 70)]:
        m = (((hsv[..., 0] < 10) | (hsv[..., 0] > 168)) &
             (hsv[..., 1] > s_min) & (hsv[..., 2] > v_min)).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:6]:
            if cv2.contourArea(c) < 0.005 * h_img * w_img:
                continue
            hull = cv2.convexHull(c)
            peri = cv2.arcLength(hull, True)
            quad = None
            for eps in (0.01, 0.02, 0.03, 0.04, 0.05):
                a = cv2.approxPolyDP(hull, eps * peri, True)
                if len(a) == 4:
                    quad = a.reshape(-1, 2)
                    break
            if quad is None:
                quad = cv2.boxPoints(cv2.minAreaRect(c))
            q = order_quad(quad)
            wd = (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2
            ht = (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2
            if ht <= 0:
                continue
            # Oblique photos foreshorten the label, so accept a wide aspect range
            # and prefer the largest plausible red quadrilateral.
            aspect = wd / ht
            area = cv2.contourArea(q)
            fill = cv2.contourArea(c) / max(area, 1)
            if (2.2 <= aspect <= 8.0 and fill > 0.15 and (best is None or area > best[0])
                    and _looks_like_label(img, q)):
                best = (area, q)
        if best is not None:
            break
    if best is None:
        raise RuntimeError("could not find the red PSA label frame; pass corners manually")
    return best[1]


def rectify(img, corners):
    M = cv2.getPerspectiveTransform(
        np.float32(corners),
        np.float32([[0, 0], [CANON_W, 0], [CANON_W, CANON_H], [0, CANON_H]]))
    return cv2.warpPerspective(img, M, (CANON_W, CANON_H), flags=cv2.INTER_CUBIC)


# ------------------------------------------------------------ measurement
def _norm(gray):
    g = gray.astype(np.float32)
    bg = cv2.GaussianBlur(g, (0, 0), 15)
    return cv2.normalize(g - bg, None, 0, 1, cv2.NORM_MINMAX)


def glyph_displacements(ref_lab, test_lab, search=30):
    """Template-match every text glyph of the reference label in the test label."""
    A = cv2.cvtColor(ref_lab, cv2.COLOR_BGR2GRAY)
    B = cv2.cvtColor(test_lab, cv2.COLOR_BGR2GRAY)
    An, Bn = _norm(A), _norm(B)
    th = cv2.adaptiveThreshold(A, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY_INV, 31, 20)
    # ignore red frame, PSA hologram logo (bottom centre) and barcode (bottom left)
    th[:40] = 0
    th[262:] = 0
    th[:, :38] = 0
    th[:, 925:] = 0
    th[200:262, 380:560] = 0
    n, _, st, _ = cv2.connectedComponentsWithStats(th, 8)
    pts = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if area < 20 or h < 8 or w > 60:
            continue
        if 205 < y < 262 and x < 300:          # barcode bars
            continue
        pad = 6
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(CANON_W, x + w + pad), min(CANON_H, y + h + pad)
        T = An[y0:y1, x0:x1]
        sx0, sy0 = max(0, x0 - search), max(0, y0 - search)
        sx1, sy1 = min(CANON_W, x1 + search), min(CANON_H, y1 + search)
        R = cv2.matchTemplate(Bn[sy0:sy1, sx0:sx1], T, cv2.TM_CCOEFF_NORMED)
        _, corr, _, loc = cv2.minMaxLoc(R)
        # sub-pixel peak (parabolic fit on the correlation surface)
        fx, fy = float(loc[0]), float(loc[1])
        cx_, cy_ = loc
        if 0 < cx_ < R.shape[1] - 1:
            l_, c_, r_ = R[cy_, cx_ - 1], R[cy_, cx_], R[cy_, cx_ + 1]
            den = l_ - 2 * c_ + r_
            if den != 0:
                fx += float(np.clip(0.5 * (l_ - r_) / den, -0.5, 0.5))
        if 0 < cy_ < R.shape[0] - 1:
            u_, c_, d_ = R[cy_ - 1, cx_], R[cy_, cx_], R[cy_ + 1, cx_]
            den = u_ - 2 * c_ + d_
            if den != 0:
                fy += float(np.clip(0.5 * (u_ - d_) / den, -0.5, 0.5))
        pts.append({"x": float(x + w / 2), "y": float(y + h / 2),
                    "dx": round(fx + sx0 - x0, 2), "dy": round(fy + sy0 - y0, 2),
                    "corr": float(corr)})
    return pts


def group_lines(pts, gap=18, min_glyphs=3):
    if not pts:
        return []
    pts = sorted(pts, key=lambda p: p["y"])
    lines, cur = [], [pts[0]]
    for p in pts[1:]:
        if p["y"] - cur[-1]["y"] > gap:
            lines.append(cur)
            cur = [p]
        else:
            cur.append(p)
    lines.append(cur)
    return [sorted(l, key=lambda p: p["x"]) for l in lines if len(l) >= min_glyphs]


def _median3(v):
    v = np.asarray(v, float)
    if len(v) < 3:
        return v
    out = v.copy()
    for i in range(1, len(v) - 1):
        out[i] = np.median(v[i - 1:i + 2])
    # line ends too: a lone glyph matched to an identical neighbour letter
    # ("EEVEE") must not decide the verdict; a re-typeset shifts whole runs
    out[0], out[-1] = np.median(v[:3]), np.median(v[-3:])
    return out


def _left_block(line, gap=70, min_x=300):
    """Glyphs of the left description block: cut the line at the first wide
    gap right of min_x. The right column (card number, grade, cert) starts there."""
    for i in range(1, len(line)):
        if line[i - 1]["x"] > min_x and line[i]["x"] - line[i - 1]["x"] > gap:
            return line[:i]
    return line


def analyse(pts, ignore_cert_line=False, description_only=False):
    good = [p for p in pts if p["corr"] >= 0.5]
    lines = group_lines(good)
    if ignore_cert_line or description_only:
        # bottom row holds the cert number, which differs between certs
        lines = [l for l in lines if np.mean([p["y"] for p in l]) < 205]
    if description_only:
        # right column holds the grade ("GEM MT 10" / "MINT 9"), which differs between grades
        lines = [l for l in (_left_block(l) for l in lines) if len(l) >= 3]
    if ignore_cert_line or description_only:
        good = [p for l in lines for p in l]
    line_stats = []
    for i, l in enumerate(lines):
        dx = np.array([p["dx"] for p in l])
        line_stats.append({"line": i + 1, "y": round(float(np.mean([p["y"] for p in l])), 1),
                           "glyphs": len(l), "dx_min": float(dx.min()), "dx_max": float(dx.max()),
                           "dx_mean": round(float(dx.mean()), 2)})
    pairs = []
    for a, b in zip(lines, lines[1:]):
        xa = np.array([p["x"] for p in a]); da = _median3([p["dx"] for p in a])
        xb = np.array([p["x"] for p in b]); db = _median3([p["dx"] for p in b])
        lo, hi = max(xa.min(), xb.min()), min(xa.max(), xb.max())
        if hi - lo < 100:
            continue
        xs = np.linspace(lo, hi, 60)
        diff = np.abs(np.interp(xs, xa, da) - np.interp(xs, xb, db))
        pairs.append({"lines": [lines.index(a) + 1, lines.index(b) + 1],
                      "max_abs_diff_px": round(float(diff.max()), 2),
                      "p90_abs_diff_px": round(float(np.percentile(diff, 90)), 2)})
    return good, lines, line_stats, pairs


def verdict(pts, good, pairs):
    corr_med = float(np.median([p["corr"] for p in pts])) if pts else 0.0
    min_glyphs = MIN_GLYPHS if len(pairs) >= 3 else 30
    if len(good) < min_glyphs or corr_med < MIN_MEDIAN_CORR or not pairs:
        return "INCONCLUSIVE", corr_med, None, (
            f"Only {len(good)} glyphs matched (median correlation {corr_med:.2f}). "
            "Use a sharper, more frontal photo of the label, or set the frame corners manually.")
    worst = max(p["max_abs_diff_px"] for p in pairs)
    if worst <= CONSISTENT_MAX:
        return "CONSISTENT", corr_med, worst, (
            "All text lines shift together; the label text layout matches PSA's image of this cert.")
    if worst >= MISMATCH_MIN:
        return "MISMATCH", corr_med, worst, (
            "Adjacent text lines shift in different directions at the same position. "
            "The label text was typeset differently from PSA's original - consistent with a reprinted/counterfeit label.")
    return "INCONCLUSIVE", corr_med, worst, (
        "Line-to-line disagreement is between the consistent and mismatch thresholds. "
        "Get a sharper, more frontal photo and re-run.")


# --------------------------------------------------------------------- QR
def decode_qr(img):
    det = cv2.QRCodeDetector()
    h = img.shape[0]
    for crop in (img[: int(h * 0.35)], img):
        for s in (1, 2, 3, 4, 6):
            c = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC) if s > 1 else crop
            if max(c.shape[:2]) > 7000:
                continue
            try:
                val, _, _ = det.detectAndDecode(c)
            except cv2.error:
                val = ""
            if val:
                return val
    return None


# ----------------------------------------------------------------- figures
def save_figures(out, ref_lab, test_lab, lines, title):
    ga = cv2.equalizeHist(cv2.cvtColor(ref_lab, cv2.COLOR_BGR2GRAY))
    gb = cv2.equalizeHist(cv2.cvtColor(test_lab, cv2.COLOR_BGR2GRAY))
    cv2.imwrite(os.path.join(out, "overlay.png"), np.dstack([ga, gb, ga]))  # magenta=ref, green=test
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(9, 4), dpi=110)
    for i, l in enumerate(lines):
        ax.plot([p["x"] for p in l], [p["dx"] for p in l], "o-", ms=3, label=f"line {i + 1}")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("glyph x position on rectified label (label width = 960 px)")
    ax.set_ylabel("horizontal shift, test vs PSA (px)")
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "displacement.png"))
    plt.close(fig)


# -------------------------------------------------------------------- main
def compare(ref, rc, test, tc, out, ignore_cert_line=False, description_only=False):
    """Compare one reference label with the test label; write figures to out/."""
    os.makedirs(out, exist_ok=True)
    ref_lab, test_lab = rectify(ref, rc), rectify(test, tc)
    cv2.imwrite(os.path.join(out, "label_ref.png"), ref_lab)
    cv2.imwrite(os.path.join(out, "label_test.png"), test_lab)

    # Pass 1 on the frame-rectified labels, then refine: fit ONE global
    # homography from all glyph matches (absorbs frame-corner and perspective
    # error) and re-measure. A single homography cannot create opposite shifts
    # in neighbouring lines, so a re-typeset label still shows up afterwards.
    pts = glyph_displacements(ref_lab, test_lab)
    g1 = [p for p in pts if p["corr"] >= 0.6]
    if len(g1) >= 12:
        src = np.float32([[p["x"] + p["dx"], p["y"] + p["dy"]] for p in g1])
        dst = np.float32([[p["x"], p["y"]] for p in g1])
        Hr, _ = cv2.findHomography(src, dst, cv2.RANSAC, 6.0)
        if Hr is not None:
            test_lab = cv2.warpPerspective(test_lab, Hr, (CANON_W, CANON_H), flags=cv2.INTER_CUBIC)
            cv2.imwrite(os.path.join(out, "label_test.png"), test_lab)
            pts = glyph_displacements(ref_lab, test_lab)
    good, lines, line_stats, pairs = analyse(pts, ignore_cert_line, description_only)
    v, corr_med, worst, msg = verdict(pts, good, pairs)
    save_figures(out, ref_lab, test_lab, lines,
                 f"{v}: max adjacent-line disagreement = {worst if worst is not None else 'n/a'} px")
    return {
        "verdict": v,
        "message": msg,
        "max_adjacent_line_disagreement_px": worst,
        "glyphs_matched": len(good),
        "median_match_correlation": round(corr_med, 3),
        "lines": line_stats,
        "adjacent_line_pairs": pairs,
        "frame_corners": {"ref": np.round(rc, 1).tolist(), "test": np.round(tc, 1).tolist()},
    }


def combine(results):
    """Vote across several genuine references.

    PSA has re-typeset the same card's label between printing eras, so a
    genuine slab can legitimately mismatch a reference from another era. The
    test label therefore counts as CONSISTENT when it matches any usable
    reference, and as MISMATCH only when it matches none of them.
    """
    usable = [r for r in results if r["verdict"] in ("CONSISTENT", "MISMATCH")]
    cons = [r for r in usable if r["verdict"] == "CONSISTENT"]
    mism = [r for r in usable if r["verdict"] == "MISMATCH"]
    if cons:
        best = min(cons, key=lambda r: r["max_adjacent_line_disagreement_px"])
        msg = (f"Text layout matches {len(cons)} of {len(results)} genuine reference label(s). "
               + (f"{len(mism)} reference(s) differ, which is normal when PSA re-typeset this "
                  "card's label between printing eras." if mism else ""))
        return "CONSISTENT", best, msg.strip()
    if len(mism) >= 2 or (mism and len(results) == 1):
        best = min(mism, key=lambda r: r["max_adjacent_line_disagreement_px"])
        return "MISMATCH", best, (
            f"Text layout matches none of the {len(mism)} usable genuine reference label(s): "
            "consistent with a reprinted/counterfeit label. Check that the references come from a "
            "similar cert-number range, since PSA re-typesets labels between eras.")
    return "INCONCLUSIVE", (mism or results)[0], (
        "Too few usable references. Add more reference photos (ideally from a similar cert-number "
        "range), or use a sharper, more frontal photo.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", required=True, nargs="+",
                    help="reference image(s) of a genuine label: PSA's cert image, or photos of "
                         "genuine slabs of the same card (e.g. from snkrdunk_refs.py)")
    ap.add_argument("--test", required=True, help="seller/listing photo of the slab (front)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--ref-corners", help="manual label-frame corners for --ref 'x,y;x,y;x,y;x,y' "
                                          "(single --ref only)")
    ap.add_argument("--test-corners", help="manual label-frame corners for --test")
    ap.add_argument("--test-back", help="optional seller photo of the slab back (QR check)")
    ap.add_argument("--cert", help="expected cert number (checked against the QR code)")
    ap.add_argument("--ignore-cert-line", action="store_true",
                    help="reference is a DIFFERENT cert of the same card (identical label text): "
                         "compare only the description lines, skip the cert-number row")
    ap.add_argument("--description-only", action="store_true",
                    help="compare only the left description block; skip the right column (card "
                         "number, grade, cert). Use for references of a different cert or grade")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    if a.ref_corners and len(a.ref) > 1:
        print("error: --ref-corners needs a single --ref", file=sys.stderr)
        return 3

    test = cv2.imread(a.test)
    if test is None:
        print("error: cannot read --test image", file=sys.stderr)
        return 3
    try:
        tc = parse_corners(a.test_corners) if a.test_corners else detect_label_frame(test)
    except Exception as e:  # noqa: BLE001
        print(f"error: test image: {e}", file=sys.stderr)
        return 3

    results = []
    for i, path in enumerate(a.ref):
        out = a.out if len(a.ref) == 1 else os.path.join(a.out, f"ref_{i + 1}")
        ref = cv2.imread(path)
        try:
            if ref is None:
                raise ValueError("cannot read image")
            rc = parse_corners(a.ref_corners) if a.ref_corners else detect_label_frame(ref)
            r = compare(ref, rc, test, tc, out, a.ignore_cert_line, a.description_only)
        except Exception as e:  # noqa: BLE001
            if len(a.ref) == 1:
                print(f"error: {e}", file=sys.stderr)
                return 3
            r = {"verdict": "ERROR", "message": str(e), "max_adjacent_line_disagreement_px": None}
        r["ref"] = path
        r["out"] = out
        results.append(r)

    if len(results) == 1:
        report = dict(results[0])
        v, msg = report["verdict"], report["message"]
    else:
        v, best, msg = combine(results)
        report = {k: best.get(k) for k in ("max_adjacent_line_disagreement_px", "glyphs_matched",
                                           "median_match_correlation", "ref", "out")}
        report = {"verdict": v, "message": msg, **report,
                  "per_reference": [{k: r.get(k) for k in ("ref", "out", "verdict",
                                                           "max_adjacent_line_disagreement_px",
                                                           "glyphs_matched", "median_match_correlation")}
                                    for r in results]}
    report["thresholds"] = {"consistent_max_px": CONSISTENT_MAX, "mismatch_min_px": MISMATCH_MIN,
                            "note": "provisional, calibrated on a handful of examples"}
    report["ignore_cert_line"] = a.ignore_cert_line
    report["description_only"] = a.description_only
    report["label_test_label_px_width"] = round(float(np.linalg.norm(tc[1] - tc[0])), 1)
    if a.test_back:
        back = cv2.imread(a.test_back)
        qr = decode_qr(back) if back is not None else None
        report["qr"] = {"decoded": qr}
        if a.cert:
            report["qr"]["matches_cert"] = bool(qr and a.cert in qr)
        report["qr"]["note"] = "A valid QR only proves the cert exists; counterfeit slabs copy real QR codes."

    with open(os.path.join(a.out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: report.get(k) for k in ("verdict", "max_adjacent_line_disagreement_px",
                                                  "glyphs_matched", "median_match_correlation")}))
    print(msg)
    return {"CONSISTENT": 0, "MISMATCH": 1}.get(v, 2)


if __name__ == "__main__":
    sys.exit(main())
