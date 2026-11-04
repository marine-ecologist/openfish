"""Portable Fish Gallery; can also rebuild existing completed runs."""
import base64
import csv
import html
import json
from pathlib import Path
from fish_similarity import build_similarity


def write_gallery(out, tracks, run):
    out = Path(out)
    similarity = build_similarity(out, tracks)
    ordered = sorted(tracks, key=lambda t: (float(t['first_s']), int(t['track_id'])))
    group_by_id = {ident: n for n, group in enumerate(similarity['groups'], 1) for ident in group}
    cards = []
    for track in ordered:
        ident = int(track['track_id'])
        crop = out / 'crops' / f'fish_{ident:04d}.jpg'
        try:
            image = '<img alt="Fish crop" src="data:image/jpeg;base64,' + base64.b64encode(crop.read_bytes()).decode() + '">'
        except OSError:
            image = '<p>Crop unavailable</p>'
        detail = html.escape(f"{track['first_s']}–{track['last_s']} seconds · {track['detections']} detections · peak confidence {track['best_confidence']}")
        if int(track['detections']) < 15:
            detail += ' · brief track'
        cards.append(f'<article data-group="{group_by_id.get(ident, 0)}"><h2>Fish {ident:04d}</h2>{image}<p>{detail}</p><p class="muted">Unreviewed · species unassigned</p></article>')
    disabled = '' if similarity['status'] == 'ready' else ' disabled'
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Fish Gallery</title><style>
body{font:16px system-ui;background:#eef5f4;color:#143132;margin:32px}main{max-width:1400px;margin:auto}p{line-height:1.6}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:20px}article{background:white;padding:18px;border-radius:12px}h2{font-size:20px}img{width:100%;height:210px;object-fit:contain;background:#102a2b}.muted{color:#536d6e;font-size:14px}select{font:inherit;padding:8px}section{margin:24px 0}</style></head><body><main><h1>Fish Gallery</h1>'''
    page += f'<p>{len(tracks)} provisional tracks · {run["total_frames"]/run["source_fps"]:.3f} seconds · {html.escape(run["model"])} · all {run["total_frames"]:,} frames processed.</p>'
    page += '<p>IDs identify continuous sightings. Occlusion and re-entry can create duplicate or swapped IDs. This is not a count of unique fish. Similar appearance does not establish species or individual identity.</p>'
    page += f'<label for="sort-order">Sort order </label><select id="sort-order"><option value="chronological">Chronological</option><option value="similarity"{disabled}>Visual similarity</option></select><p role="status">{html.escape(similarity["message"])}</p><div id="gallery"><div class="grid">' + ''.join(cards) + '</div></div>'
    page += '''</main><script>
const gallery = document.getElementById('gallery');
const cards = Array.from(gallery.querySelectorAll('article'));
document.getElementById('sort-order').addEventListener('change', event => {
  gallery.replaceChildren();
  if (event.target.value === 'chronological') {
    const grid = document.createElement('div'); grid.className = 'grid';
    grid.append(...cards); gallery.append(grid); return;
  }
  const groups = new Map();
  for (const card of cards) {
    const key = Number(card.dataset.group);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(card);
  }
  for (const key of Array.from(groups.keys()).sort((a,b) => (a===0)-(b===0) || a-b)) {
    const section = document.createElement('section');
    const heading = document.createElement('h2');
    heading.textContent = key ? `Appearance group ${key}` : 'Ungrouped — embedding unavailable';
    const grid = document.createElement('div'); grid.className = 'grid';
    grid.append(...groups.get(key)); section.append(heading, grid); gallery.append(section);
  }
});
</script></body></html>'''
    (out / 'fish_ID_gallery.html').write_text(page)
    return similarity


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output)
    with (out / 'tracks.csv').open() as stream:
        tracks = list(csv.DictReader(stream))
    write_gallery(out, tracks, json.loads((out / 'run.json').read_text()))
