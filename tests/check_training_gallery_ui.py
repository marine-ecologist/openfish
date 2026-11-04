"""Native two-stage workflow regression; edits stay inside a temporary fixture."""
import json
import os
import sys
import tempfile
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from PySide6.QtWidgets import QApplication
from ui.training_panel import TrainingPanel
app=QApplication([])
with tempfile.TemporaryDirectory() as directory:
    out=Path(directory);(out/'tracks.csv').write_text('track_id\n1\n2\n3\n');(out/'run.json').write_text('{"source":"/survey/video.mp4"}')
    (out/'similarity.json').write_text(json.dumps(dict(groups=[[1,2],[3]],status='ready')))
    (out/'crops').mkdir()
    for i in range(1,4):Image.new('RGB',(80,60),(i*50,80,100)).save(out/'crops'/f'fish_{i:04d}.jpg')
    tracks=[dict(track_id=i,first_s=i,detections=20) for i in range(1,4)]
    panel=TrainingPanel();panel.load(out,tracks)
    assert panel.tabs.tabText(0)=='Gallery' and panel.tabs.tabText(1)=='Individual'
    assert panel.tabs.currentIndex()==0
    gallery=panel.gallery
    gallery.controls[1].setCurrentIndex(1);species=gallery.controls[1].currentData()
    assert gallery.controls[2].currentData()==species
    assert not panel.store.label(1) # only explicit group save confirms labels
    gallery.controls[2].setCurrentIndex(gallery.controls[2].findData('unidentified'))
    assert gallery.controls[1].currentData()==species
    restored=TrainingPanel();restored.load(out,tracks)
    assert restored.gallery.pending[1]==species and restored.gallery.pending[2]=='unidentified'
    panel.reviewer.setText('Fixture reviewer');gallery.commit_ready();assert panel.store.label(1)['species_id']==species
    assert panel.store.label(2)['status']=='unidentified'
    assert gallery.ticks[1].text()=='✓ Saved' and gallery.group_ticks[0][1].text()=='✓ All saved'
    gallery.open_individual(1);assert panel.tabs.currentIndex()==1 and panel.current==1
    panel.checks[0].setChecked(False)
    assert panel.store.label(1)['approved']==[] # image deselection autosaved immediately
    panel.move_track(1);panel.move_track(-1);assert not panel.checks[0].isChecked()
    reopened=TrainingPanel();reopened.load(out,tracks);assert reopened.store.label(1)['approved']==[]
    assert not reopened.export_button.isEnabled()
    gallery.controls[1].setCurrentIndex(gallery.controls[1].findData('sparisoma_viride'))
    assert panel.store.label(1)['phase']=='unassessed'
    gallery.phase_controls[1].setCurrentIndex(gallery.phase_controls[1].findData('terminal'))
    assert panel.store.label(1)['phase']=='terminal'
    assert panel.store.label(2)['phase']=='unassessed' # species propagates; phase does not
    gallery.open_individual(1)
    assert panel.phase.currentData()=='terminal'
    panel.phase.setCurrentIndex(panel.phase.findData('initial'))
    assert panel.store.label(1)['phase']=='initial'
    gallery.controls[1].setCurrentIndex(gallery.controls[1].findData('acanthurus_coeruleus'))
    assert panel.store.label(1)['phase']=='not_applicable'
    assert not gallery.phase_controls[1].isEnabled()
    panel.close();restored.close();reopened.close()
print('Gallery propagation, reviewer-gated autosave, exception, ticks and crop autosave passed')
