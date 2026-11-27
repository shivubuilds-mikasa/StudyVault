from pathlib import Path
import sqlite3, json, re, datetime, os, hashlib
BASE=Path(__file__).resolve().parents[1]
DB=BASE/'library.db'
SUBJECT_NAMES={'SEPM':'SEPM','IDS':'IDS','ATC':'ATC','OS':'OS','GPU':'GPU','ML':'ML','Elective_Options_Review':'Elective Options'}
LIBRARY_ROOTS=('01_Subjects','02_Examination','03_Unclassified')
LIBRARY_EXTENSIONS={'.pdf','.pptx','.ppt','.docx','.doc','.xlsx','.xls'}
EXAMS=[
 {'date':'2026-12-07','name':'GPU','code':'24CS3501','time':None,'verified':True},
 {'date':'2026-12-09','name':'SEPM','code':'24CS3502','time':None,'verified':True},
 {'date':'2026-12-11','name':'ML','code':'24CS3503','time':None,'verified':True},
 {'date':'2026-12-14','name':'OS','code':'24CS3505','time':None,'verified':True},
 {'date':'2026-12-16','name':'IDS','code':'24CS3504','time':None,'verified':True},
 {'date':'2026-12-18','name':'Elective options shown: AI for Business Analytics (24CS3508), Computer Graphics (24CS3510), Cloud Computing (24CS3511), Introduction to XR and Immersive Technologies (24CS3512)','code':None,'time':None,'verified':False},
 {'date':'2026-12-22','name':'ATC','code':'24CS3506','time':None,'verified':True}]
