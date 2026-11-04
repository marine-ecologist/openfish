# Changelog

## 0.7.0 — 2026-11-04

- Added project export/import with bundled original video, result/ID folders, classifications, drafts, training snapshots and a pinned manual catalogue.
- Imported projects appear in the local Projects library without detection reruns; relative source paths preserve portability while original run files remain unchanged.
- New desktop processing runs now keep their copied source video and processing outputs inside one discrete project folder.
- Added background copy/verification, checksums, safe-path checks, non-overwriting imports and round-trip tests for review persistence and re-export.


## 0.6.0 — 2026-11-04

- Replaced the sidebar logo and macOS app icon with a transparent, left-facing teal fish clipart mark; retained SVG and PNG assets.

- Added Training below Viewer, with synchronized Fish Tracks tables, a 2×2 original-color image grid, species labels, explicit unidentified/excluded outcomes, crop approval, reviewer and notes.
- Saved labels and resumable drafts per run; Viewer/Training navigation preserves selected tracks and label edits.
- Added gated, versioned training exports containing approved images, samples.csv, tracks.csv and a provenance manifest. Unknown/excluded tracks remain audit records, not species training examples.
- Added persistence, export-integrity and desktop UI checks; crop selection ranks available cached views by size and edge detail and does not infer identity from clusters.

### Also included

- Added a default Caribbean-candidate benchmark view using the full explicit CoReFish species catalogue, with an unrestricted comparison. Original probability mass and score gates are preserved; regional results and allowlist provenance are exported separately.

## 0.5.1 — 2026-11-04

- Added the offline Fishial v0.10.2 TorchScript adapter, using embedded model labels and native ArcFace softmax scores; natural-centroid cosine scores remain a separate diagnostic.
- Added reproducible bounded CoReFish sampling, selective ZIP downloads with CRC validation, crop/track benchmarking, per-species metrics and confusion exports.
- Ran a 61-track / 183-crop pilot across 33 species. Multi-view top-1 was 6/45 on covered species, and all 18 accepted softmax assignments were wrong. This model remains experimental and requires manual verification.
- Checked adapter parity against the bundle’s own inference code on six crops.
- Added visible top-three suggestions, additional track views, clearer review controls and a 36-track local-footage review set. Local accuracy awaits human labels.
- Added metric regression tests and documented model/data provenance, licence limits and reproduction steps.


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
