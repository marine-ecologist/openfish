"""OpenReef-styled correction preview and tracking controls."""
import copy,json,uuid,html
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QProcess,QProcessEnvironment,QSize
from PySide6.QtGui import QPixmap,QPainter,QColor
from PySide6.QtWidgets import (QFrame,QWidget,QLabel,QVBoxLayout,QHBoxLayout,QFormLayout,QDoubleSpinBox,QSpinBox,QCheckBox,QPushButton,QComboBox,QSlider)
from fish_settings import DEFAULTS,normalize_settings,color_key

def number(low,high,value,step=.05,decimals=2):
    w=QDoubleSpinBox(); w.setRange(low,high);w.setDecimals(decimals);w.setSingleStep(step);w.setValue(value);w.setMinimumWidth(100);w.setMaximumWidth(150);return w

def help_field(form,title,widget,tip):
    label=QLabel(title+' ⓘ');label.setToolTip(tip);widget.setToolTip(tip);label.setAccessibleDescription(tip);widget.setAccessibleDescription(tip);form.addRow(label,widget);return label

def readable_tooltips(panel):
    for w in panel.findChildren(QWidget):
        tip=w.toolTip()
        if tip and not tip.startswith('<qt>'):w.setToolTip('<qt><table width="390"><tr><td>'+html.escape(tip)+'</td></tr></table></qt>')
        if tip:w.setToolTipDuration(20000)

class StillPreview(QWidget):
    def __init__(self):
        super().__init__();self.image=QPixmap();self.setMinimumWidth(200);self.setFixedHeight(450)
    def sizeHint(self):return QSize(800,450)
    def set_image(self,path):self.image=QPixmap(str(path));self.fit_height();self.update()
    def fit_height(self):
        aspect=self.image.height()/self.image.width() if not self.image.isNull() else 9/16
        target=max(120,round(self.width()*aspect))
        if self.height()!=target:self.setFixedHeight(target)
    def resizeEvent(self,event):self.fit_height();super().resizeEvent(event)
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#0b0d0e'))
        if self.image.isNull():p.setPen(QColor('#a8a8ad'));p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,'Choose a video to preview')
        else:p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform);p.drawPixmap(self.rect(),self.image)

