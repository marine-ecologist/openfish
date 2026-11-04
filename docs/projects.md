# Portable projects

OpenFish 0.7 adds **Export project…** in Projects and Viewer, and **Import project…** in Projects. Export copies the current completed run and its original video into a new folder. Import verifies that folder, copies it into the receiving computer’s `outputs/projects/` library and opens it in Viewer. Detection is not rerun. Import creates a separate copy and never overwrites another project.

```text
openfish-project-<date>-<id>/
  project.json
  video/
    original.mp4
  results/
    run.json
    summary.json
    tracks.csv
    detections.csv
    fishcount_tracked.mp4
    crops/                         Representative fish_<ID>.jpg crops
    similarity_samples/            Additional samples, using raw tracker IDs
    training_catalog.json
    training_labels.json           If reviewed
    training_drafts.json           If draft edits exist
    training_exports/              If training snapshots exist
    species_predictions.json       If classification was run
    ...other result files...
```

Original-video extension is retained. All crop/ID directories and existing raw/final track mappings stay intact. The redundant `annotated_silent.mp4` intermediate is omitted from exported packages; the review playback video is included. Model weights and Python environments are not included. The receiving machine needs a compatible openFish installation, but does not need detector weights merely to review the project.

## Share a classified project

1. Save reviewed tracks in Training. Drafts can travel too, but remain drafts.
2. Choose **Export project…**, then a destination parent folder. If the original video is unavailable, locate the correct original when prompted. The legacy run does not have an independently verified original-video hash, so selecting the correct file is the user’s responsibility.
3. Copy the entire generated folder to the colleague. It can be zipped with normal operating-system tools for transport; unzip before importing. The app currently imports folders, not ZIP files.
4. On the receiving computer, choose **Projects → Import project…** and select the folder containing `project.json`.
5. Continue in Viewer or Training. To return changes, export a fresh project folder and import that version on the other computer. Imports preserve separate versions; they do not merge concurrent reviewers’ edits.

## Persistence and integrity

The project manifest stores relative video/result paths and SHA-256 checksums. Import verifies all packaged files, rejects missing/changed files, symbolic links and paths escaping the package, then verifies the copied files again. A failed import does not leave a partial visible project. Large video copying and hashing run in a background thread; the window remains responsive but editing/closing is blocked during transfer to protect consistency.

`run.json` and `tracks.csv` remain byte-identical. Training and species review fingerprints therefore remain valid after moving between computers. The Viewer resolves the bundled source using `project.json`; it does not rewrite old source paths inside provenance records. The exported manual species catalogue travels with the project.

New desktop processing runs are created directly under `outputs/projects/<run-id>/`, copying the source into `video/` before processing into `results/`. This consumes additional disk space and leaves the camera original untouched. Legacy `outputs/runs/` and `outputs/full/` remain discoverable. Export migrates a completed legacy run into the same portable layout.

Local reviewing changes files, so the original transfer manifest becomes outdated. This does not block local review, but a fresh **Export project…** is required before importing that edited project elsewhere; it generates current checksums. Keep local projects in a writable folder. Original paths, reviewer names and notes remain in project records; review them before sharing.

**Export data** in Training remains separate: it exports only the training snapshot, not a portable video project.
