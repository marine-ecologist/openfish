"""Track-based Training workspace; labels are saved independently of model guesses."""
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QTabBar,QStackedWidget,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QSplitter,QLineEdit,QComboBox,QCheckBox,QPushButton,QMessageBox)
import json
from training import TrainingStore, atomic_json
from ui.training_gallery import TrainingGallery


class TrainingPanel(QWidget):
    selected = Signal(int)
    labels_changed = Signal()

    def __init__(self):
        super().__init__(); self.store=None; self.tracks=[]; self.current=None; self.drafts={}; self.loading=False
        layout=QVBoxLayout(self)
        self.tabs=QTabBar();self.tabs.addTab('Gallery');self.tabs.addTab('Individual');layout.addWidget(self.tabs)
        self.summary=QLabel('Open a completed result in Projects or Viewer.');layout.addWidget(self.summary)
        tools=QHBoxLayout();tools.addWidget(QLabel('Reviewer'));self.reviewer=QLineEdit();tools.addWidget(self.reviewer)
        self.export_button=QPushButton('Export data');self.export_button.setEnabled(False);self.export_button.clicked.connect(self.export_data);tools.addWidget(self.export_button);layout.addLayout(tools)
        self.pages=QStackedWidget();layout.addWidget(self.pages,1);self.gallery=TrainingGallery(self);self.pages.addWidget(self.gallery)
        individual=QWidget();self.pages.addWidget(individual);layout=QVBoxLayout(individual);layout.setContentsMargins(0,0,0,0)
        split=QSplitter();left=QWidget();ll=QVBoxLayout(left);self.image_grid=QGridLayout();self.pictures=[];self.checks=[];self.captions=[]
        for i in range(4):
            cell=QWidget();cl=QVBoxLayout(cell);pic=QLabel('No image');pic.setAlignment(Qt.AlignmentFlag.AlignCenter);pic.setMinimumSize(180,140);pic.setStyleSheet('background:#0b0d0e');cl.addWidget(pic,1)
            caption=QLabel();cl.addWidget(caption);check=QCheckBox('Use for training');cl.addWidget(check)
            self.pictures.append(pic);self.captions.append(caption);self.checks.append(check);self.image_grid.addWidget(cell,i//2,i%2)
        ll.addLayout(self.image_grid,1)
        form=QHBoxLayout();self.outcome=QComboBox();self.outcome.addItem('Choose review outcome…','pending');self.outcome.addItem('Species confirmed','species');self.outcome.addItem('Unidentifiable','unidentified');self.outcome.addItem('Exclude from training','excluded');form.addWidget(self.outcome)
        self.species=QComboBox();self.species.setEditable(True);self.species.setInsertPolicy(QComboBox.InsertPolicy.NoInsert);self.species.setMinimumWidth(200);form.addWidget(self.species,1);ll.addLayout(form)
        self.note=QLineEdit();self.note.setPlaceholderText('Review note (optional)');ll.addWidget(self.note)
        self.save_button=QPushButton('Save track');self.save_button.setEnabled(False);self.save_button.clicked.connect(self.save_track);self.save_button.hide();ll.addWidget(self.save_button)
        self.message=QLabel('Choose a track, review the four images and save a species or an explicit review outcome.');self.message.setWordWrap(True);ll.addWidget(self.message)
        right=QWidget();rl=QVBoxLayout(right);rl.addWidget(QLabel('Fish tracks'));self.search=QLineEdit();self.search.setPlaceholderText('Find ID or species…');self.search.textChanged.connect(self.filter);rl.addWidget(self.search)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['ID','First seen','Frames','Species','Review']);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.table.verticalHeader().hide();self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.itemSelectionChanged.connect(self.selection_changed);rl.addWidget(self.table)
        split.addWidget(left);split.addWidget(right);split.setSizes([800,500]);layout.addWidget(split,1)
        note=QLabel('Step 2 · All available images are selected initially. Deselect images you do not want to train on. Changes save automatically. Unidentifiable tracks do not enter species training.');note.setWordWrap(True);layout.addWidget(note)
        self.outcome.currentIndexChanged.connect(self.outcome_changed)
        self.autosave_timer=QTimer(self);self.autosave_timer.setSingleShot(True);self.autosave_timer.setInterval(250);self.autosave_timer.timeout.connect(self.autosave);self.autosave_timer.timeout.connect(self.gallery.commit_ready)
        for check in self.checks:check.toggled.connect(self.autosave)
        self.outcome.currentIndexChanged.connect(self.autosave)
        self.species.currentIndexChanged.connect(self.autosave)
        self.note.textChanged.connect(lambda:self.autosave_timer.start() if not self.loading else None)
        self.reviewer.textChanged.connect(lambda:self.autosave_timer.start() if not self.loading else None)
        self.tabs.currentChanged.connect(self.change_tab)
        buttons=QHBoxLayout();previous=QPushButton('Previous fish');following=QPushButton('Next fish')
        previous.clicked.connect(lambda:self.move_track(-1));following.clicked.connect(lambda:self.move_track(1));buttons.addWidget(previous);buttons.addWidget(following);ll.addLayout(buttons)

    def remember(self):
        if self.current is not None and not self.loading and self.store:
            value=dict(status=self.outcome.currentData(),species=self.species.currentText() if self.outcome.currentData()=='species' else 'Choose species…',note=self.note.text(),checks=[c.isChecked() for c in self.checks])
            label=self.store.label(self.current);samples=self.store.samples[self.current]
            baseline=dict(status=label.get('status','pending'),species=self.store.catalog.get(label.get('species_id'),{}).get('scientific_name','Choose species…'),note=label.get('note',''),checks=[(i<len(samples) and (samples[i]['sha256'] in label.get('approved',[]) if label else True)) for i in range(4)])
            if value==baseline:self.drafts.pop(self.current,None)
            else:self.drafts[self.current]=value
            try:atomic_json(self.store.out/'training_drafts.json',dict(dataset_sha256=self.store.fingerprint,reviewer=self.reviewer.text(),drafts=self.drafts))
            except OSError as exc:self.message.setText('Draft could not be saved: '+str(exc));self.export_button.setEnabled(False)

    def load(self, out, tracks):
        self.remember();self.current=None;self.drafts={};self.tracks=tracks;self.store=None
        self.table.blockSignals(True);self.table.setRowCount(0)
        try:self.store=TrainingStore(out,tracks)
        except (OSError,ValueError,KeyError) as exc:
            self.summary.setText('Training unavailable: '+str(exc));self.table.blockSignals(False);self.export_button.setEnabled(False);self.save_button.setEnabled(False);return
        draft_path=self.store.out/'training_drafts.json'
        if draft_path.exists():
            try:
                saved=json.loads(draft_path.read_text())
                if saved['dataset_sha256']==self.store.fingerprint:
                    self.drafts={int(k):v for k,v in saved['drafts'].items()};self.reviewer.setText(saved.get('reviewer',''))
            except (OSError,ValueError,KeyError):pass
        self.species.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.species.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.species.clear();self.species.addItem('Choose species…',None)
        for key,value in sorted(self.store.catalog.items(),key=lambda pair:pair[1]['scientific_name']):self.species.addItem(value['scientific_name'],key)
        self.table.setRowCount(len(tracks));self.refresh_rows();self.table.blockSignals(False)
        self.gallery.load(self.store)
        if tracks:self.table.selectRow(0)

    def change_tab(self,index):
        self.remember();self.pages.setCurrentIndex(index)
        if self.store:self.gallery.refresh()

    def move_track(self,delta):
        row=self.table.currentRow()+delta
        if 0<=row<len(self.tracks):self.table.selectRow(row)

    def reload_current(self):
        self.current=None
        self.selection_changed()

    def autosave(self,*_):
        if self.loading or not self.store or self.current is None:return
        self.remember()
        status=self.outcome.currentData()
        if status in ('species','unidentified','excluded') and self.reviewer.text().strip():
            if status=='species' and self.species.findText(self.species.currentText(),Qt.MatchFlag.MatchExactly)<=0:return
            label=self.store.label(self.current)
            approved=sorted(s['sha256'] for s,c in zip(self.store.samples[self.current],self.checks) if c.isChecked())
            species=self.species.currentData() if status=='species' else None
            if label and label.get('status')==status and label.get('species_id')==species and label.get('approved')==approved and label.get('note','')==self.note.text() and label.get('reviewer')==self.reviewer.text().strip():return
            self.save_track(silent=True)

    def refresh_rows(self):
        for n,track in enumerate(self.tracks):
            ident=int(track['track_id']);label=self.store.label(ident);species=self.store.catalog.get(label.get('species_id'),{}).get('scientific_name','—')
            for col,value in enumerate([f'{ident:04d}',f"{float(track['first_s']):.2f} s",track['detections'],species,('✓ '+label.get('status','pending')) if label else 'pending']):self.table.setItem(n,col,QTableWidgetItem(str(value)))
        complete=sum(bool(self.store.label(i)) for i in self.store.tracks)
        self.summary.setText(f'{complete} / {len(self.tracks)} tracks reviewed · labels saved in this video’s result folder')
        self.export_button.setEnabled(self.store.complete and not self.drafts and not self.gallery.pending);self.filter(self.search.text())

    def filter(self,text):
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row,not any(text.lower() in (self.table.item(row,col).text().lower() if self.table.item(row,col) else '') for col in range(5)))

    def selection_changed(self):
        row=self.table.currentRow()
        if not self.store or row<0 or row>=len(self.tracks):return
        self.remember();ident=int(self.tracks[row]['track_id']);self.current=ident;self.loading=True
        label=self.store.label(ident);samples=self.store.samples[ident]
        for i in range(4):
            if i<len(samples):
                sample=samples[i];pix=QPixmap(str(self.store.out/sample['path']));self.pictures[i].setPixmap(pix.scaled(340,220,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));self.captions[i].setText(f"{sample['width']} × {sample['height']} px · view {i+1}");self.checks[i].setEnabled(True);self.checks[i].setChecked(sample['sha256'] in label.get('approved',[]) if label else True)
            else:self.pictures[i].clear();self.pictures[i].setText('No additional image');self.captions[i].clear();self.checks[i].setChecked(False);self.checks[i].setEnabled(False)
        self.outcome.setCurrentIndex(max(0,self.outcome.findData(label.get('status','pending'))));self.species.setCurrentIndex(max(0,self.species.findData(label.get('species_id'))));self.note.setText(label.get('note',''))
        if not self.reviewer.text() and label:self.reviewer.setText(label['reviewer'])
        draft=self.drafts.get(ident)
        if draft:
            self.outcome.setCurrentIndex(max(0,self.outcome.findData(draft['status'])));self.species.setCurrentText(draft['species']);self.note.setText(draft['note'])
            for check,value in zip(self.checks,draft['checks']):check.setChecked(value)
        self.loading=False;self.save_button.setEnabled(True);self.outcome_changed();self.message.setText('Choose useful images. Changes save automatically once a species and reviewer are set.');self.selected.emit(row)

    def outcome_changed(self):self.species.setEnabled(self.outcome.currentData()=='species')

    def select_row(self,row):
        if self.table.currentRow()!=row:self.table.selectRow(row)

    def save_track(self,silent=False):
        if not self.store or self.current is None:return
        species_id=self.species.currentData()
        # Editable text must correspond exactly to an existing catalogue entry.
        if self.outcome.currentData()=='species':
            match=self.species.findText(self.species.currentText(),Qt.MatchFlag.MatchExactly)
            species_id=self.species.itemData(match) if match>=0 else None
        approved=[sample['sha256'] for sample,check in zip(self.store.samples[self.current],self.checks) if check.isChecked()]
        try:self.store.save(self.current,self.outcome.currentData(),species_id,self.reviewer.text(),self.note.text(),approved)
        except (OSError,ValueError) as exc:
            self.message.setText('Not saved: '+str(exc))
            if not silent:QMessageBox.warning(self,'Track not saved',str(exc))
            return
        self.drafts.pop(self.current,None);self.remember();self.refresh_rows();self.labels_changed.emit();self.gallery.refresh();self.message.setText(f'Fish {self.current:04d} saved. You can switch to Viewer or continue labelling.')

    def export_data(self):
        self.remember()
        if self.drafts or self.gallery.pending:
            QMessageBox.information(self,'Save edits first','Save each edited track before exporting.');return
        try:path=self.store.export()
        except (OSError,ValueError,KeyError) as exc:QMessageBox.warning(self,'Export unavailable',str(exc));return
        self.message.setText('Export saved: '+str(path));QMessageBox.information(self,'Training data exported','Saved images, samples.csv, tracks.csv and manifest.json to:\n'+str(path))
