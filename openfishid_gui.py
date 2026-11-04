"""OpenFishID desktop workspace, styled to match OpenReef."""
import argparse,csv,json,os,re,sys,uuid
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QUrl,QProcess,QProcessEnvironment,QThread,Signal
from PySide6.QtGui import QDesktopServices,QPixmap,QColor,QImage,QPainter,QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,QStackedWidget,QFileDialog,QMessageBox,QProgressBar,QPlainTextEdit,QSlider,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QLineEdit,QCheckBox,QSplitter,QListWidget,QListWidgetItem,QScrollArea)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput,QVideoSink
from ui.theme import application_stylesheet
from ui.settings_panels import ColorPanel,TrackingPanel
from fish_settings import normalize_settings
from ui.training_panel import TrainingPanel
from project_io import export_project, import_project, result_folder, source_video

ROOT=Path(__file__).resolve().parent
class VideoCanvas(QWidget):
    def __init__(self):
        super().__init__(); self.image=QImage(); self.frames_received=0
    def frame_ready(self,frame):
        image=frame.toImage()
        if not image.isNull():self.image=image; self.frames_received+=1; self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.fillRect(self.rect(),QColor('#0b0d0e'))
        if not self.image.isNull():
            size=self.image.size().scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatio)
            x=(self.width()-size.width())//2; y=(self.height()-size.height())//2
            p.drawImage(x,y,self.image.scaled(size,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))

class ProjectTransfer(QThread):
    succeeded=Signal(str)
    failed=Signal(str)
    def __init__(self,operation,parent):super().__init__(parent);self.operation=operation
    def run(self):
        try:self.succeeded.emit(str(self.operation()))
        except Exception as exc:self.failed.emit(str(exc))