def conn():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def initialize():
 with conn() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS documents(path TEXT PRIMARY KEY, subject TEXT, category TEXT, name TEXT, ext TEXT, size INTEGER, modified TEXT, pages INTEGER, missing INTEGER DEFAULT 0, seen TEXT, sha256 TEXT); CREATE TABLE IF NOT EXISTS exams(id INTEGER PRIMARY KEY, date TEXT, name TEXT, code TEXT, time TEXT, verified INTEGER);''')
  cols={r[1] for r in c.execute('PRAGMA table_info(documents)')}
  if 'sha256' not in cols: c.execute('ALTER TABLE documents ADD COLUMN sha256 TEXT')
  c.execute('DELETE FROM exams')
  c.executemany('INSERT INTO exams(date,name,code,time,verified) VALUES(:date,:name,:code,:time,:verified)',[dict(x,verified=int(x['verified'])) for x in EXAMS])
def classify(rel):
 parts=Path(rel).parts
 if parts[0]=='03_Unclassified': return None,'Review'
 if parts[0]=='02_Examination': return None,'Examination'
 if parts[0]=='01_Subjects' and len(parts)>2:
  slug=parts[1]; cat=parts[2]
  catmap={'Modules':'Module','PYQs':'PYQ','Mid_Sem':'Mid-semester','Other_Materials':'Other material'}
  return SUBJECT_NAMES.get(slug,slug.replace('_',' ')),catmap.get(cat,'Other material')
 return None,'Library metadata'
def page_count(p):
 if p.suffix.lower()=='.pdf':
  try:
   import pymupdf
   return len(pymupdf.open(p))
  except Exception: return None
 return None
def scan():
 initialize();now=datetime.datetime.now().isoformat(timespec='seconds'); seen=[]
 with conn() as c:
  # Fail closed: only scan the three study-library directories. BASE also contains
  # deployment artifacts (including Render's .venv), which must never appear as files.
  c.execute("DELETE FROM documents WHERE path NOT LIKE '01_Subjects/%' AND path NOT LIKE '02_Examination/%' AND path NOT LIKE '03_Unclassified/%'")
  for root_name in LIBRARY_ROOTS:
   root=BASE/root_name
   if not root.is_dir(): continue
   for p in root.rglob('*'):
    if not p.is_file() or p.suffix.lower() not in LIBRARY_EXTENSIONS or any(part.startswith('.') for part in p.relative_to(BASE).parts): continue
    rel=p.relative_to(BASE).as_posix()
    subject,cat=classify(rel); ext=p.suffix.lower()
    st=p.stat(); seen.append(rel); digest=hashlib.sha256(p.read_bytes()).hexdigest()
    prior=next((row for row in c.execute('SELECT path FROM documents WHERE sha256=? AND path<>?',(digest,rel)) if not (BASE/row['path']).exists()),None)
    if prior: c.execute('DELETE FROM documents WHERE path=?',(prior['path'],))
    c.execute('''INSERT INTO documents(path,subject,category,name,ext,size,modified,pages,missing,seen,sha256) VALUES(?,?,?,?,?,?,?,?,0,?,?) ON CONFLICT(path) DO UPDATE SET subject=excluded.subject,category=excluded.category,name=excluded.name,ext=excluded.ext,size=excluded.size,modified=excluded.modified,pages=COALESCE(excluded.pages,documents.pages),missing=0,seen=excluded.seen,sha256=excluded.sha256''',(rel,subject,cat,p.name,ext,st.st_size,datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds'),page_count(p),now,digest))
  if seen:
   c.executemany('UPDATE documents SET missing=1 WHERE path=?',[(r,) for r in []])
   marks=','.join('?' for _ in seen)
   c.execute(f'UPDATE documents SET missing=1 WHERE path NOT IN ({marks})',seen)
  else: c.execute('UPDATE documents SET missing=1')
 return len(seen)
initialize(); scan()
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse,HTMLResponse
from fastapi.staticfiles import StaticFiles
app=FastAPI(title='StudyVault')
@app.get('/api/subjects')
def subjects():
 out=[]
 subject_root=BASE/'01_Subjects'
 if subject_root.is_dir():
  for folder in subject_root.iterdir():
   if folder.is_dir(): out.append({'name':SUBJECT_NAMES.get(folder.name,folder.name.replace('_',' ')),'counts':{}})
 by_name={item['name']:item for item in out}
 for name in SUBJECT_NAMES.values():
  if name not in by_name:
   item={'name':name,'counts':{}};out.append(item);by_name[name]=item
 with conn() as c:
  rows=c.execute("SELECT subject,category,COUNT(*) count FROM documents WHERE missing=0 AND subject IS NOT NULL GROUP BY subject,category").fetchall()
 for r in rows:
  found=by_name.get(r['subject'])
  if not found:
   found={'name':r['subject'],'counts':{}};out.append(found);by_name[r['subject']]=found
  found['counts'][r['category']]=r['count']
 return sorted(out,key=lambda x:x['name'])
@app.get('/api/documents')
def documents(subject:str|None=None,category:str|None=None):
 q='SELECT * FROM documents WHERE missing=0';args=[]
 if subject: q+=' AND subject=?';args.append(subject)
 if category: q+=' AND category=?';args.append(category)
 with conn() as c: return [dict(r) for r in c.execute(q+' ORDER BY modified DESC',args)]
@app.get('/api/exams')
def exams():
 with conn() as c:return [dict(r) for r in c.execute('SELECT * FROM exams ORDER BY date')]
@app.get('/api/search')
def search(q:str=''):
 term='%'+q.strip()+'%'
 with conn() as c:return [dict(r) for r in c.execute('SELECT * FROM documents WHERE missing=0 AND (name LIKE ? OR subject LIKE ? OR category LIKE ? OR path LIKE ?) ORDER BY name LIMIT 100',(term,term,term,term))]
@app.post('/api/library/rescan')
def rescan(): return {'files_scanned':scan(),'status':'complete'}
@app.get('/api/library/duplicates')
def duplicates():
 import hashlib
 grouped={}
 for p in (BASE/'01_Subjects').rglob('*'):
  if p.is_file():
   digest=hashlib.sha256(p.read_bytes()).hexdigest()
   grouped.setdefault(digest,[]).append(p.relative_to(BASE).as_posix())
 return [paths for paths in grouped.values() if len(paths)>1]
@app.get('/api/library/status')
def status():
 with conn() as c:
  return {'documents':c.execute('SELECT COUNT(*) FROM documents WHERE missing=0').fetchone()[0],'missing':c.execute('SELECT COUNT(*) FROM documents WHERE missing=1').fetchone()[0],'review':c.execute("SELECT COUNT(*) FROM documents WHERE category='Review'").fetchone()[0]}
@app.get('/files/{rel:path}')
def files(rel:str,download:bool=False):
 p=(BASE/rel).resolve()
 parts=Path(rel).parts
 if not p.is_relative_to(BASE.resolve()) or not parts or parts[0] not in LIBRARY_ROOTS or not p.is_file() or any(part.startswith('.') for part in parts) or p.suffix.lower() not in LIBRARY_EXTENSIONS: raise HTTPException(404)
 import mimetypes
 return FileResponse(p,filename=p.name,media_type=mimetypes.guess_type(p.name)[0],content_disposition_type='attachment' if download else 'inline')
@app.get('/preview/{rel:path}',response_class=HTMLResponse)
def preview_presentation(rel:str):
 import zipfile,xml.etree.ElementTree as ET,html
 p=(BASE/rel).resolve()
 parts=Path(rel).parts
 if not p.is_relative_to(BASE.resolve()) or not parts or parts[0] not in LIBRARY_ROOTS or not p.is_file() or any(part.startswith('.') for part in parts) or p.suffix.lower()!='.pptx': raise HTTPException(404)
 ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
 try:
  with zipfile.ZipFile(p) as archive:
   names=[n for n in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
   names.sort(key=lambda n:int(re.search(r'slide(\d+)',n).group(1)))
   slides=[]
   for num,name in enumerate(names,1):
    root=ET.fromstring(archive.read(name)); paragraphs=[]
    for para in root.findall('.//a:p',ns):
     text=''.join(node.text or '' for node in para.findall('.//a:t',ns)).strip()
     if text: paragraphs.append('<p>'+html.escape(text)+'</p>')
    body=''.join(paragraphs) or '<p class=\"blank\">No selectable text on this slide</p>'
    slides.append(f'<article class=\"slide\" id=\"slide-{num}\"><div class=\"slide-no\">SLIDE {num:02} / {len(names):02}</div><div class=\"slide-body\">{body}</div></article>')
 except (zipfile.BadZipFile,ET.ParseError): raise HTTPException(422,'Presentation could not be previewed')
 title=html.escape(p.name)
 return HTMLResponse(f'''<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><style>*{{box-sizing:border-box}}body{{margin:0;padding:22px;background:#f4efdf;color:#28261f;font:14px Segoe UI,Arial,sans-serif}}header{{position:sticky;top:0;z-index:2;margin:-22px -22px 20px;padding:12px 18px;background:#fbf9f2ee;backdrop-filter:blur(12px);border-bottom:1px solid #e2d9c2;display:flex;justify-content:space-between;align-items:center}}header strong{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.controls{{display:flex;gap:8px;align-items:center}}button{{border:1px solid #d9cda8;background:#f3e8c4;border-radius:9px;padding:7px 11px;color:#544319;cursor:pointer}}#slides{{display:grid;gap:18px;max-width:980px;margin:auto}}.slide{{aspect-ratio:16/9;min-height:310px;padding:clamp(24px,5vw,62px);background:#fffefa;border:1px solid #e5deca;border-radius:15px;box-shadow:0 12px 34px #43360d12;display:flex;flex-direction:column;justify-content:center;overflow:auto;animation:enter .45s ease both}}.slide-no{{font-size:10px;letter-spacing:1.6px;color:#ad821a;margin-bottom:20px}}.slide-body p{{font-size:clamp(16px,2vw,23px);line-height:1.38;margin:0 0 13px;font-weight:500}}.slide-body p:nth-child(n+4){{font-size:clamp(13px,1.45vw,17px);color:#696354}}.blank{{color:#8d8777}}@keyframes enter{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}@media(prefers-reduced-motion:reduce){{*,*:before,*:after{{animation-duration:.01ms!important;transition-duration:.01ms!important}}}}</style></head><body><header><strong>{title}</strong><div class=\"controls\"><button onclick=\"step(-1)\">←</button><span id=\"count\">1 / {len(names)}</span><button onclick=\"step(1)\">→</button></div></header><main id=\"slides\">{''.join(slides)}</main><script>let i=1;function step(d){{i=Math.max(1,Math.min({len(names)},i+d));document.querySelector('#slide-'+i).scrollIntoView({{behavior:'smooth',block:'center'}});document.querySelector('#count').textContent=i+' / {len(names)}'}}</script></body></html>''')
@app.get('/',response_class=HTMLResponse)
def home():return FileResponse(BASE/'05_Web_Application'/'index.html')
