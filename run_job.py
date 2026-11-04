"""Coordinator used by the desktop app; work stays on this computer."""
import argparse,datetime,json,os,signal,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--source',required=True); p.add_argument('--output',required=True); p.add_argument('--settings'); a=p.parse_args()
root=Path(__file__).resolve().parent; out=Path(a.output).resolve(); out.mkdir(parents=True,exist_ok=True)
child=None
def stop(*_):
    if child and child.poll() is None:
        try: os.killpg(child.pid,signal.SIGTERM)
        except ProcessLookupError: pass
    raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop)
def status(state,error=''):
    (out/'job.json').write_text(json.dumps(dict(source=str(Path(a.source).resolve()),state=state,error=error,updated=datetime.datetime.now().isoformat()),indent=2))
try:
    from fish_settings import read_settings
    settings=read_settings(a.settings); settings_path=out/'settings.json'; settings_path.write_text(json.dumps(settings,indent=2))
    for phase,command in [('detecting',['track_fish.py','--source',a.source,'--output',str(out),'--settings',str(settings_path)]),('encoding',['finalize.py','--output',str(out)])]:
        status(phase); print('PHASE',phase,flush=True)
        child=subprocess.Popen([sys.executable,*command],cwd=root,start_new_session=True)
        if child.wait(): raise RuntimeError(f'{phase.capitalize()} failed. See the processing log for details.')
    status('complete'); print('PHASE complete',flush=True)
except KeyboardInterrupt:
    status('cancelled'); print('PHASE cancelled',flush=True); sys.exit(130)
except Exception as e:
    status('failed',str(e)); print(str(e),flush=True); sys.exit(1)
