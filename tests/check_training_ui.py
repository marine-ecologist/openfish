"""Run with the existing Qt UI environment; all label edits use a temporary run."""
import csv
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from openfishid_gui import Window

source=Path(sys.argv[1]).resolve(); screenshot=Path(sys.argv[2]).resolve()
app=QApplication([])
with tempfile.TemporaryDirectory() as directory:
    out=Path(directory)
    for name in ['summary.json','run.json','tracks.csv','detections.csv']:
        shutil.copyfile(source/name,out/name)
    for name in ['crops','similarity_samples','fishcount_tracked.mp4','review_00000.jpg']:
        if (source/name).exists():(out/name).symlink_to(source/name)
    window=Window();window.load_result(out);window.show();app.processEvents()
    assert window.nav[4].text()=='Training'
    panel=window.training
    window.navigate(4);panel.table.selectRow(2);app.processEvents()
    assert window.table.currentRow()==2
    panel.reviewer.setText('UI verification fixture')
    panel.outcome.setCurrentIndex(panel.outcome.findData('species'));panel.species.setCurrentIndex(1);panel.note.setText('Temporary test label; not expert truth')
    window.navigate(3);window.navigate(4)
    assert panel.note.text()=='Temporary test label; not expert truth'
    panel.table.selectRow(3);panel.table.selectRow(2)
    assert panel.note.text()=='Temporary test label; not expert truth'
    panel.save_track()
    assert panel.store.label(int(window.tracks[2]['track_id']))['status']=='species'
    assert window.table.item(2,3).text()==panel.species.currentText()
    assert not panel.export_button.isEnabled()
    panel.load(out,window.tracks);panel.table.selectRow(2)
    assert panel.outcome.currentData()=='species'
    assert panel.note.text()=='Temporary test label; not expert truth'
    # Capture a pending track so the screenshot contains no synthetic species label.
    panel.current=None
    for name in ['training_labels.json','training_drafts.json']:
        if (out/name).exists():(out/name).unlink()
    panel.load(out,window.tracks);window.refresh_species_columns();panel.reviewer.clear()
    row=next((n for n,t in enumerate(window.tracks) if len(panel.store.samples[int(t['track_id'])])==4),5)
    panel.table.selectRow(row);window.navigate(4);app.processEvents();window.grab().save(str(screenshot))
    assert len(panel.pictures)==4
    window.close();app.processEvents()
print('Training UI navigation, selection, draft retention, save, reopen and export gate passed')
