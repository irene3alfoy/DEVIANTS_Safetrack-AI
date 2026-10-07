import asyncio
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from pathlib import Path
import shutil
import uuid
from fastapi import FastAPI,UploadFile,File,HTTPException,Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .config import DATA,ROOT,EXTENSIONS,MAX_BYTES,MAX_DURATION
from . import store,vision,pipeline
from .ingestion import metadata,download
from .temporal import TemporalEngine,answer_plan

jobs={}
analysis_lock=asyncio.Lock()

@asynccontextmanager
async def lifespan(app):
    store.init()
    yield
    for task in jobs.values():
        if not task.done(): task.cancel()
    await asyncio.gather(*jobs.values(),return_exceptions=True)

app=FastAPI(title='Video Understanding & Temporal Reasoning',lifespan=lifespan)

class URLInput(BaseModel):
    url:str=Field(min_length=8,max_length=4096)

class AnalyzeInput(BaseModel):
    sample_interval:float=Field(default=2,ge=.25,le=10)
    chunk_seconds:float=Field(default=20,ge=5,le=60)

class QuestionInput(BaseModel):
    question:str=Field(min_length=1,max_length=1000)

def get_video(video_id):
    try:return store.video(video_id)
    except KeyError:raise HTTPException(404,'Video not found.')

def public(item):
    return {k:v for k,v in item.items() if k!='path'}

def completed(video_id):
    item=get_video(video_id)
    if item['status']!='complete':raise HTTPException(409,'Analyze this video successfully before viewing results or asking questions.')
    return item

async def create_video(video_id,path,name,size,source_url=None):
    info=await asyncio.to_thread(metadata,path)
    await asyncio.to_thread(pipeline.make_preview,path,path.parent/'preview.mp4')
    item={'id':video_id,'filename':name,'size':size,'source_url':source_url,'path':str(path),'created_at':datetime.now(timezone.utc).isoformat(),'status':'uploaded','stage':'Video loaded','progress':0,'preview_ready':True,'error':None,**info}
    store.save_video(item)
    return public(item)

@app.get('/api/health')
async def health():
    return {'backend':True,'vision':await vision.health(),'max_upload_bytes':MAX_BYTES,'max_duration_seconds':MAX_DURATION}

@app.post('/api/video/upload')
@app.post('/api/upload',include_in_schema=False)
async def upload(file:UploadFile=File(...)):
    name=Path((file.filename or 'video').replace('\\','/')).name
    suffix=Path(name).suffix.lower()
    if suffix not in EXTENSIONS:raise HTTPException(400,'Supported formats: MP4, MOV, AVI, MKV, WebM.')
    video_id=uuid.uuid4().hex
    folder=DATA/video_id
    folder.mkdir()
    path=folder/('original'+suffix)
    try:
        total=0
        with path.open('wb') as output:
            while chunk:=await file.read(1024*1024):
                total+=len(chunk)
                if total>MAX_BYTES:raise ValueError('This video exceeds the configured upload size limit.')
                output.write(chunk)
        return await create_video(video_id,path,name,total)
    except Exception as exc:
        shutil.rmtree(folder,ignore_errors=True)
        raise HTTPException(400,str(exc))
    finally:await file.close()

@app.post('/api/video/url')
async def url_video(body:URLInput):
    video_id=uuid.uuid4().hex
    folder=DATA/video_id
    folder.mkdir()
    path=folder/'original.mp4'
    try:
        size=await download(body.url,path)
        return await create_video(video_id,path,'Linked video',size,body.url)
    except Exception as exc:
        shutil.rmtree(folder,ignore_errors=True)
        raise HTTPException(400,str(exc) if isinstance(exc,ValueError) else 'Could not download the video. Check the public direct-file URL.')

@app.get('/api/video/{video_id}')
@app.get('/api/videos/{video_id}',include_in_schema=False)
async def video_detail(video_id:str):return public(get_video(video_id))

@app.get('/api/video/{video_id}/status')
async def status(video_id:str):return public(get_video(video_id))

