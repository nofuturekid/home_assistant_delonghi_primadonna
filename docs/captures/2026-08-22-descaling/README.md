# BLE capture: descaling run, ECAM 656.55.MS, 2026-08-22

Raw evidence behind several fixes in this fork. Kept on this branch only —
it is deliberately **not** merged into `maintained` or offered upstream,
because raw logs do not belong in the shipped integration.

## Contents

| File | What it is |
| --- | --- |
| `analysis.md` | The write-up: byte-by-byte decoding of the `0x75` status frame |
| `frames-descaling.log` | Full descaling program, 17:20-18:23 |
| `frames-steam.log` | Steam dispensing, 19:43, 96 s |
| `frames-attachments.log` | Milk container / water spout detection |
| `frames-*-changes.log` | Same runs, reduced to frames where a byte changed |
| `frames-annotated.tsv` | Timeline with the manual annotations made during the run |

## What it backs

The capture is what the following claims rest on. If any of them is
questioned, the timestamps in these logs are the answer.

- **PR #254** - machine states `4` (descaling), `5` (steam), `14` (filter
  change) were wrong in `MACHINE_STATUS`, not merely missing. State `12`
  (milk system cleaning) was unknown.
- **PR #258** - the dispensing condition missed most dispenses.
- `DEBUG_NOTES.md` on `maintained`, commit `c890d26` - the distilled version
  of `analysis.md`. That commit has **not** been offered upstream yet.

## Still open from `analysis.md`

1. `motor_down` (bit `0x04`) is mislabelled: it marks a resting position, not
   a permanent state. It only looked permanent because the machine was idle
   whenever it was observed. Still present in `machine_switch.py` and 13
   translation files.
2. Offering the `DEBUG_NOTES.md` protocol findings upstream as a docs PR.

## Note

`analysis.md` referred to the logs as `rahmen-*.log`; the files have always
been named `frames-*.log`. Corrected when the folder was moved here.
