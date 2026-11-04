"""Portable project folders: immutable run files stay byte-identical across moves."""
import hashlib
import json
import shutil
import uuid
from pathlib import Path, PurePosixPath

REQUIRED = ('run.json','summary.json','tracks.csv','detections.csv','fishcount_tracked.mp4')


def sha256(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):result.update(block)
    return result.hexdigest()


def member(root, relative):
    path=PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or '\\' in relative or not path.parts:
        raise ValueError('Unsafe project path')
    candidate=Path(root).joinpath(*path.parts)
    if not candidate.resolve().is_relative_to(Path(root).resolve()):raise ValueError('Project path escapes its folder')
    return candidate


def source_video(results):
    results=Path(results)
    manifest=results.parent/'project.json'
    if manifest.exists():
        data=json.loads(manifest.read_text())
        source=member(results.parent,data['source_video'])
        if source.is_file():return source
    source=Path(json.loads((results/'run.json').read_text())['source'])
    return source if source.is_file() else None


def result_folder(path):
    path=Path(path)
    if (path/'project.json').exists():
        data=json.loads((path/'project.json').read_text())
        return member(path,data['results'])
    return path


def validate_results(results):
    for name in REQUIRED:
        if not (results/name).is_file():raise ValueError('Missing result file: '+name)
    json.loads((results/'run.json').read_text());json.loads((results/'summary.json').read_text())


def write_manifest(folder, video_relative, results_relative='results'):
    folder=Path(folder)
    manifest=dict(format='openfish-project',schema_version=1,project_id=uuid.uuid4().hex,
        source_video=video_relative,results=results_relative,
        files={p.relative_to(folder).as_posix():sha256(p) for p in sorted(folder.rglob('*')) if p.is_file() and p!=folder/'project.json' and p.name!='.DS_Store' and not p.name.startswith('._')})
    (folder/'project.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')


def export_project(results, destination, original=None):
    results=result_folder(results).resolve();destination=Path(destination).resolve()
    validate_results(results)
    if destination.exists():raise ValueError('Choose a new project folder; existing folders are never overwritten')
    if destination.is_relative_to(results) or destination.is_relative_to(results.parent) and (results.parent/'project.json').exists():
        raise ValueError('Export outside the current project folder')
    video=Path(original).resolve() if original else source_video(results)
    if video is None or not video.is_file():raise ValueError('Locate the original source video to make a self-contained project')
    stage=destination.with_name('.'+destination.name+'.'+uuid.uuid4().hex+'.building')
    try:
        stage.mkdir(parents=True)
        output=stage/'results';output.mkdir()
        # Copy review/training state and all crop folders, omitting redundant silent rendering.
        for item in results.rglob('*'):
            relative=item.relative_to(results)
            if item.is_symlink():raise ValueError('Project exports cannot contain symbolic links: '+str(relative))
            if any(part.endswith('.building') for part in relative.parts):continue
            if not item.is_file() or item.name in ('annotated_silent.mp4','.DS_Store') or item.name.startswith('._'):continue
            target=output/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(item,target)
        if not (output/'training_catalog.json').exists():
            catalog=json.loads((Path(__file__).parent/'catalogs/caribbean_training.json').read_text())
            catalog.update(json.loads((Path(__file__).parent/'catalogs/caribbean_reef_v5.json').read_text()))
            (output/'training_catalog.json').write_text(json.dumps(catalog,indent=2,sort_keys=True)+'\n')
        suffix=video.suffix.lower() or '.mp4';target_video=stage/'video'/('original'+suffix);target_video.parent.mkdir();shutil.copy2(video,target_video)
        checksums={p.relative_to(stage).as_posix():sha256(p) for p in sorted(stage.rglob('*')) if p.is_file()}
        manifest=dict(format='openfish-project',schema_version=1,project_id=uuid.uuid4().hex,
            source_video=target_video.relative_to(stage).as_posix(),results='results',files=checksums)
        (stage/'project.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        stage.rename(destination)
    except Exception:
        if stage.exists():shutil.rmtree(stage)
        raise
    return destination


def import_project(folder, library):
    folder=Path(folder).resolve();library=Path(library).resolve()
    data=json.loads((folder/'project.json').read_text())
    if data.get('format')!='openfish-project' or data.get('schema_version')!=1:raise ValueError('Unsupported project format')
    results=member(folder,data['results']);video=member(folder,data['source_video'])
    validate_results(results)
    if not video.is_file():raise ValueError('Original video is missing')
    # Validate every file before copying anything into the library.
    files={p.relative_to(folder).as_posix():p for p in folder.rglob('*') if p.is_file() and p.name!='.DS_Store' and not p.name.startswith('._')}
    if any(p.is_symlink() for p in folder.rglob('*')):raise ValueError('Project contains symbolic links')
    expected=data['files']
    if set(files)-{'project.json'}!=set(expected):raise ValueError('Project files changed; export a fresh project package')
    for relative,fingerprint in expected.items():
        if sha256(member(folder,relative))!=fingerprint:raise ValueError('Project file failed verification: '+relative)
    library.mkdir(parents=True,exist_ok=True)
    destination=library/(folder.name+'-'+uuid.uuid4().hex[:8]);stage=library/('.'+destination.name+'.building')
    try:
        shutil.copytree(folder,stage,ignore=shutil.ignore_patterns('.DS_Store','._*'))
        # Detect source edits during copying as well as transfer damage.
        for relative,fingerprint in expected.items():
            if sha256(member(stage,relative))!=fingerprint:raise ValueError('Project changed while importing')
        stage.rename(destination)
    except Exception:
        if stage.exists():shutil.rmtree(stage)
        raise
    return destination
