"""Verify the downloaded release before rerunning or editing its files."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1]
records=json.loads((R/'manifest_sha256.json').read_text())
errors=[]
for row in records:
 p=(R/row['path']).resolve()
 if R not in p.parents or not p.is_file():errors.append('missing/invalid '+row['path']);continue
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 if h.hexdigest()!=row['sha256'] or p.stat().st_size!=row['bytes']:errors.append('modified '+row['path'])
if errors:raise SystemExit('\n'.join(errors))
print('PASS:',len(records),'files match the shipped SHA-256 manifest.')
print('File integrity does not certify Julia execution or actual MBTA operating requirements.')