class ColorPanel(QFrame):
    def __init__(self,root):
        super().__init__(); self.root=root;self.source=None;self.revision=0;self.running_revision=-1;self.confirmed=None;self.valid_preview=None;self.preview_path=None;self.again=False;self.restoring=True;self.restored_source=None;self.saved_time=0;self.last_valid_color=copy.deepcopy(DEFAULTS['color']);self.preferences_path=root/'.runtime/video_preferences.json'
        self.setObjectName('workflowGroup');self.setProperty('level','3')
        outer=QVBoxLayout(self);outer.setContentsMargins(20,18,20,18);outer.setSpacing(12)
        title=QLabel('2   Color correction · confirm with stills');title.setStyleSheet('font-size:17px;font-weight:650');outer.addWidget(title)
        self.enabled=QCheckBox('Apply correction to detection and playback');self.enabled.setToolTip('Use the corrected frames to find fish and to render the result video. Source video and original-color fish crops are retained.');outer.addWidget(self.enabled)
        self.controls=QWidget();self.controls.setObjectName('collapsibleContent');forms=QHBoxLayout(self.controls);left=QFormLayout();right=QFormLayout();forms.addLayout(left);forms.addSpacing(24);forms.addLayout(right);self.fields={}
        specs=[('red_gain','Red balance ×',.5,2.5,.05,2),('blue_gain','Blue balance ×',.5,2.5,.05,2),('black','Black threshold',0,254,1,0),('white','White threshold',1,255,1,0),('gamma','Shadow brightness',.5,2,.05,2),('local_contrast','Local contrast',0,4,.1,1),('saturation','Color saturation',.5,1.8,.05,2),('sharpness','Sharpening',0,1.5,.1,1)]
        tips={'black':'Sets the source intensity mapped to black (0–255). Raise it for deeper shadows and stronger contrast; too high can hide dark fish. Lower it to retain shadow detail. Must stay below the white threshold.','white':'Sets the source intensity mapped to white (0–255). Lower it to brighten the image and expand contrast; too low clips bright fish and sand. Raise it to preserve highlights.','gamma':'1 is neutral. Raise it to brighten shadows and reveal dark fish; too much can wash out contrast. Lower it to darken midtones.','local_contrast':'0 is off. Raise it to separate faint fish edges from nearby background. It can also exaggerate coral, noise and caustics. Compare several stills.','sharpness':'0 is off. Raise gently to emphasize edges. Too much creates halos and false detail; it cannot restore detail lost to blur.','red_gain':'1 is neutral. Raise it to add red and counter a blue/green underwater cast. Too much produces a red tint or clipped highlights. Values are fixed across the video.','blue_gain':'1 is neutral. Lower it to reduce a blue cast; raise it for a cooler image. Too much correction distorts natural fish colors. Values are fixed across the video.','saturation':'1 is neutral. Raise it to strengthen color differences; lower it to reduce color noise and casts. Strong saturation can exaggerate misleading markings.'}
        for i,(key,label,lo,hi,step,dp) in enumerate(specs):
            w=number(lo,hi,DEFAULTS['color'][key],step,dp);help_field(left if i<4 else right,label,w,tips[key]);self.fields[key]=w;w.valueChanged.connect(self.changed)
        outer.addWidget(self.controls)
        time_row=QHBoxLayout();time_row.addWidget(QLabel('Still at'));self.time=number(0,86400,0,.5,2);self.time.setSuffix(' s');self.time.setToolTip('Choose a timestamp to compare the same source frame before and after correction. Check dark fish, bright sand and shaded coral.');time_row.addWidget(self.time)
        for label,delta in [('−1 s',-1),('+1 s',1)]:
            b=QPushButton(label);b.setToolTip('Move the comparison still one second through the footage.');b.clicked.connect(lambda checked=False,d=delta:self.time.setValue(self.time.value()+d));time_row.addWidget(b)
        time_row.addStretch();outer.addLayout(time_row);self.timeline=QSlider(Qt.Orientation.Horizontal);self.timeline.setToolTip('Choose a comparison still anywhere in the video.');self.timeline.setRange(0,1000);self.timeline.setEnabled(False);outer.addWidget(self.timeline)
        self.frame_label=QLabel('Preview a few points in the swim before confirming.');self.frame_label.setObjectName('pageSubtitle');self.frame_label.setWordWrap(True);outer.addWidget(self.frame_label);self.images=[]
        for name in ['Original','Corrected']:
            caption=QLabel(name);caption.setStyleSheet('font-size:17px;font-weight:650');outer.addWidget(caption);pic=StillPreview();pic.setToolTip(name+' still at the selected timestamp. Scroll to compare the full-width views.');outer.addWidget(pic);self.images.append(pic)
        buttons=QHBoxLayout();preset=QPushButton('Shallow reef starting point');preset.clicked.connect(self.preset);buttons.addWidget(preset);reset=QPushButton('Reset correction');reset.clicked.connect(lambda:self.set_values(DEFAULTS['color']));buttons.addWidget(reset)
        self.confirm=QPushButton('Use these settings');self.confirm.setObjectName('primaryButton');self.confirm.clicked.connect(self.confirm_values);self.confirm.setEnabled(False);buttons.addWidget(self.confirm);outer.addLayout(buttons)
        self.state=QLabel('Correction off. Original footage will be processed.');self.state.setWordWrap(True);self.state.setObjectName('pageSubtitle');outer.addWidget(self.state)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(300);self.timer.timeout.connect(self.request_preview)
        self.worker=QProcess(self);self.worker.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels);self.worker.finished.connect(self.preview_done);self.worker.errorOccurred.connect(self.preview_error)
        self.enabled.toggled.connect(self.changed);self.time.valueChanged.connect(self.changed);self.timeline.sliderReleased.connect(self.timeline_seek);self.controls.setEnabled(False)
        self.save_timer=QTimer(self);self.save_timer.setSingleShot(True);self.save_timer.setInterval(200);self.save_timer.timeout.connect(self.save_preferences)
        try:
            saved=json.loads(self.preferences_path.read_text());self.last_valid_color=normalize_settings({'color':saved['color']})['color'];self.set_values(self.last_valid_color);self.restored_source=Path(saved['source']) if saved.get('source') else None;self.saved_time=max(0,min(86400,float(saved.get('time_s',0))))
        except (OSError,ValueError,KeyError,TypeError):pass
        self.restoring=False
        readable_tooltips(self)
    def save_preferences(self):
        try:self.last_valid_color=normalize_settings({'color':self.values()})['color']
        except ValueError:pass
        try:
            self.preferences_path.parent.mkdir(parents=True,exist_ok=True);tmp=self.preferences_path.with_suffix('.tmp');tmp.write_text(json.dumps(dict(color=self.last_valid_color,source=str(self.source or self.restored_source or ''),time_s=self.time.value()),indent=2));tmp.replace(self.preferences_path)
        except OSError as e:self.state.setText('Could not save Video preferences: '+str(e))
    def values(self):
        return dict(enabled=self.enabled.isChecked(),**{k:w.value() for k,w in self.fields.items()})
    def set_values(self,values):
        values=normalize_settings({'color':values})['color']
        for k,w in self.fields.items():w.blockSignals(True);w.setValue(values[k]);w.blockSignals(False)
        self.enabled.blockSignals(True);self.enabled.setChecked(values['enabled']);self.enabled.blockSignals(False);self.changed()
    def preset(self):
        c=copy.deepcopy(DEFAULTS['color']);c.update(enabled=True,red_gain=1.15,blue_gain=.95,gamma=1.05,local_contrast=1.5,saturation=1.05,sharpness=.2);self.set_values(c)
    def set_source(self,path):
        path=Path(path);at=self.time.value() if self.source==path else self.saved_time if self.restored_source==path else 0
        self.source=path;self.time.blockSignals(True);self.time.setMaximum(86400);self.time.setValue(at);self.time.blockSignals(False);self.changed()
    def changed(self,*_):
        self.revision+=1;self.confirmed=None;self.valid_preview=None;self.confirm.setEnabled(False);self.controls.setEnabled(self.enabled.isChecked())
        self.state.setText('Preview updating… Confirm the stills before running correction.' if self.enabled.isChecked() else 'Correction off. Original footage will be processed.')
        if self.source:self.timer.start()
        if not self.restoring:self.save_timer.start()
    def timeline_seek(self):
        self.time.setValue(self.timeline.value()/1000*self.time.maximum())
    def request_preview(self):
        if not self.source:return
        if self.worker.state()!=QProcess.ProcessState.NotRunning:self.again=True;return
        try:s=normalize_settings({'color':self.values()})
        except ValueError as e:self.state.setText(str(e));return
        self.running_revision=self.revision;self.again=False;self.preview_path=self.root/'.runtime/previews'/uuid.uuid4().hex;self.preview_path.mkdir(parents=True)
        config=self.preview_path/'settings.json';config.write_text(json.dumps(s));self.request_key=(str(self.source),color_key(s['color']))
        env=QProcessEnvironment.systemEnvironment();env.remove('PYTHONPATH');self.worker.setProcessEnvironment(env)
        self.worker.start(str(self.root/'.venv/bin/python'),[str(self.root/'preview_frame.py'),'--source',str(self.source),'--settings',str(config),'--time',str(self.time.value()),'--output',str(self.preview_path)])
    def preview_done(self,code,status):
        error=bytes(self.worker.readAllStandardOutput()).decode(errors='replace')
        if self.running_revision==self.revision:
            if code==0:
                meta=json.loads((self.preview_path/'preview.json').read_text())
                for label,name in zip(self.images,['original','corrected']):
                    label.set_image(self.preview_path/f'{name}.png')
                self.time.blockSignals(True);self.time.setMaximum(max(0,meta['duration_s']-.001));self.time.setValue(meta['time_s']);self.time.blockSignals(False)
                self.timeline.setEnabled(True);self.timeline.setValue(round(meta['time_s']/meta['duration_s']*1000))
                self.frame_label.setText(f'Frame {meta["frame"]:,} · {meta["time_s"]:.2f} s / {meta["duration_s"]:.2f} s. Correction uses fixed values throughout the video.')
                self.valid_preview=self.request_key;self.confirm.setEnabled(self.enabled.isChecked());self.state.setText('Review the corrected still, then choose “Use these settings”.' if self.enabled.isChecked() else 'Correction off. Original footage will be processed.')
                self.save_timer.start()
            else:self.state.setText('Still preview failed: '+error.strip().splitlines()[-1] if error.strip() else 'Still preview failed.')
        if self.again or self.running_revision!=self.revision:self.timer.start(0)
    def preview_error(self,error):
        if error==QProcess.ProcessError.FailedToStart:self.state.setText('Cannot start the still-preview runtime.');self.confirm.setEnabled(False)
    def confirm_values(self):
        key=(str(self.source),color_key(self.values()))
        if self.valid_preview==key:self.confirmed=key;self.state.setText('Confirmed. These correction values will be used for detection and final playback.');self.confirm.setEnabled(False)
    def is_confirmed(self):
        return not self.enabled.isChecked() or self.confirmed==(str(self.source),color_key(self.values()))
    def shutdown(self):
        self.timer.stop();self.save_timer.stop();self.save_preferences()
        if self.worker.state()!=QProcess.ProcessState.NotRunning:self.worker.kill();self.worker.waitForFinished(1500)

