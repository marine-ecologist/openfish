"""Read the published V5 workbook into an attributed manual-label catalogue.
Read-only extraction; no source workbook modifications.
"""
import hashlib,json,re,sys
from pathlib import Path
import openpyxl
source=Path(sys.argv[1]);destination=Path(sys.argv[2])
book=openpyxl.load_workbook(source,data_only=True,read_only=True)
rows=list(book.active.values);catalog={};family=None;excluded=[]
for row in rows[1:]:
    name=str(row[0] or '').strip()
    if name.isupper() and name.endswith('IDAE'):family=name.title()
    if str(row[2]).lower()!='yes':continue
    name=re.sub(r'\s+\((?:species.*|sp)\)$','',name)
    if not re.match(r'^[A-Z][a-z]+ [a-z-]+(?: [a-z-]+)?$',name):
        excluded.append(name);continue
    key=name.lower().replace(' ','_')
    catalog[key]=dict(scientific_name=name,family=family,authority=str(row[1] or ''),
        deep_reef=str(row[8]).lower()=='yes',source='Robertson & Tornabene 2023 V5',source_row=rows.index(row)+1)
destination.write_text(json.dumps(catalog,indent=2,sort_keys=True)+'\n')
metadata=dict(title='Reef-associated Bony Fishes of the Greater Caribbean: A Checklist (VERSION 5)',
    authors=['D. Ross Robertson','Luke Tornabene'],doi='10.5281/zenodo.10225031',url='https://zenodo.org/records/10225031',
    workbook_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),named_reef_taxa=len(catalog),
    shallow_flagged=sum(not v['deep_reef'] for v in catalog.values()),excluded_unresolved_labels=excluded,
    scope='Native reef-associated bony fishes; not all regional fishes. Introduced species and sharks/rays require supplements.',
    depth_note='Source Deep flag uses approximately 40 m, not an exact 50 m occurrence filter. No species removed solely on this flag.')
destination.with_name('caribbean_reef_v5_source.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps(metadata,indent=2))
