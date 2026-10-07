import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowUpRight, Upload, Link2, Film, X, Search, ChevronDown, ChevronRight, Clock3, ScanLine, MessageSquare, Play, Layers3, CircleAlert, Check, SlidersHorizontal, RotateCcw, Download } from 'lucide-react';
import './style.css';

type Video = {id:string;filename:string;size:number;duration:number;fps:number;width:number;height:number;codec:string;format:string;status:string;stage:string;progress:number;error:string|null;preview_ready:boolean;summary?:string;limitations?:string[];event_count?:number;entity_count?:number};
type Event = {id:string;type:string;description:string;start_time:number;end_time:number;duration:number;entities:string[];category:string;confidence:number;approximate:boolean;identity_uncertain:boolean;timing_uncertainty:number;evidence_times:number[]};
type Entity = {id:string;label:string;appearance:string;first_seen:number;last_seen:number;identity_confidence:number;identity_uncertain:boolean;observations:{time:number;box:number[];confidence:number}[]};
type Answer = {question:string;answer:string;timestamps:{time:number;label:string}[];confidence:number|null;related_events:string[];supported:boolean;created_at:string};
type Health = {backend:boolean;vision:{ready:boolean;model:string;message:string};max_upload_bytes:number};
const categories=['All','People','Vehicles','Objects','Alerts','Motion','Other'];
const time=(seconds:number)=>{const n=Math.max(0,Math.floor(seconds||0)),h=Math.floor(n/3600),m=Math.floor(n/60)%60,s=n%60;return `${h?`${h.toString().padStart(2,'0')}:`:''}${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;};
const size=(bytes:number)=>`${(bytes/1024/1024).toFixed(1)} MB`;
async function api<T>(path:string, options?:RequestInit):Promise<T>{
  let response:Response;
  try{response=await fetch(path,{...options,headers:{...(options?.body?{'Content-Type':'application/json'}:{}),...options?.headers}});}catch{throw new Error('The backend is unavailable. Start the application server and try again.');}
  const data=await response.json().catch(()=>({detail:'The server returned an unreadable response.'}));
  if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Please check your input and try again.');
  return data;
}
function App(){
  const [mode,setMode]=useState<'upload'|'url'|null>(null),[video,setVideo]=useState<Video|null>(null),[localSrc,setLocalSrc]=useState('');
  const [health,setHealth]=useState<Health|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[uploadProgress,setUploadProgress]=useState(0),[url,setUrl]=useState('');
  const [analyzing,setAnalyzing]=useState(false),[events,setEvents]=useState<Event[]>([]),[entities,setEntities]=useState<Entity[]>([]),[answers,setAnswers]=useState<Answer[]>([]);
  const [question,setQuestion]=useState(''),[asking,setAsking]=useState(false),[search,setSearch]=useState(''),[category,setCategory]=useState('All'),[selected,setSelected]=useState<string|null>(null),[expanded,setExpanded]=useState<string|null>(null);
  const [advanced,setAdvanced]=useState(false),[interval,setInterval]=useState(2),[chunk,setChunk]=useState(20),[showSummary,setShowSummary]=useState(false),[showTracks,setShowTracks]=useState(false),[current,setCurrent]=useState(0),[dragging,setDragging]=useState(false),[resultView,setResultView]=useState(false);
  const player=useRef<HTMLVideoElement>(null),fileInput=useRef<HTMLInputElement>(null),uploadRequest=useRef<XMLHttpRequest|null>(null),initiated=useRef(false);
  const src=video?.preview_ready?`/api/video/${video.id}/media`:localSrc|| (video?`/api/video/${video.id}/media`:'');
  const filtered=events.filter(e=>(category==='All'||e.category===category)&&`${e.description} ${e.entities.join(' ')} ${e.type}`.toLowerCase().includes(search.toLowerCase()));
  const processing=analyzing||video?.status==='queued'||video?.status==='processing';

  async function loadResults(item:Video){
    const [ev,en,history]=await Promise.all([api<Event[]>(`/api/video/${item.id}/events`),api<Entity[]>(`/api/video/${item.id}/entities`),api<Answer[]>(`/api/video/${item.id}/questions`)]);
    setEvents(ev);setEntities(en);setAnswers(history);setVideo(item);setResultView(true);
  }
  useEffect(()=>{
    api<Health>('/api/health').then(setHealth).catch(e=>setError(e.message));
    const restore=async()=>{
      const id=window.location.pathname.match(/^\/analysis\/([a-f0-9]{32})$/)?.[1];
      if(!id){setResultView(false);return;}
      try{const item=await api<Video>(`/api/video/${id}`);setVideo(item);if(item.status==='complete')await loadResults(item);}catch(e){setError((e as Error).message);}
    };
    void restore();window.addEventListener('popstate',restore);return()=>{window.removeEventListener('popstate',restore);uploadRequest.current?.abort();};
  },[]);
  useEffect(()=>()=>{if(localSrc)URL.revokeObjectURL(localSrc);},[localSrc]);
  useEffect(()=>{
    if(!video||!processing)return;
    let cancelled=false,timer:ReturnType<typeof setTimeout>;
    const poll=async()=>{
      try{
        const item=await api<Video>(`/api/video/${video.id}/status`);
        if(cancelled)return;
        setVideo(item);
        if(item.status==='complete'){
          setAnalyzing(false);await loadResults(item);
          if(initiated.current){window.history.pushState({},'',`/analysis/${item.id}`);initiated.current=false;}
          return;
        }
        if(item.status==='failed'){setAnalyzing(false);setError(item.error||'Analysis failed. Please retry.');return;}
        timer=setTimeout(poll,1500);
      }catch(e){if(!cancelled){setAnalyzing(false);setError((e as Error).message);}}
    };
    timer=setTimeout(poll,800);return()=>{cancelled=true;clearTimeout(timer);};
  },[video?.id,processing]);

  function upload(file:File){
    if(busy||processing)return;
    setError('');
    if(!/\.(mp4|mov|avi|mkv|webm)$/i.test(file.name)){setError('Choose an MP4, MOV, AVI, MKV, or WebM video.');return;}
    if(health&&file.size>health.max_upload_bytes){setError(`The video exceeds the ${size(health.max_upload_bytes)} limit.`);return;}
    const replacedVideo=video;
    setBusy(true);setUploadProgress(0);setMode('upload');setEvents([]);setResultView(false);setVideo(null);setLocalSrc(URL.createObjectURL(file));
    const data=new FormData();data.append('file',file);
    const request=new XMLHttpRequest();uploadRequest.current=request;request.open('POST','/api/video/upload');
    request.upload.onprogress=e=>{if(e.lengthComputable)setUploadProgress(Math.round(e.loaded/e.total*100));};
    request.onload=()=>{setBusy(false);try{const result=JSON.parse(request.responseText);if(request.status>=400)throw new Error(result.detail||'Upload failed.');setVideo(result);setAnswers([]);setEntities([]);if(replacedVideo)void api(`/api/video/${replacedVideo.id}`,{method:'DELETE'}).catch(()=>{});}catch(e){setError((e as Error).message);setLocalSrc('');if(replacedVideo)setVideo(replacedVideo);}};
    request.onerror=()=>{setBusy(false);setError('Upload failed. Check that the backend is running.');setLocalSrc('');};
    request.onabort=()=>{setBusy(false);setLocalSrc('');};request.send(data);
  }
  async function loadUrl(e:React.FormEvent){
    e.preventDefault();setError('');
    try{const parsed=new URL(url);if(!['http:','https:'].includes(parsed.protocol))throw new Error();}catch{setError('Enter a valid public HTTP or HTTPS video URL.');return;}
    setBusy(true);setVideo(null);setLocalSrc('');setResultView(false);
    try{setVideo(await api<Video>('/api/video/url',{method:'POST',body:JSON.stringify({url})}));}catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  async function analyze(){
    if(!video||processing)return;
    setError('');setBusy(true);
    try{
      const next=await api<Video>(`/api/video/${video.id}/analyze`,{method:'POST',body:JSON.stringify({sample_interval:interval,chunk_seconds:chunk})});
      initiated.current=true;player.current?.pause();setVideo(next);setAnalyzing(true);setResultView(false);
    }catch(e){setError((e as Error).message);void api<Health>('/api/health').then(setHealth).catch(()=>{});}finally{setBusy(false);}
  }
  async function remove(){
    if(!video||processing||busy)return;
    setError('');
    try{await api(`/api/video/${video.id}`,{method:'DELETE'});setVideo(null);setLocalSrc('');setEvents([]);setEntities([]);setAnswers([]);setSelected(null);setExpanded(null);setCurrent(0);setMode(null);setResultView(false);setQuestion('');setUrl('');window.history.pushState({},'','/');}catch(e){setError((e as Error).message);}
  }
  function seek(seconds:number,eventId?:string){
    if(!player.current)return;
    player.current.pause();player.current.currentTime=Math.min(seconds,video?.duration||seconds);setCurrent(seconds);if(eventId)setSelected(eventId);
  }
  async function ask(e:React.FormEvent){
    e.preventDefault();if(!video||!question.trim()||asking)return;
    setAsking(true);setError('');
    try{const answer=await api<Answer>(`/api/video/${video.id}/question`,{method:'POST',body:JSON.stringify({question:question.trim()})});setAnswers(previous=>[...previous,answer]);setQuestion('');}catch(e){setError((e as Error).message);}finally{setAsking(false);}
  }
  function exportResults(){
    if(!video)return;
    const blob=new Blob([JSON.stringify({video,events,entities,questions:answers},null,2)],{type:'application/json'}),link=document.createElement('a'),objectUrl=URL.createObjectURL(blob);link.href=objectUrl;link.download=`video-analysis-${video.id}.json`;link.click();URL.revokeObjectURL(objectUrl);
  }

  return <div className="app">
    <header className="topbar"><a className="brand" href="/" onClick={e=>{e.preventDefault();setResultView(false);window.history.pushState({},'','/');}}><span className="brand-icon"><ScanLine size={23}/></span><span>Temporal<span className="brand-secondary"> / video intelligence</span></span></a><span className="top-note">See the sequence. Find the moment.</span></header>
    <main>
      <div className="page-heading"><div><div className="eyebrow"><span/> VIDEO UNDERSTANDING & TEMPORAL REASONING</div><h1>{resultView?'Your video, understood.':'Understand what happened'}{!resultView&&<><br/><span>— and when.</span></>}</h1><p>{resultView?'Explore the observed events. Follow the evidence back to your video.':'Bring your video. Explore its events, their order, and the moments between.'}</p></div><div className="heading-mark" aria-hidden="true"><div/><div/><div/><ScanLine size={32}/></div></div>
      {error&&<div className="error" role="alert"><CircleAlert size={19}/><span>{error}</span><button className="icon-button" onClick={()=>setError('')} aria-label="Dismiss error"><X size={18}/></button></div>}
      {!resultView&&!processing&&<section className="input-section" aria-label="Video input">
        <div className="section-label"><span className="step">01</span><h2>Start with your video</h2><span className="muted">Your footage. Your questions.</span></div>
        <div className="input-body">
          <div className="input-tabs"><button className={mode==='upload'?'active':''} onClick={()=>setMode('upload')} disabled={busy}><Upload size={17}/>Upload video</button><span>or</span><button className={mode==='url'?'active':''} onClick={()=>setMode('url')} disabled={busy}><Link2 size={17}/>Video URL</button></div>
          <input ref={fileInput} type="file" accept=".mp4,.mov,.avi,.mkv,.webm" hidden onChange={e=>{if(e.target.files?.[0])upload(e.target.files[0]);e.target.value='';}}/>
          {mode===null&&<div className="unselected"><Film size={30}/><strong>No video selected</strong><p>Choose an input method above to begin.</p></div>}
          {mode==='upload'&&!video&&<div className={`dropzone ${dragging?'dragging':''}`} onDragOver={e=>{e.preventDefault();setDragging(true);}} onDragLeave={()=>setDragging(false)} onDrop={e=>{e.preventDefault();setDragging(false);if(e.dataTransfer.files[0])upload(e.dataTransfer.files[0]);}}>
            <div className="upload-icon"><Upload size={26}/></div><h3>{busy?'Loading your video…':'Drop your video here'}</h3><p>{busy?(uploadProgress<100?`Uploading · ${uploadProgress}%`:'Reading metadata and preparing playback…'):<>or <button className="text-button" onClick={()=>fileInput.current?.click()}>Browse files</button></>}</p><span className="file-types">MP4 · MOV · AVI · MKV · WEBM</span>{busy&&<progress max="100" value={uploadProgress} aria-label="Upload progress"/>}
          </div>}
          {mode==='url'&&!video&&<form className="url-form" onSubmit={loadUrl}><label htmlFor="video-url">Public video link</label><div><Link2 size={19}/><input id="video-url" type="url" placeholder="Paste a public video URL…" value={url} onChange={e=>setUrl(e.target.value)} required disabled={busy}/><button className="primary small" disabled={busy||!url.trim()}>{busy?'Loading…':'Load video'}</button></div><p>Use a direct video file link. Streaming pages, login-protected links, and DRM video are not supported.</p></form>}
          {video&&<div className="selected-file"><div className="file-symbol"><Film size={23}/></div><div><strong>{video.filename}</strong><p>{size(video.size)} <span>·</span> {time(video.duration)} <span>·</span> {video.format.toUpperCase()}</p></div><span className="file-check"><Check size={16}/>Ready</span><button className="text-button" onClick={()=>fileInput.current?.click()}>Replace</button><button className="icon-button" aria-label="Remove video" onClick={remove}><X size={19}/></button></div>}
          {video&&<div className="preview"><video ref={player} src={src} controls preload="metadata" onTimeUpdate={e=>setCurrent(e.currentTarget.currentTime)} onError={()=>setError('The browser cannot play this source format. The analysis pipeline creates an MP4 preview with FFmpeg.')} /><span>Preview · starts paused</span></div>}
          <div className="input-footer"><button className="text-button settings-toggle" onClick={()=>setAdvanced(!advanced)}><SlidersHorizontal size={16}/>Analysis settings<ChevronDown size={15}/></button><button className="primary" disabled={!video||busy} onClick={analyze}><ScanLine size={18}/>{busy?'Preparing…':'Analyze video'}<ArrowUpRight size={17}/></button></div>
          {advanced&&<div className="settings"><label>Sample every <select value={interval} onChange={e=>setInterval(Number(e.target.value))}><option value={.5}>0.5 seconds</option><option value={1}>1 second</option><option value={2}>2 seconds</option><option value={5}>5 seconds</option></select></label><label>Segment length <select value={chunk} onChange={e=>setChunk(Number(e.target.value))}><option value={5}>5 seconds</option><option value={10}>10 seconds</option><option value={20}>20 seconds</option><option value={60}>60 seconds</option></select></label><p>Smaller intervals capture more detail and take longer. Keep each segment at 24 frames or fewer.</p></div>}
        </div>
      </section>}
      {!resultView&&!processing&&<div className="process-notes"><div><Clock3 size={19}/><span><strong>Every event has a time</strong><small>See order, duration, and repetition.</small></span></div><div><Layers3 size={19}/><span><strong>Follow people & objects</strong><small>Review visual tracks and uncertainty.</small></span></div><div><MessageSquare size={19}/><span><strong>Answers with evidence</strong><small>Jump from an answer to its moment.</small></span></div></div>}
      {processing&&video&&<section className="processing" aria-live="polite"><div className="processing-icon"><ScanLine size={35}/></div><div className="eyebrow">ANALYSIS IN PROGRESS</div><h2>Finding the story in your video.</h2><p>{video.filename}</p><div className="progress-line"><progress max="100" value={video.progress} aria-label="Analysis progress"/><span>{Math.round(video.progress)}%</span></div><strong>{video.stage}</strong><p className="muted">Progress follows completed processing stages. Model inference can take several minutes.</p></section>}
      {resultView&&video&&<>
        <div className="results-meta"><span className="ready-badge"><Check size={15}/>Analysis complete</span><strong>{video.filename}</strong><div><span>{time(video.duration)} duration</span><span>{events.length} events</span><span>{entities.length} entities</span></div><button className="text-button" onClick={exportResults}><Download size={16}/>Export</button><button className="text-button" onClick={()=>{setResultView(false);window.history.pushState({},'','/');}}><RotateCcw size={15}/>Analyze again</button></div>
        <div className="workspace">
          <section className="video-panel"><div className="panel-heading"><span className="eyebrow">SOURCE VIDEO</span><span className="mono">{time(current)} / {time(video.duration)}</span></div><video ref={player} src={src} controls preload="metadata" onTimeUpdate={e=>setCurrent(e.currentTarget.currentTime)} onError={()=>setError('Could not load the video preview. Please check the backend.')} /><div className="video-bottom"><span>{video.width} × {video.height} <span>·</span> {video.fps.toFixed(2)} fps <span>·</span> {video.codec}</span><label>Playback speed<select defaultValue="1" onChange={e=>{if(player.current)player.current.playbackRate=Number(e.target.value);}}><option value=".5">0.5×</option><option value="1">1×</option><option value="1.5">1.5×</option><option value="2">2×</option></select></label></div></section>
          <aside className="summary-panel"><div className="panel-heading"><h2>Video summary</h2><Layers3 size={20}/></div><p className="summary-text">{video.summary}</p><div className="divider"/><span className="eyebrow">KEY MOMENTS</span><div className="key-events">{events.slice(0,showSummary?events.length:3).map(event=><button key={event.id} onClick={()=>seek(event.start_time,event.id)}><span className="mono">{time(event.start_time)}</span><span>{event.description}</span><ChevronRight size={15}/></button>)}{!events.length&&<p>No events were confidently identified.</p>}</div>{events.length>3&&<button className="text-button" onClick={()=>setShowSummary(!showSummary)}>{showSummary?'Show less':'Show all moments'}<ChevronDown size={15}/></button>}</aside>
        </div>
        <section className="timeline-section"><div className="section-label"><span className="step">02</span><h2>The event timeline</h2><span className="muted">Click a moment to seek. Playback stays paused.</span></div><div className="filters"><div className="search"><Search size={17}/><input aria-label="Search events" placeholder="Search events…" value={search} onChange={e=>setSearch(e.target.value)}/></div><div className="category-filters" aria-label="Filter events">{categories.map(c=><button key={c} className={category===c?'active':''} onClick={()=>setCategory(c)} aria-pressed={category===c}>{c}</button>)}</div></div><div className="timeline-ruler"><div className="ruler-line"/>{filtered.map((event,index)=><button key={event.id} className={`timeline-marker ${selected===event.id?'selected':''}`} style={{left:`${Math.max(1,Math.min(99,event.start_time/video.duration*100))}%`,top:index%2?31:9}} title={`Approximately ${time(event.start_time)}–${time(event.end_time)} · ${event.description} · ${event.duration.toFixed(1)}s · ${Math.round(event.confidence*100)}% model confidence`} aria-label={`${time(event.start_time)}: ${event.description}`} onClick={()=>seek(event.start_time,event.id)}><span/></button>)}<div className="ruler-labels">{[0,.25,.5,.75,1].map(r=><span key={r}>{time(video.duration*r)}</span>)}</div></div>
          <div className="event-log"><div className="event-log-head"><span>TIME</span><span>OBSERVED EVENT</span><span>ENTITIES</span><span>DURATION</span></div>{filtered.map(event=><React.Fragment key={event.id}><div className={`event-row ${selected===event.id?'selected':''}`}><button className="timestamp" onClick={()=>seek(event.start_time,event.id)}><Play size={11}/>{time(event.start_time)}</button><button className="event-description" onClick={()=>{setExpanded(expanded===event.id?null:event.id);setSelected(event.id);}}><span>{event.description}</span><small>{event.category} · Approximate timing</small><ChevronDown size={15}/></button><span className="entities-cell">{event.entities.join(', ')||'Not identified'}{event.identity_uncertain&&<small>Identity uncertain</small>}</span><span className="duration-cell">{event.duration>0?`${event.duration.toFixed(1)} s`:'Instant observed'}</span></div>{expanded===event.id&&<div className="event-details"><span>Start <button className="text-button mono" onClick={()=>seek(event.start_time,event.id)}>{time(event.start_time)}</button></span><span>End <button className="text-button mono" onClick={()=>seek(event.end_time,event.id)}>{time(event.end_time)}</button></span><span>Model confidence {Math.round(event.confidence*100)}%</span><span>Timing resolution ~{event.timing_uncertainty}s</span><div>Evidence frames: {event.evidence_times.map((t,i)=><button className="timestamp" key={i} onClick={()=>seek(t,event.id)}>{time(t)}</button>)}</div></div>}</React.Fragment>)}{!filtered.length&&<div className="no-events">{events.length?'No events match this filter.':'No events were confidently identified in the sampled frames.'}</div>}</div>
        </section>
        <section className="question-section"><div className="section-label"><span className="step">03</span><h2>Ask about this video</h2><span className="muted">Answers grounded in observed events.</span></div><form className="question-form" onSubmit={ask}><MessageSquare size={21}/><input aria-label="Question about the video" placeholder="What happened immediately before the last event?" value={question} onChange={e=>setQuestion(e.target.value)} maxLength={1000}/><button className="primary" disabled={!question.trim()||asking}>{asking?'Finding evidence…':'Ask AI'}<ArrowUpRight size={16}/></button></form><div className="suggestions"><span>Try asking</span>{['What happened first?','Describe the sequence of events.','Which events were repeated?'].map(q=><button key={q} onClick={()=>setQuestion(q)}>{q}</button>)}</div><div className="answer-history" aria-live="polite">{answers.map((answer,index)=><article className="answer" key={`${answer.created_at}-${index}`}><div className="answer-question"><MessageSquare size={16}/><strong>{answer.question}</strong></div><div className="answer-content"><span className="answer-icon"><ScanLine size={18}/></span><div><div className="eyebrow">{answer.supported?'EVIDENCE-BASED ANSWER':'INSUFFICIENT EVIDENCE'}</div><p>{answer.answer}</p><div className="answer-refs">{answer.timestamps.map((ref,i)=><button key={i} onClick={()=>seek(ref.time)} title={ref.label}><Play size={11}/><span className="mono">{time(ref.time)}</span><span>{ref.label}</span></button>)}</div></div></div></article>)}</div></section>
        <section className="track-section"><button className="disclosure" onClick={()=>setShowTracks(!showTracks)} aria-expanded={showTracks}><Layers3 size={19}/><strong>Entity tracks</strong><span>{entities.length} visual tracks</span><ChevronDown size={18}/></button>{showTracks&&<div className="tracks">{entities.map(entity=><article key={entity.id}><strong>{entity.id}</strong><span>{entity.label} · {entity.identity_uncertain?'Identity uncertain':'Visual association'}</span><p>{entity.appearance}</p><div><button className="timestamp" onClick={()=>seek(entity.first_seen)}>{time(entity.first_seen)}</button><span> to </span><button className="timestamp" onClick={()=>seek(entity.last_seen)}>{time(entity.last_seen)}</button></div><small>{entity.observations.length} observed frames; first-to-last span is not continuous presence.</small></article>)}</div>}</section>
        <details className="limitations"><summary><CircleAlert size={16}/>Analysis coverage & limitations</summary><ul>{video.limitations?.map((limitation,i)=><li key={i}>{limitation}</li>)}</ul></details>
      </>}
      {!processing&&!resultView&&health&&!health.vision.ready&&<details className="model-setup"><summary><CircleAlert size={16}/>Vision model setup required</summary><p>{health.vision.message}</p><p>Videos stay on the backend machine. Configure the local vision model before analysis; no simulated results are used.</p></details>}
      <footer><span>Temporal <span> / </span> Video intelligence</span><span>Observed evidence. Explicit uncertainty.</span></footer>
    </main>
  </div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