class Window(QMainWindow):
    def __init__(self,result=None):
        super().__init__(); self.setWindowTitle('OpenFishID 0.7.0 · Reef fish video'); self.resize(1480,920); self.setMinimumSize(1100,720)
        self.source=None; self.result=None; self.tracks=[]; self.frames={}; self.run={}; self.pending=''; self.busy=False; self.project_busy=False; self.phase=''; self.user_scrubbing=False
        self.process=QProcess(self); self.process.setWorkingDirectory(str(ROOT)); self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output); self.process.finished.connect(self.finished); self.process.errorOccurred.connect(self.process_error)
        self.stack=QStackedWidget(); self.stack.setObjectName('workspaceStack'); self.nav=[]
        shell=QWidget(); sl=QHBoxLayout(shell); sl.setContentsMargins(0,0,0,0); sl.setSpacing(0)
        sidebar=QFrame(); sidebar.setObjectName('appSidebar'); sidebar.setFixedWidth(224)
        sb=QVBoxLayout(sidebar); sb.setContentsMargins(16,18,16,16); sb.setSpacing(5)
        lights=QHBoxLayout()
        for name in ['trafficRed','trafficYellow','trafficGreen']:
            dot=QLabel(); dot.setObjectName(name); dot.setFixedSize(12,12); lights.addWidget(dot)
        lights.addStretch(); sb.addLayout(lights); sb.addSpacing(25)
        brand=QHBoxLayout(); brand.setSpacing(10); logo=QLabel(); logo.setPixmap(QIcon(str(ROOT/'ui/assets/fish.svg')).pixmap(40,40)); brand.addWidget(logo)
        names=QVBoxLayout(); names.setSpacing(1); title=QLabel('OpenFishID'); title.setObjectName('appTitle'); names.addWidget(title)
        caption=QLabel('REEF FISH VIDEO'); caption.setObjectName('appCaption'); names.addWidget(caption); brand.addLayout(names); sb.addLayout(brand); sb.addSpacing(25)
        section=QLabel('WORKSPACE'); section.setObjectName('sidebarSection'); sb.addWidget(section)
        for i,name in enumerate(['Projects','Video','Process','Viewer','Training']):
            b=QPushButton(name); b.setObjectName('sidebarNav'); b.setCheckable(True); b.clicked.connect(lambda checked=False,n=i:self.navigate(n)); self.nav.append(b); sb.addWidget(b)
            b.setToolTip({'Projects':'Reopen completed fish surveys and their exported results.','Video':'Select footage, adjust color correction, and inspect full-width original/corrected stills. Video preferences are remembered between sessions.','Process':'Choose YOLO or RF-DETR and tune detection and tracking. Hover each setting label for its purpose and the effect of raising or lowering it.','Training':'Review up to four images per track, save species labels and export reviewed training data.','Viewer':'Play annotated results, step through frames, and select a fish ID to inspect its crop and first sighting.'}[name]);b.setToolTip('<qt>'+b.toolTip()+'</qt>');b.setToolTipDuration(20000)
        sb.addStretch(); hint=QLabel('Local processing\nVideos stay on this Mac'); hint.setWordWrap(True); hint.setStyleSheet('color:#77797d;font-size:12px;'); sb.addWidget(hint)
        version=QLabel('OpenFishID v0.7.0'); version.setObjectName('sidebarVersion'); sb.addWidget(version)
        sl.addWidget(sidebar); sl.addWidget(self.stack,1); self.setCentralWidget(shell)
        self.build_projects(); self.build_video(); self.build_process(); self.build_viewer(); self.build_training()
        self.setStyleSheet(application_stylesheet(True)+'''QTableWidget,QListWidget{background:#1b1d1f;border:1px solid #303337;border-radius:8px;gridline-color:#303337;color:#f2f2f7;} QListWidget::item{padding:16px;} QHeaderView::section{background:#222528;color:#a8a8ad;border:0;padding:8px;} QTableWidget::item:selected,QListWidget::item:selected{background:#303337;color:white;} QVideoWidget{background:#0b0d0e;} QPushButton#primaryButton:disabled{background:#303337;border-color:#393d42;color:#77797d;}''')
        self.navigate(0); self.refresh_projects(); self.statusBar().showMessage('Ready — select a video or open a completed result')
        self.refresh_timer=QTimer(self); self.refresh_timer.timeout.connect(self.refresh_projects); self.refresh_timer.start(5000)
        if result: self.load_result(Path(result)); self.navigate(3)
        elif self.color_panel.restored_source and self.color_panel.restored_source.is_file():self.set_source(self.color_panel.restored_source)

    def page(self,title,subtitle):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(32,28,32,28); l.setSpacing(14)
        t=QLabel(title); t.setObjectName('pageTitle'); l.addWidget(t)
        s=QLabel(subtitle); s.setObjectName('pageSubtitle'); s.setWordWrap(True); l.addWidget(s)
        if title in ('Video','Process'):
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setObjectName('workspacePageScroll');scroll.setWidget(w);self.stack.addWidget(scroll)
        else:self.stack.addWidget(w)
        return l
    def card(self,title,level=1):
        f=QFrame(); f.setObjectName('workflowGroup'); f.setProperty('level',str(level)); l=QVBoxLayout(f); l.setContentsMargins(20,18,20,18); l.setSpacing(12)
        t=QLabel(title); t.setStyleSheet('font-size:17px;font-weight:650'); l.addWidget(t); return f,l
    def button(self,text,callback,primary=False):
        b=QPushButton(text); b.clicked.connect(callback)
        if primary:b.setObjectName('primaryButton')
        return b
    def navigate(self,n):
        if hasattr(self,'training'):self.training.remember()
        if n==4 and hasattr(self,'player'):self.player.pause()
        self.stack.setCurrentIndex(n)
        for i,b in enumerate(self.nav): b.setChecked(i==n)
    def build_projects(self):
        l=self.page('Projects','Reopen a completed survey, or begin with a new reef video.')
        row=QHBoxLayout(); row.addWidget(self.button('New video',self.choose_video,True)); row.addWidget(self.button('Open result folder…',self.open_result)); row.addWidget(self.button('Import project…',self.import_project_dialog)); row.addWidget(self.button('Export project…',self.export_project_dialog)); row.addStretch(); l.addLayout(row)
        self.project_list=QListWidget(); self.project_list.itemDoubleClicked.connect(lambda item:self.load_result(Path(item.data(Qt.ItemDataRole.UserRole))))
        l.addWidget(self.project_list,1)
        l.addWidget(QLabel('Double-click a completed project to review its tracks and video.'))
    def refresh_projects(self):
        selected=self.project_list.currentItem(); selected=selected.data(Qt.ItemDataRole.UserRole) if selected else None
        dirs=[ROOT/'outputs/full']+sorted((ROOT/'outputs/runs').glob('*'),reverse=True)+[p/'results' for p in sorted((ROOT/'outputs/projects').glob('*'),reverse=True) if (p/'project.json').exists()]
        self.project_list.clear()
        for d in dirs:
            if not d.is_dir():continue
            try:
                meta=json.loads((d/'summary.json').read_text())
                text=f'{Path(meta["source"]).name}   ·   {meta["track_count"]} provisional tracks   ·   Ready'
            except (OSError,ValueError,KeyError):
                if d==ROOT/'outputs/full':text='fishcount.MP4   ·   Trial processing / preparing playback'
                else:
                    try:meta=json.loads((d/'job.json').read_text()); text=f'{Path(meta["source"]).name}   ·   {meta["state"]}'
                    except (OSError,ValueError,KeyError):continue
            item=QListWidgetItem(text); item.setData(Qt.ItemDataRole.UserRole,str(d)); self.project_list.addItem(item)
            if str(d)==selected:self.project_list.setCurrentItem(item)
    def build_video(self):
        l=self.page('Video','Select the footage to detect fish and follow their sightings through time.')
        c,cl=self.card('1   Select source footage',1)
        self.source_name=QLabel('No video selected'); self.source_name.setStyleSheet('font-size:20px;font-weight:600'); cl.addWidget(self.source_name)
        self.source_path=QLabel('MP4 · MOV · M4V · AVI · MKV'); self.source_path.setWordWrap(True); self.source_path.setObjectName('pageSubtitle'); cl.addWidget(self.source_path)
        cl.addWidget(self.button('Choose video…',self.choose_video,True)); l.addWidget(c)
        self.color_panel=ColorPanel(ROOT);l.addWidget(self.color_panel)
        c,cl=self.card('3   Review the result',3); info=QLabel('The result includes a playable video, provisional track IDs and original-resolution fish crops. Correction can improve visibility, but tracking still needs review.'); info.setWordWrap(True); cl.addWidget(info)
        info=QLabel('IDs follow continuous sightings. Occlusion and re-entry can create duplicate IDs. Small fish may be missed; species are not assigned.'); info.setObjectName('pageSubtitle'); info.setWordWrap(True); cl.addWidget(info)
        cl.addWidget(self.button('Continue to Process',lambda:self.navigate(2))); l.addWidget(c); l.addStretch()
    def choose_video(self):
        if self.busy:return
        path,_=QFileDialog.getOpenFileName(self,'Select reef video',str(Path.home()),'Video files (*.mp4 *.MP4 *.mov *.MOV *.m4v *.avi *.mkv);;All files (*)')
        if path:self.set_source(Path(path)); self.navigate(1)
    def set_source(self,path):
        self.source=Path(path).resolve(); self.source_name.setText(path.name); self.source_path.setText(str(self.source)); self.process_source.setText(path.name); self.run_button.setEnabled(True);self.color_panel.set_source(self.source)
    def build_process(self):
        l=self.page('Process','Detect fish, assign track IDs, then prepare the playback video.')
        c,cl=self.card('1   Fish detection & tracking',1); self.process_source=QLabel('Choose a video to begin'); cl.addWidget(self.process_source)
        detail=QLabel('Fish detection model + BoT-SORT tracking\nOriginal frame rate · local processing'); detail.setObjectName('pageSubtitle'); cl.addWidget(detail)
        self.tracking_panel=TrackingPanel();cl.addWidget(self.tracking_panel)
        row=QHBoxLayout(); self.run_button=self.button('Run video',self.start,True); self.run_button.setEnabled(False); row.addWidget(self.run_button)
        self.cancel_button=self.button('Cancel',lambda:self.process.terminate()); self.cancel_button.setEnabled(False); row.addWidget(self.cancel_button); row.addStretch(); cl.addLayout(row); l.addWidget(c)
        c,cl=self.card('2   Prepare playback',3); self.phase_label=QLabel('Ready'); cl.addWidget(self.phase_label); self.progress=QProgressBar(); self.progress.setRange(0,1000); self.progress.setValue(0); cl.addWidget(self.progress)
        self.open_viewer=self.button('Open Viewer',lambda:self.navigate(3),True); self.open_viewer.setEnabled(False); cl.addWidget(self.open_viewer); l.addWidget(c)
        self.terminal=QPlainTextEdit(); self.terminal.setObjectName('processingTerminal'); self.terminal.setReadOnly(True); self.terminal.setMaximumBlockCount(1500); l.addWidget(self.terminal,1)
    def start(self):
        if not self.source or self.busy:return
        if not self.source.is_file():QMessageBox.warning(self,'Video unavailable','The selected video is no longer available.'); return
        try:settings=normalize_settings(dict(detector=self.tracking_panel.detector_values(),color=self.color_panel.values(),tracking=self.tracking_panel.values()))
        except ValueError as e:QMessageBox.warning(self,'Check processing settings',str(e));return
        if not self.color_panel.is_confirmed():
            QMessageBox.information(self,'Confirm correction stills','Review the original and corrected stills in Video, then choose “Use these settings” before running.');self.navigate(1);return
        self.output=ROOT/'outputs/projects'/f'{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}'/'results'; self.output.mkdir(parents=True)
        settings_path=self.output/'settings.json';settings_path.write_text(json.dumps(settings,indent=2));self.color_panel.shutdown();self.color_panel.setEnabled(False);self.tracking_panel.setEnabled(False)
        self.busy=True; self.phase='detecting'; self.pending=''; self.progress.setValue(0); self.terminal.clear(); self.run_button.setEnabled(False); self.cancel_button.setEnabled(True); self.open_viewer.setEnabled(False)
        env=QProcessEnvironment.systemEnvironment(); env.insert('PATH','/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'); env.insert('PYTHONUNBUFFERED','1'); env.insert('PYTORCH_ENABLE_MPS_FALLBACK','1'); env.insert('YOLO_CONFIG_DIR',str(ROOT/'.runtime')); env.insert('MPLCONFIGDIR',str(ROOT/'.runtime/matplotlib')); self.process.setProcessEnvironment(env)
        env.insert('HF_HOME',str(ROOT/'.runtime/huggingface'));env.insert('HF_HUB_OFFLINE','1');self.process.setProcessEnvironment(env)
        self.log_file=(self.output/'processing.log').open('w')
        self.process.start(str(ROOT/'.venv/bin/python'),['-u',str(ROOT/'run_job.py'),'--source',str(self.source),'--output',str(self.output),'--settings',str(settings_path)])
        self.phase_label.setText('Detecting fish & assigning IDs…'); self.statusBar().showMessage('Processing '+self.source.name)
    def read_output(self):
        text=bytes(self.process.readAllStandardOutput()).decode('utf-8',errors='replace')
        if hasattr(self,'log_file') and not self.log_file.closed:self.log_file.write(text); self.log_file.flush()
        self.pending+=text; lines=self.pending.split('\n'); self.pending=lines.pop()
        for line in lines:
            self.terminal.appendPlainText(line)
            if line.startswith('PHASE preparing'):self.phase_label.setText('Preparing self-contained project · copying source video…')
            if line.startswith('PHASE encoding'):self.phase='encoding'; self.phase_label.setText('Rendering readable IDs & preparing playback…'); self.progress.setValue(850)
            m=re.search(r'(\d+)/(\d+) frames; (\d+) tracks; ([\d.]+) fps',line)
            if m:
                done,total,count,speed=m.groups(); self.progress.setValue(int(int(done)/int(total)*850)); self.phase_label.setText(f'Detecting & tracking · {int(done):,} / {int(total):,} frames · {count} provisional tracks')
            if line.startswith('Encoded '):
                try:
                    n=int(line.split()[1]); total=json.loads((self.output/'run.json').read_text())['total_frames']; self.progress.setValue(850+int(n/total*140))
                except (OSError,ValueError,KeyError):pass
    def finished(self,code,status):
        self.read_output(); self.busy=False; self.run_button.setEnabled(self.source is not None); self.cancel_button.setEnabled(False);self.color_panel.setEnabled(True);self.tracking_panel.setEnabled(True)
        if hasattr(self,'log_file') and not self.log_file.closed:self.log_file.close()
        if code==0 and (self.output/'summary.json').exists():
            self.progress.setValue(1000); self.phase_label.setText('Complete · playback ready'); self.load_result(self.output); self.open_viewer.setEnabled(True); self.navigate(3)
        else:
            try:state=json.loads((self.output/'job.json').read_text())['state']
            except (OSError,ValueError,KeyError):state='failed'
            self.phase_label.setText('Cancelled · partial output retained' if state=='cancelled' else 'Processing failed · see the log below')
            self.statusBar().showMessage(self.phase_label.text())
        self.refresh_projects()
    def process_error(self,error):
        if error==QProcess.ProcessError.FailedToStart:
            self.busy=False; self.run_button.setEnabled(True); self.cancel_button.setEnabled(False);self.color_panel.setEnabled(True);self.tracking_panel.setEnabled(True);self.phase_label.setText('Could not start the processing runtime.'); self.terminal.appendPlainText(self.process.errorString())
            if hasattr(self,'log_file') and not self.log_file.closed:self.log_file.close()
    def build_viewer(self):
        l=self.page('Viewer','Play the processed footage, step through frames, or jump to a fish track.')
        self.result_label=QLabel('Open a completed result to review'); self.result_label.setObjectName('datasetSummary'); l.addWidget(self.result_label)
        split=QSplitter(); left=QWidget(); vl=QVBoxLayout(left); vl.setContentsMargins(0,0,0,0)
        self.video=VideoCanvas(); self.video.setMinimumSize(480,270); vl.addWidget(self.video,1)
        self.player=QMediaPlayer(self); self.audio=QAudioOutput(self); self.audio.setVolume(.35); self.player.setAudioOutput(self.audio); self.sink=QVideoSink(self); self.sink.videoFrameChanged.connect(self.video.frame_ready); self.player.setVideoSink(self.sink)
        self.player.positionChanged.connect(self.position_changed); self.player.durationChanged.connect(lambda d:self.slider.setRange(0,d)); self.player.errorOccurred.connect(lambda error,msg:self.statusBar().showMessage('Playback: '+msg))
        self.slider=QSlider(Qt.Orientation.Horizontal); self.slider.sliderPressed.connect(lambda:setattr(self,'user_scrubbing',True)); self.slider.sliderReleased.connect(self.seek_slider); vl.addWidget(self.slider)
        row=QHBoxLayout(); row.addWidget(self.button('◀ Frame',lambda:self.step(-1))); self.play_button=self.button('Play',self.play_pause,True); row.addWidget(self.play_button); row.addWidget(self.button('Frame ▶',lambda:self.step(1)))
        self.clock=QLabel('00:00 / 00:00'); row.addWidget(self.clock); row.addStretch(); self.speed=QComboBox(); self.speed.addItems(['0.5×','1×','2×']); self.speed.setCurrentIndex(1); self.speed.currentIndexChanged.connect(lambda i:self.player.setPlaybackRate([.5,1,2][i])); row.addWidget(self.speed); vl.addLayout(row)
        self.player.playbackStateChanged.connect(lambda s:self.play_button.setText('Pause' if s==QMediaPlayer.PlaybackState.PlayingState else 'Play'))
        self.frame_label=QLabel('Frame —'); self.frame_label.setObjectName('pageSubtitle'); vl.addWidget(self.frame_label)
        right=QWidget(); rl=QVBoxLayout(right); rl.setContentsMargins(12,0,0,0); title=QLabel('Fish tracks'); title.setStyleSheet('font-size:17px;font-weight:650'); rl.addWidget(title)
        self.search=QLineEdit(); self.search.setPlaceholderText('Find ID…'); self.search.textChanged.connect(self.filter_tracks); rl.addWidget(self.search)
        self.table=QTableWidget(0,5); self.table.setHorizontalHeaderLabels(['ID','First seen','Frames','Species','Review']); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.table.verticalHeader().hide(); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.itemSelectionChanged.connect(self.track_selected); rl.addWidget(self.table,1)
        self.crop=QLabel('Select a track'); self.crop.setAlignment(Qt.AlignmentFlag.AlignCenter); self.crop.setFixedHeight(160); self.crop.setObjectName('mediaPreview'); rl.addWidget(self.crop)
        self.track_detail=QLabel('Provisional sighting IDs\nSpecies unassigned'); self.track_detail.setWordWrap(True); self.track_detail.setObjectName('pageSubtitle'); rl.addWidget(self.track_detail)
        split.addWidget(left); split.addWidget(right); split.setSizes([900,300]); l.addWidget(split,1)
        row=QHBoxLayout(); row.addWidget(self.button('Open result folder',self.reveal_result)); row.addWidget(self.button('Export project…',self.export_project_dialog)); row.addWidget(self.button('Track CSV',lambda:self.open_artifact('tracks.csv'))); row.addWidget(self.button('Fish gallery',lambda:self.open_artifact('fish_ID_gallery.html'))); row.addStretch(); l.addLayout(row)
        note=QLabel('Review pass · fish can receive new IDs after occlusion or re-entry. Small fish may be missed. Track totals are not unique-fish counts.'); note.setWordWrap(True); note.setObjectName('pageSubtitle'); l.addWidget(note)
    def build_training(self):
        layout=self.page('Training','Review fish tracks, confirm species and build a training dataset from approved original-color images.')
        self.training=TrainingPanel();layout.addWidget(self.training)
        self.training.selected.connect(lambda row:self.table.selectRow(row) if self.table.currentRow()!=row else None)
        self.training.labels_changed.connect(self.refresh_species_columns)

    def refresh_species_columns(self):
        if not self.training.store:return
        for row,track in enumerate(self.tracks):
            label=self.training.store.label(int(track['track_id']))
            name=self.training.store.catalog.get(label.get('species_id'),{}).get('scientific_name','—')
            self.table.setItem(row,3,QTableWidgetItem(name));self.table.setItem(row,4,QTableWidgetItem(label.get('status','pending')))
        row=self.table.currentRow()
        if 0<=row<len(self.tracks):
            track=self.tracks[row];label=self.training.store.label(int(track['track_id']))
            species=self.training.store.catalog.get(label.get('species_id'),{}).get('scientific_name','Species unassigned')
            self.track_detail.setText(f"Fish {int(track['track_id']):04d} · {track['first_s']}–{track['last_s']} s\n{species} · {label.get('status','pending')}")

    def transfer_project(self,operation,importing):
        self.project_busy=True;self.centralWidget().setEnabled(False);self.statusBar().showMessage('Copying and verifying project files… Large videos may take several minutes.')
        self.project_transfer=ProjectTransfer(operation,self)
        def done(path):
            self.project_busy=False;self.centralWidget().setEnabled(True);self.refresh_projects()
            if importing:self.load_result(result_folder(Path(path)))
            else:QMessageBox.information(self,'Project exported','Share this entire folder with your colleague:\n'+path)
            self.statusBar().showMessage('Project imported' if importing else 'Project exported')
        def failed(message):
            self.project_busy=False;self.centralWidget().setEnabled(True);QMessageBox.warning(self,'Project transfer failed',message)
        self.project_transfer.succeeded.connect(done);self.project_transfer.failed.connect(failed);self.project_transfer.start()

    def export_project_dialog(self):
        if self.busy or self.project_busy:return
        if not self.result:QMessageBox.information(self,'Open a project','Open a completed result first.');return
        self.training.remember()
        original=source_video(self.result)
        if original is None:
            path,_=QFileDialog.getOpenFileName(self,'Locate this project’s original video','','Videos (*.mp4 *.MP4 *.mov *.MOV);;All files (*)')
            if not path:return
            original=Path(path)
        parent=QFileDialog.getExistingDirectory(self,'Choose where to save the project folder',str(Path.home()))
        if not parent:return
        destination=Path(parent)/('openfish-project-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
        result=self.result
        self.transfer_project(lambda:export_project(result,destination,original),False)

    def import_project_dialog(self):
        if self.busy or self.project_busy:return
        folder=QFileDialog.getExistingDirectory(self,'Choose an exported openFish project folder',str(Path.home()))
        if folder:self.transfer_project(lambda:import_project(folder,ROOT/'outputs/projects'),True)

    def open_result(self):
        path=QFileDialog.getExistingDirectory(self,'Open completed OpenFishID result',str(ROOT/'outputs'))
        if path:self.load_result(Path(path))
    def load_result(self,path):
        try:
            path=result_folder(path)
            meta=json.loads((path/'summary.json').read_text()); tracks=list(csv.DictReader((path/'tracks.csv').open()))
            if not (path/'fishcount_tracked.mp4').is_file():raise ValueError('The playback video is not available.')
            original=source_video(path)
        except (OSError,ValueError,KeyError,TypeError) as e:QMessageBox.information(self,'Result is not ready','Choose a completed result folder containing summary.json and the playback video.\n\n'+str(e)); return
        self.result=path; self.run=meta; self.tracks=tracks; self.frames={}
        if not self.busy and original is not None:
            if 'settings' in meta:
                self.tracking_panel.set_detector(meta['settings'].get('detector',{}).get('name','yolo'));self.tracking_panel.set_values(meta['settings']['tracking'])
            self.set_source(original)
        for r in csv.DictReader((path/'detections.csv').open()):
            if r['track_id']:self.frames.setdefault(int(r['frame']),set()).add(int(r['track_id']))
        self.table.setRowCount(0)
        for n,t in enumerate(tracks):
            self.table.insertRow(n)
            for col,value in enumerate([f'{int(t["track_id"]):04d}',self.time_text(float(t['first_s'])*1000),t['detections']]):self.table.setItem(n,col,QTableWidgetItem(value))
        self.training.load(path,tracks);self.refresh_species_columns()
        self.result_label.setText(f'{Path(meta["source"]).name} · {meta["processed_frames"]:,} frames · {len(tracks)} provisional tracks')
        self.video.image=QImage(str(path/'review_00000.jpg')); self.video.frames_received=0; self.video.update()
        self.player.setSource(QUrl.fromLocalFile(str(path/'fishcount_tracked.mp4'))); self.open_viewer.setEnabled(True); self.navigate(3); self.statusBar().showMessage('Playback ready — '+Path(meta['source']).name)
        QTimer.singleShot(250,lambda:self.position_changed(self.player.position()))
    def track_selected(self):
        n=self.table.currentRow()
        if n<0 or n>=len(self.tracks):return
        self.training.select_row(n)
        t=self.tracks[n]; self.player.pause(); self.player.setPosition(round(float(t['first_s'])*1000))
        pic=QPixmap(str(self.result/'crops'/f'fish_{int(t["track_id"]):04d}.jpg')); self.crop.setPixmap(pic.scaled(280,150,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        label=self.training.store.label(int(t['track_id'])) if self.training.store else {}
        species=self.training.store.catalog.get(label.get('species_id'),{}).get('scientific_name','Species unassigned') if self.training.store else 'Species unassigned'
        review_line=species+' · '+label.get('status','pending')
        self.track_detail.setText(f'Fish {int(t["track_id"]):04d} · {t["first_s"]}–{t["last_s"]} s\n{t["detections"]} detected frames · peak score {t["best_confidence"]}\n{review_line}')
    def filter_tracks(self,text):
        for n,t in enumerate(self.tracks):self.table.setRowHidden(n,text.strip() not in f'{int(t["track_id"]):04d}')
    @staticmethod
    def time_text(ms):
        s=int(ms/1000); return f'{s//60:02d}:{s%60:02d}'
    def position_changed(self,pos):
        if not self.user_scrubbing:self.slider.setValue(pos)
        self.clock.setText(f'{self.time_text(pos)} / {self.time_text(self.player.duration())}')
        if self.run:
            n=round(pos/1000*self.run['source_fps']); self.frame_label.setText(f'Frame {min(n,self.run["total_frames"]-1):,} · {len(self.frames.get(n,set()))} tracked fish in this frame')
    def seek_slider(self):self.user_scrubbing=False; self.player.setPosition(self.slider.value())
    def play_pause(self):
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:self.player.pause()
        else:self.player.play()
    def step(self,direction):
        self.player.pause(); fps=self.run.get('source_fps',30); self.player.setPosition(max(0,round((round(self.player.position()/1000*fps)+direction)/fps*1000)))
    def reveal_result(self):
        if self.result:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.result)))
    def open_artifact(self,name):
        if self.result:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.result/name)))
    def closeEvent(self,event):
        if self.project_busy:
            QMessageBox.information(self,'Project transfer running','Keep this window open until the project copy finishes.');event.ignore();return
        if self.busy:
            QMessageBox.information(self,'Processing is running','Keep this window open until processing finishes, or cancel the run from Process.'); event.ignore()
        else:self.training.remember();self.color_panel.shutdown();self.player.stop(); event.accept()

def main():
    p=argparse.ArgumentParser(); p.add_argument('--result'); p.add_argument('--screenshot'); a=p.parse_args()
    app=QApplication(sys.argv[:1]); app.setApplicationName('OpenFishID'); app.setOrganizationName('OpenFishID'); app.setWindowIcon(QIcon(str(ROOT/'OpenFishID.app/Contents/Resources/OpenFishID.icns'))); window=Window(a.result); window.show()
    if a.screenshot:
        def capture():
            try:
                if a.result:
                    assert window.player.duration()>0,'Playback did not load'
                    assert window.video.frames_received>0,'No video frames decoded'
                    assert len(window.tracks)==window.run['track_count']
                    window.player.pause()
                    if window.tracks:window.table.selectRow(0); window.step(1)
                def finish_capture():
                    window.grab().save(a.screenshot); print('UI smoke check passed',flush=True); app.exit(0)
                QTimer.singleShot(500,finish_capture)
            except Exception as e:print('UI smoke check failed',repr(e),flush=True); app.exit(1)
        if a.result:QTimer.singleShot(300,window.player.play)
        QTimer.singleShot(4000,capture)
    sys.exit(app.exec())
if __name__=='__main__':main()
