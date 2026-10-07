import pytest
from fastapi.testclient import TestClient
from backend import store,vision
from backend.main import app
import backend.main as main
import cv2
import numpy as np

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    monkeypatch.setattr(main,'DATA',tmp_path)
    with TestClient(app) as client:yield client

def test_api_invalid_upload_and_missing_video(client):
    result=client.post('/api/video/upload',files={'file':('notes.txt',b'text','text/plain')})
    assert result.status_code==400
    assert client.get('/api/video/missing/status').status_code==404

def test_model_unavailable_does_not_start_fake_analysis(client,monkeypatch):
    store.save_video({'id':'test','status':'uploaded','duration':30,'path':'unused'})
    async def unavailable():return {'ready':False,'message':'Vision model unavailable'}
    monkeypatch.setattr(vision,'health',unavailable)
    result=client.post('/api/video/test/analyze',json={})
    assert result.status_code==503
    assert store.video('test')['status']=='uploaded'

def test_question_requires_completed_analysis(client):
    store.save_video({'id':'test','status':'uploaded','duration':30})
    assert client.post('/api/video/test/question',json={'question':'What happened?'}).status_code==409

def test_empty_evidence_answer_is_timestamped_and_persisted(client):
    store.save_video({'id':'test','status':'complete','duration':90})
    result=client.post('/api/video/test/question',json={'question':'What happened first?'})
    assert result.status_code==200
    assert '[00:00–01:30]' in result.json()['answer']
    assert result.json()['supported'] is False
    assert len(client.get('/api/video/test/questions').json())==1

def test_invalid_batch_configuration_is_rejected(client):
    store.save_video({'id':'test','status':'uploaded','duration':90})
    result=client.post('/api/video/test/analyze',json={'sample_interval':.25,'chunk_seconds':60})
    assert result.status_code==400

def test_real_file_ingestion_browser_transcode_and_range(client,tmp_path):
    fixture=tmp_path/'source.avi'
    writer=cv2.VideoWriter(str(fixture),cv2.VideoWriter_fourcc(*'MJPG'),10,(128,96))
    for index in range(20):
        frame=np.zeros((96,128,3),dtype=np.uint8)
        cv2.rectangle(frame,(index+10,20),(index+30,40),(0,0,200),-1)
        writer.write(frame)
    writer.release()
    result=client.post('/api/video/upload',files={'file':('motion.avi',fixture.read_bytes(),'video/x-msvideo')})
    assert result.status_code==200,result.text
    video=result.json()
    assert video['duration']==pytest.approx(2,.1)
    assert video['preview_ready']
    response=client.get(f"/api/video/{video['id']}/media",headers={'Range':'bytes=0-99'})
    assert response.status_code==206
    assert len(response.content)==100
    assert response.headers['content-type']=='video/mp4'
    assert client.delete(f"/api/video/{video['id']}").status_code==200
    assert client.get(f"/api/video/{video['id']}").status_code==404
