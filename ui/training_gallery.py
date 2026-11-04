"""Embedded appearance-group species review, sharing the native TrainingStore."""
import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap,QStandardItemModel,QStandardItem
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QComboBox,QPushButton,QScrollArea,QFrame,QMessageBox
from training import atomic_json
from species_labels import title


class TrainingGallery(QWidget):
    def __init__(self, panel):
        super().__init__();self.panel=panel;self.store=None;self.pending={};self.controls={};self.ticks={};self.group_ticks=[];self.groups=[];self.group_controls=[];self.changing=False
        layout=QVBoxLayout(self)
        note=QLabel('Step 1 · Assign species to appearance groups, check each fish. Valid choices save automatically after you enter a reviewer name. Similar appearance does not establish species identity. Use Unidentifiable for individual exceptions.');note.setWordWrap(True);layout.addWidget(note)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);layout.addWidget(self.scroll)

    def choice(self):
        box=QComboBox();box.setModel(self.choice_model);box.setEditable(True);box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        box.completer().setFilterMode(Qt.MatchFlag.MatchContains);box.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        return box

    def load(self, store):
        self.store=store;self.pending={};self.controls={};self.ticks={};self.group_ticks=[];self.groups=[];self.group_controls=[]
        if not store:return
        self.choice_model=QStandardItemModel(self)
        entries=[('Unreviewed · species unassigned',None)]+[(title(v),k) for k,v in sorted(store.catalog.items(),key=lambda p:(p[1]['scientific_name'],0 if p[0].endswith('__TP') else 1))]+[('Unidentifiable','unidentified')]
        for text,key in entries:
            item=QStandardItem(text);item.setData(key,Qt.ItemDataRole.UserRole);self.choice_model.appendRow(item)
        self.path=store.out/'training_gallery_drafts.json'
        if self.path.exists():
            saved=json.loads(self.path.read_text())
            if saved['dataset_sha256']==store.fingerprint:self.pending={int(k):v for k,v in saved['pending'].items()}
        ids=set(store.tracks);seen=set();groups=[]
        sim=store.out/'similarity.json'
        if sim.exists():
            for group in json.loads(sim.read_text()).get('groups',[]):
                members=[int(i) for i in group if int(i) in ids and int(i) not in seen]
                if members:groups.append(members);seen.update(members)
        groups.extend([[i] for i in sorted(ids-seen)])
        content=QWidget();outer=QVBoxLayout(content)
        for number,members in enumerate(groups,1):
            section=QFrame();section.setObjectName('workflowGroup');sl=QVBoxLayout(section);header=QHBoxLayout();header.addWidget(QLabel(f'Appearance group {number} · {len(members)} fish'))
            group_box=self.choice();header.addWidget(group_box,1);tick=QLabel();header.addWidget(tick);sl.addLayout(header)
            group_box.currentIndexChanged.connect(lambda _,m=members,b=group_box:self.assign(m,b.currentData()))
            self.group_ticks.append((members,tick));self.group_controls.append((members,group_box))
            grid=QGridLayout()
            for n,ident in enumerate(members):
                card=QWidget();cl=QVBoxLayout(card);heading=QHBoxLayout();heading.addWidget(QLabel(f'Fish {ident:04d}'));saved=QLabel();heading.addWidget(saved);cl.addLayout(heading);self.ticks[ident]=saved
                image=QLabel();image.setAlignment(Qt.AlignmentFlag.AlignCenter);pix=QPixmap(str(store.out/'crops'/f'fish_{ident:04d}.jpg'));image.setPixmap(pix.scaled(220,140,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));cl.addWidget(image)
                choice=self.choice();choice.setMinimumWidth(160);choice.setMaximumWidth(280);cl.addWidget(choice);self.controls[ident]=choice
                choice.currentIndexChanged.connect(lambda _,i=ident,m=members,b=choice:self.individual_choice(i,m,b.currentData()))
                grid.addWidget(card,n//3,n%3)
            sl.addLayout(grid);outer.addWidget(section);self.groups.append(members)
        outer.addStretch();self.scroll.setWidget(content);self.refresh()

    def value(self, ident):
        label=self.store.label(ident)
        return label.get('species_id') if label.get('status')=='species' else 'unidentified' if label.get('status') in ('unidentified','excluded') else None

    def persist(self):
        atomic_json(self.path,dict(dataset_sha256=self.store.fingerprint,pending=self.pending))

    def assign(self, members, value):
        if self.changing:return
        # Human-selected propagation is a staged edit, never an automatic taxonomy inference.
        for ident in members:self.pending[ident]=value
        self.persist();self.refresh();self.panel.refresh_rows();self.commit_ready()

    def individual_choice(self, ident, members, value):
        if self.changing:return
        if value=='unidentified' or value is None:
            self.pending[ident]=value;self.persist();self.refresh();self.panel.refresh_rows();self.commit_ready()
        else:self.assign(members,value)

    def commit_ready(self):
        if self.changing or not self.panel.reviewer.text().strip():return
        members=[i for i,v in self.pending.items() if v is not None]
        if members:self.save(members)

    def refresh(self):
        if not self.store:return
        self.changing=True
        for ident,control in self.controls.items():
            value=self.pending.get(ident,self.value(ident));control.setCurrentIndex(max(0,control.findData(value)))
            self.ticks[ident].setText('✓ Saved' if self.store.label(ident) and ident not in self.pending else 'Unsaved' if ident in self.pending else '')
        for members,box in self.group_controls:
            values={self.pending.get(i,self.value(i)) for i in members};value=next(iter(values)) if len(values)==1 else None
            box.setCurrentIndex(max(0,box.findData(value)))
        for members,tick in self.group_ticks:tick.setText('✓ All saved' if all(self.store.label(i) and i not in self.pending for i in members) else '')
        self.changing=False

    def save(self, members):
        try:
            self.panel.remember()
            rows=[]
            for ident in members:
                value=self.pending.get(ident,self.value(ident))
                if value is None:raise ValueError('Assign a species or Unidentifiable to every fish in the group')
                old=self.store.label(ident);draft=self.panel.drafts.get(ident,{})
                approved=old.get('approved',[s['sha256'] for s in self.store.samples[ident]])
                if 'checks' in draft:approved=[s['sha256'] for s,checked in zip(self.store.samples[ident],draft['checks']) if checked]
                rows.append(dict(track_id=ident,status='unidentified' if value=='unidentified' else 'species',species_id=None if value=='unidentified' else value,
                    reviewer=self.panel.reviewer.text().strip(),note=draft.get('note',old.get('note','')),approved=approved))
            self.store.save_group(rows)
            for ident in members:self.pending.pop(ident,None);self.panel.drafts.pop(ident,None)
            self.persist();self.panel.refresh_rows();self.panel.reload_current();self.panel.labels_changed.emit();self.refresh()
        except (OSError,ValueError) as exc:
            self.panel.message.setText('Not saved: '+str(exc));self.panel.export_button.setEnabled(False)

    def open_individual(self, ident):
        row=next(n for n,t in enumerate(self.panel.tracks) if int(t['track_id'])==ident)
        self.panel.table.selectRow(row);self.panel.tabs.setCurrentIndex(1)
