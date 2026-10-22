#!/usr/bin/env python3
"""Run the bundled examples and check the verdicts. Works with plain python or pytest.
Everything runs offline: SNKRDUNK references are bundled in examples/snkrdunk_refs/."""
import glob
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "psa-label-alignment", "scripts", "psa_label_check.py")
EX = os.path.join(ROOT, "examples")
REFS = os.path.join(EX, "snkrdunk_refs")
CASES = [
    ("01-reprinted-label-suspect", "134699919", "MISMATCH", 1),
    ("02-genuine-control", "161870798", "CONSISTENT", 0),
]
# (example, SNKRDUNK reference folder, expected verdict, expected exit code)
SNKRDUNK_CASES = [
    ("01-reprinted-label-suspect", "kanazawa-pikachu-psa10", "MISMATCH", 1),
    ("02-genuine-control", "kanazawa-pikachu-psa10", "CONSISTENT", 0),
    ("03-snkrdunk-reference", "leafeon-vmax-hr", "CONSISTENT", 0),
]


def _run(args):
    out = tempfile.mkdtemp(prefix="psa_")
    p = subprocess.run([sys.executable, SCRIPT, *args, "--out", out], capture_output=True, text=True)
    with open(os.path.join(out, "report.json"), encoding="utf-8") as f:
        return p.returncode, json.load(f)


def run_case(name, cert, extra=()):
    ex = os.path.join(EX, name)
    return _run(["--ref", os.path.join(ex, "psa_front.png"),
                 "--test", os.path.join(ex, "listing_front.jpg"),
                 "--test-back", os.path.join(ex, "listing_back.jpg"), "--cert", cert, *extra])


def run_snkrdunk_case(name, refs):
    ex = os.path.join(EX, name)
    return _run(["--ref", *sorted(glob.glob(os.path.join(REFS, refs, "ref_*.jpg"))),
                 "--description-only", "--test", os.path.join(ex, "listing_front.jpg")])


def test_examples():
    for name, cert, want, code in CASES:
        rc, rep = run_case(name, cert)
        assert rep["verdict"] == want, (name, rep["verdict"], rep["max_adjacent_line_disagreement_px"])
        assert rc == code, (name, rc)


def test_snkrdunk_references():
    for name, refs, want, code in SNKRDUNK_CASES:
        rc, rep = run_snkrdunk_case(name, refs)
        assert rep["verdict"] == want, (name, rep["verdict"], rep["per_reference"])
        assert rc == code, (name, rc)


def test_cross_cert_reference():
    # genuine photo vs PSA image of a different cert of the same card -> still consistent
    _, rep = _run(["--ref", os.path.join(EX, "01-reprinted-label-suspect", "psa_front.png"),
                   "--test", os.path.join(EX, "02-genuine-control", "listing_front.jpg"),
                   "--ignore-cert-line"])
    assert rep["verdict"] == "CONSISTENT", rep


if __name__ == "__main__":
    ok = True
    for name, cert, want, code in CASES:
        rc, rep = run_case(name, cert)
        good = rep["verdict"] == want and rc == code
        ok &= good
        print(f"{'PASS' if good else 'FAIL'}  {name} vs PSA image: {rep['verdict']} "
              f"({rep['max_adjacent_line_disagreement_px']} px), expected {want}")
    for name, refs, want, code in SNKRDUNK_CASES:
        rc, rep = run_snkrdunk_case(name, refs)
        good = rep["verdict"] == want and rc == code
        ok &= good
        n = sum(r["verdict"] == "CONSISTENT" for r in rep["per_reference"])
        print(f"{'PASS' if good else 'FAIL'}  {name} vs SNKRDUNK {refs}: {rep['verdict']} "
              f"({rep['max_adjacent_line_disagreement_px']} px, {n}/{len(rep['per_reference'])} match), "
              f"expected {want}")
    test_cross_cert_reference()
    print("PASS  cross-cert reference (--ignore-cert-line)")
    print("all tests passed" if ok else "SOME TESTS FAILED")
    sys.exit(0 if ok else 1)
