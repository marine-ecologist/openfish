# OpenFishID

![OpenFishID showing tracked fish in reef video](docs/images/openfishid-viewer.png)

OpenFishID helps people explore fish life in underwater video. It brings fish detection, tracking and visual review into one desktop app, making reef footage easier to study for researchers, conservation teams, divers and anyone curious about marine life.

Videos are processed locally on your Mac, so your footage stays with you.

## What it offers

- **Find fish in video** with automated detection and provisional tracking.
- **Review sightings** with annotated playback, frame-by-frame viewing and a searchable fish list.
- **Explore the Fish Gallery** chronologically or in groups of similar-looking fish.
- **Improve underwater visibility** with adjustable color correction and preview comparisons.
- **Build a training dataset** in the [Training workspace](docs/training.md), with track labels, crop approval and versioned exports.
- **Review species assignments** in the Fish Gallery and export corrections with their review history.
- **Share classified projects** through [portable project export/import](docs/projects.md), including video, crops and review records.
- **Revisit projects** to explore previously processed footage.

## In development

OpenFishID is an early research tool for macOS. Detections and tracks need human review: fish may be missed, and the same fish can receive more than one track ID. Track totals are not counts of unique fish.

Visual similarity groups help with browsing; they do not identify species or confirm that sightings show the same individual. Phase 3 adds optional local species classification, confidence scores and per-track manual review. A trained Caribbean classifier is not bundled; without one, tracks remain unidentified. See the [species workflow](docs/species-identification.md) and [pretrained-model pilot](docs/fishial-trial.md).

Current version: **0.7.1** · [Release history](CHANGELOG.md)

## Acknowledgements

OpenFishID builds on Community Fish Detector, YOLO, RF-DETR, BoT-SORT and DINOv2. Its interface styling draws on OpenReef, with attribution included in the project.
