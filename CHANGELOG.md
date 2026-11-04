# Changelog

## 0.5.0 — 2026-11-04

- Added a modular offline image-classification adapter with explicit catalogue/logit mapping and model file hashes; no classifier weights or performance claims are bundled.
- Added bounded per-crop scoring and equal-weight track aggregation, configurable score/margin gates, provisional assignments and explicit unidentified reasons.
- Added per-track gallery review, unknown selection, notes, reviewer and timestamp, downloadable review imports, validated correction history and reproducible JSON/CSV exports.
- Bound review imports to track and run metadata hashes; preserved model predictions independently of human corrections and retained review history on reruns.
- Added a small, extensible Caribbean starter catalogue for manual review, workflow/model contract documentation and species regression tests.
- Appearance groups remain browsing aids and never propagate species assignments. Default score gates are exploratory; open-set rejection, score calibration and field performance require validation.


## 0.4.0 — 2026-11-04

First source release to `marine-ecologist/openfish`; includes the existing desktop app and the Fish Gallery visual-similarity implementation.

### Added

- Chronological / Visual similarity gallery selector; chronological remains the default, with first-sighting time and track ID determining order.
- Offline DINOv2 Small embeddings aggregated from up to four original-color crop samples per track, with complete-link cosine clustering at distance 0.25.
- Appearance groups with chronological ordering within each group, plus an Ungrouped section for tracks without usable embeddings.
- `similarity.json` containing embeddings, group membership, missing tracks, model, threshold and availability status.
- Gallery rebuild command for completed runs; older runs fall back to their representative crop.
- Automated coverage for aggregation, clustering, bounded sampling, partial failures, offline fallback, HTML ordering and repeated gallery sort switching.

### Changed

- Desktop window, sidebar and macOS bundle version advanced from 0.3.0 to 0.4.0.

### Limitations

- Local model weights are required for similarity; missing weights or inference failures preserve chronological browsing.
- Groups describe appearance, do not merge tracking IDs, and do not establish species or individual identity. The clustering threshold is exploratory and clustering uses quadratic memory.
- Model weights, local environments, source videos and generated results are excluded from source control. `requirements-lock.txt` records the original local environment, including machine-specific wheel paths; it is not a portable installer.

## 0.3.0 — prior local version

- Added YOLO / RF-DETR detector selection, persisted video-correction preferences and responsive preview panels.
- Both detectors use the shared BoT-SORT tracking and export workflow; native appearance matching remains YOLO-only.

## 0.2.0 — prior local version

- Added video color correction with preview confirmation and adjustable detection/tracking settings.

## Initial local version

- Local macOS desktop workflow for video selection, fish detection, provisional tracking IDs, annotated playback, crops and chronological gallery export.