class TrackingPanel(QWidget):
    def __init__(self):
        super().__init__();self.setObjectName('collapsibleContent');l=QVBoxLayout(self);l.setContentsMargins(0,0,0,0);self.fields={};forms=QHBoxLayout();left=QFormLayout();right=QFormLayout()
        left.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint);right.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        model_form=QFormLayout();self.detector=QComboBox();self.detector.addItem('YOLO · fish detector','yolo');self.detector.addItem('RF-DETR · fish detector (Small)','rfdetr')
        help_field(model_form,'Detector',self.detector,'YOLO and RF-DETR are two different fish-finding models. Both return fish boxes, which BoT-SORT links between frames. Try both on the same footage. Scores differ, so suitable thresholds may differ too. Neither model assigns species.');l.addLayout(model_form)
        self.detector_note=QLabel();self.detector_note.setWordWrap(True);self.detector_note.setObjectName('pageSubtitle');l.addWidget(self.detector_note)
        specs=[('confidence','Detector threshold',.01,1,.01,'Minimum model score sent to the tracker. Lower it to admit faint or camouflaged fish; too low adds coral and noise. Raise it for cleaner boxes, but more fish may be missed. A score is not a measured probability of correctness.'),('track_low_thresh','Recovery threshold',.01,1,.01,'Minimum weak-detection score allowed to recover an existing ID. Lower it to bridge faint sightings; too low can follow background. Raise it for stricter recovery, with more ID breaks. Keep the detector threshold at or below this value.'),('track_high_thresh','Strong-match threshold',.01,1,.01,'Score needed for the first matching stage. Lower it to match more weak detections directly; raise it for stricter primary matches. Detections between recovery and this threshold use the weaker recovery stage.'),('new_track_thresh','New-ID threshold',.01,1,.01,'Score required to create a new ID from an unmatched detection. Raise it to reduce spurious new IDs and background tracks; faint new fish may be missed. Lower it to start tracks more readily, at the cost of more false IDs.'),('gap_seconds','Missing-track memory (s)',.1,10,.1,'How long an unmatched track stays eligible to return with its old ID. Increase it to bridge occlusion and camouflage gaps. Too long may attach the old ID to a different fish. It does not guarantee recovery; the returning fish must still match.'),('match_thresh','Match tolerance',.01,1,.05,'Controls how lenient position and motion matching may be. Higher is more permissive: fewer breaks, but more possible ID swaps between nearby fish. Lower is stricter: fewer mistaken associations, but more fragmented tracks.'),('iou','Box overlap threshold',.01,1,.05,'YOLO only: controls suppression of overlapping detection boxes. Higher values retain more boxes, helping overlapping fish but risking duplicate boxes. Lower values suppress duplicates more strongly, but may remove one of two nearby fish. RF-DETR does not use this control.'),('appearance_thresh','Appearance similarity',.01,1,.05,'Used only with appearance matching enabled. Raise it to require more similar visual features, reducing mistaken links but increasing missed recoveries. Lower it to tolerate changed views or lighting, with greater risk of confusing similar fish.'),('proximity_thresh','Appearance spatial overlap',.01,1,.05,'Used only with appearance matching enabled. Minimum overlap between the predicted and observed fish boxes before visual features are considered. Lower it to permit larger position changes; raise it to reduce distant or mistaken matches.')]
        for i,(key,label,lo,hi,step,tip) in enumerate(specs):
            w=number(lo,hi,DEFAULTS['tracking'][key],step);self.fields[key]=w;help_field(left if i<5 else right,label,w,tip)
        self.resolution=QComboBox();self.resolution.addItems(['640 · faster','1024 · standard','1536 · more detail']);self.resolution.setCurrentIndex(1);help_field(right,'Detector resolution (px)',self.resolution,'Size of the image supplied to the detector. Higher values give small fish more pixels and may improve detection, but use more time and memory. Lower values run faster but may miss distant fish. This does not increase detail in the original footage.')
        self.reid=QCheckBox('Appearance matching (experimental) ⓘ');self.reid.setToolTip('YOLO only: adds visual features to position and motion when matching fish. It may recover IDs through changing views, but similar-looking fish can still be confused. RF-DETR currently uses motion and box matching. SAM 2 is planned as a later stage.');right.addRow(self.reid);self.reid.toggled.connect(self.reid_changed);self.reid_changed(False)
        forms.addLayout(left);forms.addSpacing(24);forms.addLayout(right);l.addLayout(forms)
        note=QLabel('Threshold order: detector ≤ recovery ≤ strong match ≤ new ID. More tolerance can reduce ID breaks but can also merge different fish.');note.setWordWrap(True);note.setObjectName('pageSubtitle');l.addWidget(note)
        row=QHBoxLayout();b=QPushButton('Continuity starting point');b.clicked.connect(lambda:self.set_values(DEFAULTS['tracking']));row.addWidget(b);b=QPushButton('Trial comparison thresholds');b.clicked.connect(self.trial);row.addWidget(b);row.addStretch();l.addLayout(row)
        self.detector.currentIndexChanged.connect(self.detector_changed);self.detector_changed()
        readable_tooltips(self)
    def detector_values(self):return {'name':self.detector.currentData()}
    def set_detector(self,name):self.detector.setCurrentIndex(0 if name=='yolo' else 1)
    def detector_changed(self,*_):
        yolo=self.detector.currentData()=='yolo';self.reid.setEnabled(yolo);self.fields['iou'].setEnabled(yolo)
        if not yolo:self.reid.setChecked(False)
        self.reid_changed(self.reid.isChecked())
        self.detector_note.setText('YOLO: fish boxes with optional native appearance matching.' if yolo else 'RF-DETR Small: alternative fish detector, using the same motion-based tracker. Appearance matching and YOLO box suppression are unavailable for this model.')
    def reid_changed(self,value):
        for key in ['appearance_thresh','proximity_thresh']:self.fields[key].setEnabled(value)
    def values(self):return dict(**{k:w.value() for k,w in self.fields.items()},imgsz=[640,1024,1536][self.resolution.currentIndex()],with_reid=self.reid.isChecked())
    def set_values(self,values):
        t=normalize_settings({'tracking':values})['tracking']
        for k,w in self.fields.items():w.setValue(t[k])
        self.resolution.setCurrentIndex([640,1024,1536].index(t['imgsz']));self.reid.setChecked(t['with_reid']);self.reid_changed(t['with_reid'])
    def trial(self):
        t=copy.deepcopy(DEFAULTS['tracking']);t.update(confidence=.25,track_low_thresh=.25,track_high_thresh=.25,new_track_thresh=.25,gap_seconds=1);self.set_values(t)