@app.post('/api/video/{video_id}/analyze')
async def analyze(video_id:str,body:AnalyzeInput):
    item=get_video(video_id)
    if item['status'] in ('processing','queued'):raise HTTPException(409,'Analysis is already running for this video.')
    # A bounded batch keeps vision requests and memory manageable.
    if body.chunk_seconds/body.sample_interval>24:raise HTTPException(400,'Use at most 24 sampled frames per segment. Increase the interval or reduce segment length.')
    model=await vision.health()
    if not model['ready']:raise HTTPException(503,model['message'])
    if get_video(video_id)['status'] in ('processing','queued'):raise HTTPException(409,'Analysis is already running for this video.')
    async def queued():
        async with analysis_lock:await pipeline.run(video_id,body.sample_interval,body.chunk_seconds)
    store.update(video_id,status='queued',stage='Waiting for analysis worker',progress=0,error=None)
    jobs[video_id]=asyncio.create_task(queued())
    return public(store.video(video_id))

@app.get('/api/video/{video_id}/media')
async def media(video_id:str):
    item=get_video(video_id)
    source=Path(item['path'])
    if item['preview_ready'] and (source.parent/'preview.mp4').exists():source=source.parent/'preview.mp4'
    # Starlette FileResponse supports HTTP Range for native video seeking.
    return FileResponse(source,media_type='video/mp4' if source.suffix=='.mp4' else 'video/webm' if source.suffix=='.webm' else 'application/octet-stream')

@app.get('/api/video/{video_id}/events')
@app.get('/api/videos/{video_id}/events',include_in_schema=False)
async def events(video_id:str):
    completed(video_id)
    return sorted(store.records('events',video_id),key=lambda e:e['start_time'])

@app.get('/api/video/{video_id}/timeline')
async def timeline(video_id:str):
    completed(video_id)
    return {'events':store.records('events',video_id),'relationships':store.records('relationships',video_id)}

@app.get('/api/video/{video_id}/entities')
async def entities(video_id:str):
    completed(video_id)
    return store.records('entities',video_id)

@app.get('/api/video/{video_id}/summary')
@app.get('/api/videos/{video_id}/summary',include_in_schema=False)
async def summary(video_id:str):
    item=completed(video_id)
    return {'summary':item.get('summary'),'limitations':item.get('limitations',[])}

@app.get('/api/video/{video_id}/questions')
async def history(video_id:str):
    get_video(video_id)
    return store.records('questions',video_id)

@app.post('/api/video/{video_id}/question')
@app.post('/api/videos/{video_id}/questions',include_in_schema=False)
async def question(video_id:str,body:QuestionInput):
    item=completed(video_id)
    events=store.records('events',video_id)
    if not events:
        plan=vision.QueryPlan(operation='search',match_ids=[])
    else:
        try:plan=await vision.plan_question(body.question,events,store.records('entities',video_id))
        except ValueError as exc:raise HTTPException(503,str(exc))
    answer=answer_plan(plan,events,item['duration'])
    return store.save_question(video_id,body.question,answer)

@app.get('/api/video/{video_id}/relationship')
async def relationship(video_id:str,event_a:str,event_b:str):
    completed(video_id)
    engine=TemporalEngine(store.records('events',video_id))
    if event_a not in engine.by_id or event_b not in engine.by_id:raise HTTPException(404,'Event not found.')
    return {'event_a':event_a,'event_b':event_b,'relationship':engine.compare_event_order(engine.by_id[event_a],engine.by_id[event_b])}

@app.delete('/api/video/{video_id}')
async def delete(video_id:str):
    item=get_video(video_id)
    if item['status'] in ('queued','processing'):raise HTTPException(409,'Wait for the current analysis to finish before removing the video.')
    with store.connection() as db:
        for table in ('events','entities','relationships','questions'):
            db.execute(f'DELETE FROM {table} WHERE video_id=?',(video_id,))
        db.execute('DELETE FROM videos WHERE id=?',(video_id,))
    shutil.rmtree(DATA/video_id,ignore_errors=True)
    return {'removed':True}

# Production: serve the built React application alongside the API.
dist=ROOT/'frontend'/'dist'
if dist.exists():
    app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
    @app.get('/{path:path}',include_in_schema=False)
    async def frontend(path:str):
        if path.startswith('api/'):raise HTTPException(404,'Endpoint not found.')
        if path=='favicon.svg':return FileResponse(dist/'favicon.svg')
        return FileResponse(dist/'index.html')
