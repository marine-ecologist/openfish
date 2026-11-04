# Training workspace

Open a completed run, then choose **Training** below Viewer. Both pages show the same track order and selection. Training replaces the video area with a 2×2 crop grid. The Viewer retains its playback position when changing pages; selecting another track seeks to that track. Species and review columns display saved human labels.

Enter a reviewer name, choose **Species confirmed** and a catalogue species, approve useful images, and click **Save track**. Alternatively choose **Unidentified** or **Exclude from training**. The starting manual catalogue is the explicit CoReFish Caribbean species crosswalk; any run prediction catalogue is also available. Model suggestions are not automatically confirmed. If the desired species is absent, leave the track unidentified until the catalogue is curated.

Label edits and checkbox choices survive row changes and Viewer/Training navigation. Drafts are also saved on navigation and close, in `training_drafts.json`; only **Save track** completes a review and adds its event to `training_labels.json`. Reopening restores saved labels and drafts. Files are bound to the track CSV and run metadata fingerprint; changed runs are rejected rather than silently relabelled. Draft writes can report disk errors; unsaved edits should be saved before closing if an error occurs.

## Images

The grid uses up to four available original-color cached crops: temporal samples plus the representative crop. It removes exact duplicate files and ranks readable crops by square-root pixel area (capped at 250,000 pixels) and capped grayscale edge variance. This is a quality heuristic, not a validated measure of taxonomic usefulness. Samples are not resized on disk; display scaling adds no detail. Fewer than four usable crops produce empty slots. This release does not re-extract extra views from the source video. Reviewer approval is essential for blurred, obscured, mixed-track or otherwise misleading images. Sample timestamps are not available for all older cached crops; their original paths and content hashes are retained.

## Export data

**Export data** unlocks when every track has a saved review outcome. Unidentified and excluded outcomes count as reviewed, without forcing a species guess. Edits still in draft must be saved first. Confirmed species tracks require at least one approved image.

Exports are stored within the run:

```text
training_exports/<snapshot-id>/
  README.txt
  manifest.json
  tracks.csv
  samples.csv
  images/<species-folder-id>/track_<id>_<crop-hash>.jpg
```

- `samples.csv`: one row per approved training image, with track ID, species ID, scientific name, image path, original crop path, SHA-256, width, height, source-video group and reviewer.
- `tracks.csv`: every track's review outcome, human label, reviewer, review time, notes and approved crop hashes. Unidentified/excluded tracks appear here but not as species training images.
- `manifest.json`: dataset fingerprint, original source-video path, grouping guidance, crop policy, catalogue entries, track records and image records.
- Images: original-resolution approved JPEG files, copied without enhancement or recompression. Species folder names are safe stable hashes; use the tables for their names.

Unchanged saved reviews and crops produce the same snapshot directory. Changed reviews create a new snapshot; existing snapshots remain intact. Export validates approved image hashes and detects damaged existing image copies. An entirely unidentified/excluded video can export its audit tables with zero training images.

No training happens when exporting, and no random train/test split is created. Keep whole source videos/surveys together during future training. The video-group identifier currently hashes the recorded absolute source path, not video content: renamed copies need cross-survey deduplication before splitting. Dataset manifests may contain local source paths and reviewer names; review these before sharing.

## Verification

```sh
python -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen /path/to/UI-python tests/check_training_ui.py /path/to/completed-run /tmp/training.png
```

The UI check uses a temporary run, never records test labels in the original survey, and checks synchronized selection, draft retention, save/reopen behavior and export gating.
