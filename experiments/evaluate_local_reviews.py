"""Report agreement against imported human reviews; unidentified is not species truth."""
import json
import sys
from pathlib import Path

out=Path(sys.argv[1])
data=json.loads((out/'species_export.json').read_text())
reviewed={r['track_id']:r for r in data['tracks'] if r['status']=='reviewed'}
resolved={k:r for k,r in reviewed.items() if r['species_id']!='unidentified'}
correct=0;rows=[]
for prediction in data['predictions']['tracks']:
    ident=prediction['track_id']
    if ident not in reviewed:continue
    candidate=prediction.get('candidate_id')
    review=reviewed[ident]
    match=candidate==review['species_id'] if ident in resolved else None
    correct+=int(match is True)
    rows.append(dict(track_id=ident,human_species=review['species_id'],model_candidate=candidate,model_assignment=prediction['species_id'],match=match))
result=dict(status='reviewed' if reviewed else 'awaiting_user_review',selected_tracks=len(data['tracks']),reviewed_tracks=len(reviewed),
    species_resolved_tracks=len(resolved),unidentified_reviews=len(reviewed)-len(resolved),
    top1_agreement=correct/len(resolved) if resolved else None,
    note='Assisted human review, not a blinded independent benchmark. Unidentified reviews are excluded from species accuracy.',tracks=rows)
(out/'validation_status.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
