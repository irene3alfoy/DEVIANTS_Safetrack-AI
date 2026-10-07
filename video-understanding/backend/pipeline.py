import asyncio
import math
from pathlib import Path
import cv2
from . import store, vision
from .ingestion import make_preview
from .tracking import Tracker
from .temporal import normalize, TemporalEngine, event_line

def sample_chunk(path, start, end, interval, max_width=768):
    '''Seek/decode only a bounded batch. POS_MSEC after decoding reflects video
    presentation time when the codec provides it; frame index/FPS is fallback.
    '''
    cap = cv2.VideoCapture(str(path))
    frames=[]
    fps=cap.get(cv2.CAP_PROP_FPS)
    try:
        for target in [start+i*interval for i in range(max(1,math.ceil((end-start)/interval)))]:
            if target>=end: break
            cap.set(cv2.CAP_PROP_POS_MSEC,target*1000)
            ok,image=cap.read()
            if not ok: continue
            actual=cap.get(cv2.CAP_PROP_POS_MSEC)/1000
            if not math.isfinite(actual) or (actual==0 and target>0):
                actual=max(0,(cap.get(cv2.CAP_PROP_POS_FRAMES)-1)/fps)
            if actual < start-interval or actual >= end+interval: continue
            h,w=image.shape[:2]
            if w>max_width:
                image=cv2.resize(image,(max_width,round(h*max_width/w)))
            if not frames or abs(actual-frames[-1]['time']) > .001:
                frames.append({'time':actual,'image':image})
    finally:
        cap.release()
    if not frames: raise ValueError('No readable frames in a video segment. The video may be corrupted.')
    return frames

async def run(video_id, interval, chunk_seconds):
    try:
        item=store.video(video_id)
        source=Path(item['path'])
        store.update(video_id,status='processing',stage='Preparing browser-compatible video',progress=2,error=None)
        preview=source.parent/'preview.mp4'
        if not preview.exists():
            await asyncio.to_thread(make_preview,source,preview)
        store.update(video_id,preview_ready=True,progress=8)
        tracker=Tracker()
        events=[]
        limitations={'Visual analysis only; audio is not analyzed.',f'Sampling interval: {interval:g} seconds. Brief events between sampled frames can be missed.', 'Timestamps and durations describe observed samples and are approximate; exact onset/offset can fall between samples.', 'Identity association uses appearance and motion evidence, not face recognition. Occlusion, similar appearances, and scene cuts can split tracks.'}
        duration=item['duration']
        count=math.ceil(duration/chunk_seconds)
        for index in range(count):
            start=index*chunk_seconds
            end=min(duration,start+chunk_seconds)
            store.update(video_id,stage=f'Reading frames · segment {index+1} of {count}',progress=8+82*index/count)
            frames=await asyncio.to_thread(sample_chunk,source,start,end,interval)
            store.update(video_id,stage=f'Detecting entities and events · segment {index+1} of {count}')
            observed=await vision.analyze_frames(frames)
            store.update(video_id,stage=f'Associating visual tracks · segment {index+1} of {count}')
            maps={}
            for frame_index,frame in enumerate(frames):
                detections=[d for d in observed.detections if d.frame==frame_index]
                maps[frame_index]=await asyncio.to_thread(tracker.update,frame['image'],frame['time'],detections)
            limitations.update(observed.limitations)
            for event in observed.events:
                indices=[event.start_frame,event.end_frame,*event.evidence_frames]
                if any(i<0 or i>=len(frames) for i in indices) or event.end_frame<event.start_frame or any(i<event.start_frame or i>event.end_frame for i in event.evidence_frames):
                    raise ValueError('The model referenced frames outside the supplied evidence. No results were published.')
                if event.confidence<.5:
                    limitations.add('Low-confidence event candidates were omitted.')
                    continue
                entity_ids=set()
                identity_uncertain=False
                for local_id in event.local_entities:
                    associated={maps[i][local_id] for i in event.evidence_frames if local_id in maps[i]}
                    if not associated:
                        identity_uncertain=True
                    entity_ids.update(associated)
                    if len(associated)>1: identity_uncertain=True
                known=tracker.export()
                identity_uncertain |= any(e['identity_uncertain'] for e in known if e['id'] in entity_ids)
                t0,t1=frames[event.start_frame]['time'],frames[event.end_frame]['time']
                events.append({'id':'pending','type':event.type,'description':event.description,'start_time':t0,'end_time':t1,'duration':t1-t0,'entities':sorted(entity_ids),'category':event.category,'confidence':event.confidence,'approximate':True,'timing_uncertainty':interval,'identity_uncertain':identity_uncertain,'continuous':event.continuous,'evidence_times':[frames[i]['time'] for i in event.evidence_frames]})
            # The image batch is released before decoding the next segment.
            del frames,observed
        store.update(video_id,stage='Normalizing events and building temporal graph',progress=92)
        events=normalize(events,interval)
        graph=TemporalEngine(events).graph()
        store.save_results(video_id,events,tracker.export(),graph)
        store.update(video_id,stage='Generating evidence-based summary',progress=97)
        # Extractive summary cannot add unsupported facts or alter timestamps.
        summary=' '.join(event_line(event)+'.' for event in events[:5]) if events else 'No events were confidently identified in the sampled visual evidence.'
        store.update(video_id,status='complete',stage='Ready',progress=100,summary=summary,limitations=sorted(limitations),event_count=len(events),entity_count=len(tracker.tracks),settings={'sample_interval':interval,'chunk_seconds':chunk_seconds})
    except asyncio.CancelledError:
        store.update(video_id,status='failed',stage='Interrupted',error='Analysis interrupted. Please retry.')
        raise
    except Exception as exc:
        store.update(video_id,status='failed',stage='Analysis failed',error=str(exc)[:1000])
