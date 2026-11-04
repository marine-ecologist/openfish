# Phase 3: species identification

The workflow adds species evidence to existing provisional track IDs. It does not merge tracks, count unique fish or infer taxonomy from DINOv2 groups. Tracking and grouping algorithms are unchanged.

## Use

New completed runs generate species outputs alongside the gallery. Existing runs can be rebuilt:

```sh
python fish_gallery.py --output outputs/RUN
```

Without a configured classifier, every automatic assignment is `unidentified`. The three-entry `catalogs/caribbean_starter.json` is an illustrative manual-review starting list, not a complete regional checklist. Use `OPENFISHID_SPECIES_CATALOG=/absolute/path/catalog.json` for a curated survey catalogue keyed by stable species IDs, with `scientific_name` and optional `common_name`. Taxonomic authority, regional coverage and juvenile/color-phase coverage should be documented with your catalogue. Unlisted fish should remain unidentified.

In the gallery, enter a reviewer name, choose the species or Unidentified, add a note and click **Mark reviewed** for each track. Download reviews, then import them:

```sh
python species.py --output outputs/RUN --reviews /path/species_review_import.json
python fish_gallery.py --output outputs/RUN
```

The portable HTML cannot write back to a run folder. Staged edits are lost on page reload unless downloaded. Imports require a reviewer, timezone-aware timestamp, known track/catalogue ID and matching dataset fingerprint (track CSV plus run JSON). Imports append history; the last imported correction wins. Re-importing identical events is idempotent. Corrections affect only explicitly reviewed tracks, even when the gallery is sorted by appearance. Rebuilding displays persisted corrections. Never edit the prediction/export files to record corrections.

## Local model contract

Set `OPENFISHID_SPECIES_MODEL` to a local Hugging Face `AutoModelForImageClassification` directory containing processor configuration, weights and `species_manifest.json`. It uses local files only, runs on CPU in evaluation/inference mode and never silently downloads weights. Existing dependencies include torch, transformers and Pillow; the historical requirements lock is machine-specific.

Example manifest (illustrates the contract, not a trained model):

```json
{
  "model_id": "your-caribbean-classifier",
  "revision": "immutable-training-artifact-id",
  "labels": ["acanthurus_coeruleus", "abudefduf_saxatilis"],
  "catalog": {
    "acanthurus_coeruleus": {"scientific_name": "Acanthurus coeruleus"},
    "abudefduf_saxatilis": {"scientific_name": "Abudefduf saxatilis"}
  }
}
```

`labels` must exactly match the trained model's logit order, with one unique catalogue ID per output. Document training data, license, geographic scope, exclusions and any measured validation separately. All model files are SHA-256 fingerprinted in predictions. An alternative adapter can be passed to `build_species`: expose `labels`, `manifest` and a callable accepting one crop path and returning a complete normalized score dictionary. This keeps model selection independent of tracking, grouping and review.

## Decisions and limits

Reuse up to four original-color temporal samples, mapped via raw tracker ID, with representative crop fallback for older runs. Unreadable or invalid-score samples are recorded and excluded. Average valid crop score vectors equally; correlated frames are not independent evidence. Select the largest mean score only when it reaches 0.8 and exceeds the runner-up by 0.2. Defaults are exploratory policy choices, not validated operating points. Configure alternatives with:

```sh
python species.py --output outputs/RUN --threshold 0.85 --margin 0.25
```

This standalone command updates species exports. Gallery rebuilding preserves the saved score and margin gates. Missing models, unusable crops, low scores and ambiguous results remain unidentified with explicit reasons. Threshold-passing results are **provisional**, never human-verified. Softmax scores are not measured accuracy or calibrated probabilities. High scores cannot reliably detect out-of-catalogue taxa; unidentified handling is a review policy, not validated open-set recognition. Local field validation must cover held-out videos, species confusion, unknown taxa, juveniles, lighting, calibration and track fragmentation before ecological use.

## Outputs and reproducibility

- `species_predictions.json`: automatic scores, candidates, reasons, model manifest and hashes, sample hashes/paths, aggregation, policy and dataset fingerprint.
- `species_reviews.json`: append-only imported correction history, kept separate from automatic evidence.
- `species_tracks.csv`: one row per provisional track, final assignment/status, original model assignment/confidence and latest review metadata.
- `species_export.json`: prediction provenance, complete review history and final rows in one artifact.

Exports have deterministic track/key ordering and no generated export timestamp. Identical inputs, scores and history yield identical bytes. Model inference can vary across software/hardware; preserve the environment, original run, crops, model directory and exported scores for reproducibility. A changed track/run fingerprint rejects existing reviews rather than silently applying them. Archives do not include source footage or model weights. CSV fields use standard quoting; treat human-entered text as text when importing into spreadsheets.

## Validation

```sh
python -m unittest discover -s tests -v
node tests/test_species_review.cjs
```

Tests use synthetic scores to check behavior, not fish-identification performance. No trained classifier or labelled Caribbean validation dataset is supplied with this release.
