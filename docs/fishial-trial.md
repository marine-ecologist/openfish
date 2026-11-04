# Fishial / CoReFish pilot

This experiment runs an existing trained model before any regional fine-tuning. It does not assign taxonomy from appearance clusters.

## Sources and scope

- [Fishial official repository](https://github.com/Wye-Foundation/Fishial-Fish-Identification): downloadable v0.10.2 classifier bundle, 866 embedded class labels. The checkpoint's own embedded mapping is authoritative; the repository's separate labels.json has a different class count and is not used.
- [Official model archive](https://storage.googleapis.com/fishial-ml-resources/classification_model_v0.10.2.zip): DinoV2 + ViT pooling with ArcFace outputs and embedded natural centroids. The distributed info.json specifies input height 154, width 434, despite the architecture's “224” name.
- [CoReFish](https://warplab.github.io/corefish/): expert-labelled Caribbean survey data. Dataset licence: CC BY-NC-SA 4.0. Downloaded data, crops, model weights and local footage remain outside the Git source tree.
- [Smithsonian Caribbean fish inventory update](https://stri-sites.si.edu/docs/publications/pdfs/Estape_et_al_2025_Colombian_continental_coast_fishes.pdf) and [WoRMS](https://www.marinespecies.org/aphia.php?id=273718&p=taxdetails) inform explicit synonym handling. Closely related but distinct taxa such as Stegastes xanthurus / S. variabilis and Acanthurus tractus / A. bahianus are not silently equated.

The crosswalk in `experiments/prepare_trial.py` interprets category codes and common names explicitly. Generic fish, family/genus-only and ambiguous categories are excluded from species scoring. This is a reviewable crosswalk, not an assertion that all dataset taxonomy has been independently audited.

## Fixed protocol

Select at most two tracks per explicitly mapped species, using seed 20261104. Require a single consistent category across the track, at least three available views with crop sides >=16 pixels, and image entries present in the ZIP. Select first, middle and last eligible views. Selection never uses model predictions. One species loses eligibility because its referenced images are absent from the archive.

The realized pilot contains 61 tracks, 183 crops and 33 species. Twenty-four species are in the checkpoint's catalogue; nine are outside it. The full CoReFish publication totals do not describe this pilot: the downloaded species COCO table contains a subset of the larger collection.

Preprocessing reproduces the bundle's box-only fallback: RGB conversion, OpenCV linear resize to 154×434, scaling to [0,1], ImageNet mean/std normalization. No segmentation, polygon rotation, TTA or colour enhancement is applied. Inference runs locally on CPU with four torch threads.

Two scoring methods are kept separate:

1. Primary: softmax of native ArcFace logits. Accept provisionally at score >=0.8 and runner-up margin >=0.2.
2. Secondary diagnostic: maximum cosine similarity to natural centroids per species. Accept at cosine >=0.7 and margin >=0.05. These are cosine scores, not probabilities.

Compare all individual crops, the first view per track and equal-weight mean class scores across three views. Thresholds were fixed before observing outcomes; they are exploratory choices, not fitted or validated operating points. No regional filtering removes implausible model suggestions. Exact permitted aliases map to the same species; unknown categories never become species ground truth.

Report covered-species top-1/top-3, acceptance/unidentified rates, accepted precision, confidently wrong assignments and rejection of species absent from the model. Save per-species precision/recall, confusion counts and full crop/track scores. Null metrics mean there was no denominator, not zero accuracy.

This is an external-dataset pilot. Model training overlap with CoReFish is not established. Only one or two tracks represent each species, and tracks within a survey may be correlated. These results cannot establish general field accuracy or calibrated confidence.

## Reproduce

Run from the repository using an environment with torch, numpy, Pillow, OpenCV and requests. The app's existing environment contains these. `corefish_fetch.py` reads the ZIP directory and metadata through HTTP byte ranges; `fetch_sample.py` fetches only selected frames and verifies their ZIP CRCs. The full archive is about 40.3 GB, so no full download is required.

```sh
mkdir -p outputs/species_trial
curl -L --fail -o outputs/species_trial/fishial-v0.10.2.zip \
  https://storage.googleapis.com/fishial-ml-resources/classification_model_v0.10.2.zip
python experiments/prepare_fishial.py \
  --archive outputs/species_trial/fishial-v0.10.2.zip \
  --out outputs/species_trial/fishial-model \
  --labels-output outputs/species_trial/fishial_labels.json
python experiments/corefish_fetch.py outputs/species_trial/corefish
python experiments/prepare_trial.py outputs/species_trial
python experiments/fetch_sample.py outputs/species_trial
python experiments/run_species_trial.py --root outputs/species_trial --benchmark
```

The run records model and input hashes, software versions, selection manifest and unrounded scores. Fishial code is published under MIT; retain upstream attribution and check model/data terms for redistribution. No weights or dataset imagery are included in this source release.

To use the adapter in the normal gallery workflow:

```sh
export OPENFISHID_SPECIES_MODEL=/absolute/path/to/outputs/species_trial/fishial-model
python fish_gallery.py --output /absolute/path/to/RUN
```

## Local footage review

The local trial selects 36 chronological, evenly spaced tracks with at least 15 detections from the existing 25.826-second run. It copies representative crops and up to four original-color samples per track into a separate review folder; original outputs are preserved. This is an inspectable subset, not a population-level sample.

```sh
python experiments/run_species_trial.py --root outputs/species_trial \
  --local-source /absolute/path/to/original/RUN
```

The generated gallery shows the top three model suggestions, raw scores, track views, provisional/unidentified status and per-track correction controls. Enter a reviewer name, choose a species or Unidentified, mark reviewed, then download the review file. Import it and evaluate:

```sh
python species.py --output outputs/species_trial/local_review --reviews /path/to/species_review_import.json
python experiments/evaluate_local_reviews.py outputs/species_trial/local_review
```

Species-level agreement is calculated only for human-resolved tracks. Human-unidentified tracks remain unresolved, not automatically labelled as outside the classifier. Because suggestions are visible, this is assisted review rather than a blinded independent test. Until reviews exist, local accuracy remains null. Local suggestions must not be used as their own ground truth.

## Results — 2026-11-04

| Method | Covered-track top-1 | Covered-track top-3 | Accepted / all tracks | Correct accepted |
|---|---:|---:|---:|---:|
| First crop, softmax | 0/45 (0%) | 1/45 (2.2%) | 49/61 | 0/49 |
| Three-view mean, softmax | 6/45 (13.3%) | 13/45 (28.9%) | 18/61 | 0/18 |
| First crop, cosine | 0/45 (0%) | 0/45 (0%) | 0/61 | Not applicable |
| Three-view mean, cosine | 6/45 (13.3%) | 8/45 (17.8%) | 0/61 | Not applicable |

The primary multi-view rule left 43/61 tracks unidentified (70.5%). It rejected 12/16 outside-catalogue tracks (75%), but falsely accepted four of them. All 18 accepted assignments, including 14 covered-species tracks, were wrong. The first-view baseline uses the earliest eligible crop, not an optimally selected representative crop; this comparison does not prove averaging is always better. Across all individual crops, softmax top-1 on covered species was 16/135 (11.9%).

Crops are often difficult: the median shorter crop side is about 39 pixels, and many have substantial colour cast or partial views. These are possible contributors, not established causes. No ablation established whether segmentation, better crops or regional fine-tuning would resolve the failures.

The adapter reproduced the vendor's top-three predictions on six checked crops, with maximum softmax difference below 0.000003. Saved benchmark scores matched the adapter exactly on those checks. The original bundle's inference code and Albumentations 2.0.8 were used for this comparison, with dependencies isolated in the trial folder. Torch warns that TorchScript loading is unsupported on Python >=3.14; this run used Python 3.15 and torch 2.15, and cross-version reproducibility is not established.

**Decision:** keep this model as an experimental review aid. Do not use its threshold-passing outputs as reliable automatic species IDs. The next model experiment should address the actual video crop domain and include regional coverage and unknown-taxon testing.

The local review set contains 36 tracks: nine provisional assignments and 27 unidentified tracks under the same initial policy. These numbers describe model decisions, not correctness. User verification is pending; local accuracy is not reported.

- [Machine-readable summary and provenance](benchmarks/fishial-corefish-2026-11-04.json)
- [Per-species softmax precision/recall](benchmarks/softmax_per_species.csv)
- [Top-1 confusion counts](benchmarks/softmax_top1_confusion.csv)
- [Gated-assignment confusion counts](benchmarks/softmax_gated_confusion.csv)
- [Per-species cosine results](benchmarks/cosine_per_species.csv)

To render the reference crop gallery after benchmarking:

```sh
python experiments/render_trial_report.py outputs/species_trial
```

The renderer expects the local review folder to exist. Optional vendor parity check:

```sh
python -m pip install --target outputs/species_trial/verification_deps albumentations==2.0.8
python experiments/verify_fishial_adapter.py outputs/species_trial
```
