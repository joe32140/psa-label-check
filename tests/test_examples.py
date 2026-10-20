#!/usr/bin/env python3
"""Run the bundled examples and check the verdicts. Works with plain python or pytest."""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "psa-label-alignment", "scripts", "psa_label_check.py")
CASES = [
    ("01-reprinted-label-suspect", "134699919", "MISMATCH", 1),
    ("02-genuine-control", "161870798", "CONSISTENT", 0),
]


def run_case(name, cert, extra=()):
    ex = os.path.join(ROOT, "examples", name)
    out = tempfile.mkdtemp(prefix=f"psa_{name}_")
    cmd = [sys.executable, SCRIPT, "--ref", os.path.join(ex, "psa_front.png"),
           "--test", os.path.join(ex, "listing_front.jpg"),
           "--test-back", os.path.join(ex, "listing_back.jpg"), "--cert", cert,
           "--out", out, *extra]
    p = subprocess.run(cmd, capture_output=True, text=True)
    with open(os.path.join(out, "report.json"), encoding="utf-8") as f:
        return p.returncode, json.load(f)


def test_examples():
    for name, cert, want, code in CASES:
        rc, rep = run_case(name, cert)
        assert rep["verdict"] == want, (name, rep["verdict"], rep["max_adjacent_line_disagreement_px"])
        assert rc == code, (name, rc)


def test_cross_cert_reference():
    # genuine photo vs PSA image of a different cert of the same card -> still consistent
    ex1 = os.path.join(ROOT, "examples", "01-reprinted-label-suspect")
    ex2 = os.path.join(ROOT, "examples", "02-genuine-control")
    out = tempfile.mkdtemp()
    subprocess.run([sys.executable, SCRIPT, "--ref", os.path.join(ex1, "psa_front.png"),
                    "--test", os.path.join(ex2, "listing_front.jpg"),
                    "--ignore-cert-line", "--out", out], capture_output=True)
    rep = json.load(open(os.path.join(out, "report.json"), encoding="utf-8"))
    assert rep["verdict"] == "CONSISTENT", rep


if __name__ == "__main__":
    for name, cert, want, code in CASES:
        rc, rep = run_case(name, cert)
        ok = rep["verdict"] == want and rc == code
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {rep['verdict']} "
              f"({rep['max_adjacent_line_disagreement_px']} px), expected {want}")
    test_cross_cert_reference()
    print("PASS  cross-cert reference (--ignore-cert-line)")
    test_examples()
    print("all tests passed")
