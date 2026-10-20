# AGENTS.md

This repo contains one agent skill: **`skills/psa-label-alignment/`**.

## When to use it

Use the skill when the user asks whether a PSA-graded slab is real or fake.
Typical cases:

- a slab listed on Mercari, Rakuma, eBay or Yahoo Auctions
- the user wants a seller's slab photo compared with the PSA cert page

## What to do

1. Read [`skills/psa-label-alignment/SKILL.md`](skills/psa-label-alignment/SKILL.md)
   and follow its workflow. It covers getting the images, running the check,
   interpreting the result and reporting it.
2. Run the CLI. It needs Python 3 and the packages in `requirements.txt`.

   ```bash
   python skills/psa-label-alignment/scripts/psa_label_check.py \
       --ref <psa_cert_front_image> --test <seller_front_photo> --out <dir>
   ```

3. Read `<dir>/report.json`. Check `verdict`, which is one of:
   - `CONSISTENT`
   - `MISMATCH`
   - `INCONCLUSIVE`
4. Reply in the user's language. Always mention the limits listed in
   `SKILL.md`: the check covers the label only, it cannot detect a swapped
   card, and a valid QR code does not prove the slab is genuine.

## Self-test

```bash
python tests/test_examples.py
```

The expected results are:

- `01`: `MISMATCH`
- `02`: `CONSISTENT`
