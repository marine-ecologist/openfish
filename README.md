# OpenFishID

Current version: **0.4.0**. See [CHANGELOG.md](CHANGELOG.md) for release history.

Local macOS desktop app for selecting reef videos, detecting fish, assigning provisional track IDs, and reviewing annotated playback. The dark sidebar, neutral panels, controls and workflow colors follow OpenReef's Qt styling (attribution in `ui/OPENREEF-LICENSE.txt`).

Open `OpenFishID.app` in this folder. Choose **New video → Choose video → Process → Run video**. When processing finishes, Viewer provides play/pause, frame stepping, scrubbing, playback speed, a searchable ID table, crops, and jump-to-first-sighting. Projects reopens completed runs; results are stored under `outputs/runs/`. The original trial appears as `fishcount.MP4` when complete.

Version 0.2 adds correction in **Video**: enable it, adjust red/blue balance, black/white thresholds, shadow brightness, local contrast, saturation and sharpening, then inspect original/corrected stills at several timestamps. Choose **Use these settings** before running. Changing the source, correction values or preview time requires fresh confirmation. Values are fixed through the video, and the same correction runs before detection and before final playback rendering. Original-resolution review crops retain the source colors.

Under **Process → 1 Fish detection & tracking**, adjust detection, weak-detection recovery, strong-match and new-ID thresholds, missing-track memory in seconds, matching tolerance, overlap suppression, detector resolution and experimental appearance matching. Tooltips explain each field. The continuity starting point uses thresholds 0.10 / 0.10 / 0.25 / 0.35 and a three-second memory. These are starting values to evaluate, not validated accuracy improvements. Trial comparison thresholds reproduce the original pass's effective confidence cutoff and approximately one-second memory.

Each new run saves `settings.json`, the resolved `tracker.yaml`, and settings in `run.json` / `summary.json`. Controls are frozen during a run. Existing result IDs are not merged by changing settings; process the source again to evaluate a new configuration. Color correction can also increase false detections, and longer memory / looser matching can merge different fish. Appearance matching uses the detector's native features and remains experimental.

This local build uses the existing OpenReef PySide6 runtime at `/Users/heliopora/GitHub/openreef/.venv/bin/python` for its interface, and this project's `.venv` for detection. Keep the app bundle in this project folder. An independent UI runtime can be installed with `python3.12 -m venv .ui-venv` followed by `.ui-venv/bin/pip install PySide6==6.12.0`; the launcher prefers it when present. Processing requires FFmpeg on PATH and the downloaded model in `models/`.

Version 0.3 adds **YOLO / RF-DETR** selection in Process. YOLO uses CFD YOLOv12x; RF-DETR uses the official CFD Small 1024 checkpoint. Both feed the same BoT-SORT tracking and exports. Native appearance matching is currently YOLO-only; RF-DETR disables that control and the YOLO-specific overlap-suppression control. RF-DETR runs one frame per batch in full precision on the local GPU. Choosing it does not establish that it is more accurate on this footage; compare reviewed examples and count misses, false detections and ID switches separately. SAM 2 is reserved for a subsequent tracking stage.

Video correction values, enable state, source file and still timestamp are saved automatically in `.runtime/video_preferences.json` and restored between sessions. Saved correction values are retained when opening a previous result; preview confirmation is renewed for processing. Invalid black/white combinations do not overwrite the last valid saved correction. Original and corrected stills now occupy the full width, vertically stacked, and follow window resizing. Hover a navigation tab, a setting label marked ⓘ, or its control for wrapped explanations of what increasing or decreasing it does.

RF-DETR checkpoint provenance is stored in `models/rfdetr-source.json`. SHA-256: `da078e3cbd7120f5e1880c66723b21e62acad7260adddc4ac7f32fe1468aa49a`. The installed RF-DETR package and weights are local; worker inference runs with Hugging Face offline mode enabled. Project model releases: https://github.com/filippovarini/community-fish-detector/releases

## Trial processing

