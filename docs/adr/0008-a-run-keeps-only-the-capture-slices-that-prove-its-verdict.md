# A run keeps only the capture slices that prove its verdict

When a run is judged, the judge cuts out of the packet captures only the slices that prove its verdict and keeps them in the run's folder.
The full captures are then deleted, and the finished run's folder is compressed.
Captures and compressed runs are never committed to git or published; readers who want packets rerun the test.

## Why

On 2026-11-24 one MLAG campaign's evidence was about 315 MB, and full captures later piled up to 21 GB on the lab machine.
On 2026-11-25 the operator rejected keeping full captures for later analysis: "get rid of them only keep what is needed for proof after a run".
Cutting the evidence down is part of every run, not a cleanup step afterwards.
Removing large files from git history takes coordinated work, so they must never enter it.

## Considered options

Git, Git LFS, release assets, object storage, a static site and a hosted database were weighed for publishing evidence and rejected: anyone can rerun the committed labs.

## What is not built

Networka keeps every per-point capture in `captures/`, and `nw test replay` judges from those full captures.
It does not cut slices, delete full captures or compress a run.
Replay must then judge from the kept slices and still give a byte-identical result ([ADR 0006](0006-replay-judges-saved-evidence-again-and-must-give-a-byte-identical-result.md)); how it does so is not designed yet.
