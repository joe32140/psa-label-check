# AGENTS.md

This repo contains one agent skill: **`skills/psa-label-alignment/`**.

## When to use it

Use the skill when the user asks whether a PSA-graded slab is real or fake.
Typical cases:

- a slab listed on Mercari, Rakuma, eBay or Yahoo Auctions
- the user wants a seller's slab photo compared with genuine slabs or the PSA cert page

## What to do

1. Read [`skills/psa-label-alignment/SKILL.md`](skills/psa-label-alignment/SKILL.md)
   and follow its workflow. It covers getting the images, running the check,
   interpreting the result and reporting it.
2. Fetch references from SNKRDUNK, then run the check. It needs Python 3 and
   the packages in `requirements.txt`.

   ```bash
   python skills/psa-label-alignment/scripts/snkrdunk_refs.py --search "<card number>"
   python skills/psa-label-alignment/scripts/snkrdunk_refs.py --apparel-id <id> --out refs/
   python skills/psa-label-alignment/scripts/psa_label_check.py \
       --ref refs/ref_*.jpg --description-only --test <seller_front_photo> --out <dir>
   ```

   If you have PSA's cert image for the exact cert, you can pass it as the
   single `--ref` without `--description-only` instead.

3. Read `<dir>/report.json`. Check `verdict`, which is one of:
   - `CONSISTENT`
   - `MISMATCH`
   - `INCONCLUSIVE`
4. Reply in the user's language. Always mention the limits listed in
   `SKILL.md`: the check covers the label only, it cannot detect a swapped
   card, `--description-only` does not compare the cert number, and a valid QR
   code does not prove the slab is genuine.

## Self-test

```bash
python tests/test_examples.py
```

The expected results are:

- `01`: `MISMATCH`, against both PSA's image and the bundled SNKRDUNK references
- `02`: `CONSISTENT`, against both
- `03`: `CONSISTENT`, against the bundled SNKRDUNK references