Local processing of `fishcount.MP4` with the single-class Community Fish Detector YOLOv12x and Ultralytics BoT-SORT. No video is uploaded.

Source: `/Users/heliopora/openfishID/videos/fishcount.MP4` (3840 × 2160, 30000/1001 fps, 5052 frames, 168.5684 seconds).

Model: https://github.com/filippovarini/community-fish-detector/releases/tag/cfd-1.00-yolov12x

Tracking documentation: https://docs.ultralytics.com/modes/track/

Run from this folder:

```sh
PYTORCH_ENABLE_MPS_FALLBACK=1 .venv/bin/python track_fish.py
.venv/bin/python finalize.py
```

`outputs/full/detections.csv` contains frame-level bounding boxes in original 4K pixel coordinates and timestamps relative to clip start. `tracks.csv` summarizes provisional tracks. Final IDs are consecutive; `raw_tracker_id` preserves BoT-SORT's IDs, and the `_raw.csv` files preserve the original tables. Each `crops/fish_NNNN.jpg` is the highest-confidence detected crop for the final ID, rather than a species identification. `fishcount_tracked.mp4` is the final 1080p review video with original audio and readable ID labels. `fish_ID_gallery.html` is a portable crop gallery. `run.json` records settings and processed frame count; `summary.json` adds final validation results.

The run uses batches of eight for detection in half precision, then updates one persistent BoT-SORT tracker sequentially for every frame. Metal GPU access may require running outside the desktop sandbox. `requirements-lock.txt` records the installed environment. Model SHA-256: `0b259afb3dca1d1d7f9d842ebf136884b2e3706b151172b266bb24e07f2b8e98`.

This is an unvalidated initial pass. Track IDs are continuous sightings, not confirmed unique biological individuals. Occlusion, missed detections, crossings and re-entry can split or swap IDs. Short tracks and detections against complex coral backgrounds need review. Counts of tracks must not be reported as fish abundance. Single-class detection does not establish species. Full-frame inference at 1024 pixels can miss small or distant fish; original-resolution crops are retained for review.

## Fish Gallery sort order

Fish Gallery now offers **Sort order → Chronological / Visual similarity**. Chronological is the default and sorts by first sighting, with track ID breaking ties. Similarity displays appearance groups, retaining chronological order within each group; tracks with unusable crops appear under Ungrouped. Grouping does not merge IDs or assign species.

New tracking runs retain up to four confident, original-color crops per track (one best crop per rotating one-second slot, rejecting crops smaller than 16 pixels). DINOv2 Small extracts CLS embeddings using its supplied image processor; normalized crop vectors are averaged and normalized per track. Complete-link hierarchical clustering uses cosine distance 0.25, preventing similarity chains. This is an exploratory threshold, not a validated species boundary. `similarity.json` records normalized vectors, group membership, missing tracks, model and threshold. Clustering uses quadratic memory in the number of tracks.

Inference is offline, using `models/dinov2-small` or cached `facebook/dinov2-small`. Set `OPENFISHID_SIMILARITY_MODEL` to use another local DINOv2 directory. To install the standard weights once with internet access:

```sh
.venv/bin/python -c 'from huggingface_hub import snapshot_download; snapshot_download("facebook/dinov2-small", local_dir="models/dinov2-small", allow_patterns=["config.json", "preprocessor_config.json", "model.safetensors"])'
```

Rebuild an existing gallery without detection or video encoding:

```sh
.venv/bin/python fish_gallery.py --output outputs/runs/20261103-211517-6fec1f
```

Older runs use their single representative crop. Missing weights, unreadable crops or inference failures leave the chronological gallery usable; similarity is disabled when no embeddings are available. Rebuilding regenerates embeddings. No footage is uploaded. Implementation follows the [Transformers DINOv2 API](https://huggingface.co/docs/transformers/model_doc/dinov2).

Run verification with `.venv/bin/python -m unittest discover -s tests -v`. Test the generated sort-switching script with `node tests/gallery_sort.cjs outputs/runs/20261103-211517-6fec1f/fish_ID_gallery.html`.
