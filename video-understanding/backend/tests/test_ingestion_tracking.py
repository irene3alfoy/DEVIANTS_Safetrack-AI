import socket
import cv2
import numpy as np
import pytest
from backend.ingestion import metadata,public_url
from backend.pipeline import sample_chunk
from backend.tracking import Tracker
from backend.vision import Detection

def test_chunk_sampling_keeps_global_times(tmp_path):
    path=tmp_path/'fixture.avi'
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),10,(64,48))
    for index in range(70):writer.write(np.full((48,64,3),index,dtype=np.uint8))
    writer.release()
    info=metadata(path)
    assert info['duration']==pytest.approx(7,.1)
    frames=sample_chunk(path,5,7,.5)
    assert frames[0]['time']==pytest.approx(5,.11)
    assert frames[-1]['time']==pytest.approx(6.5,.11)
    assert all(5<=frame['time']<7 for frame in frames)

def test_corrupt_video_does_not_produce_metadata(tmp_path):
    path=tmp_path/'broken.mp4'
    path.write_bytes(b'not a video')
    with pytest.raises(ValueError):metadata(path)

@pytest.mark.parametrize('url',['file:///etc/passwd','http://user:password@example.com/a.mp4','http://127.0.0.1/video.mp4','http://10.0.0.1/video.mp4','http://169.254.169.254/latest/meta-data','http://[::1]/video.mp4','http://example.com:8080/a.mp4'])
def test_url_security_rejects_private_and_non_http(url):
    with pytest.raises(ValueError):public_url(url)

def test_url_dns_checks_all_answers(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *args,**kwargs:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443)),(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))])
    with pytest.raises(ValueError):public_url('https://example.com/a.mp4')

def detection(local='p',box=None):
    return Detection(frame=0,local_id=local,label='box',appearance='red box',category='Objects',box=box or [.2,.2,.5,.5],confidence=.95)

def test_track_reconnects_after_temporary_gap_without_face_id():
    image=np.zeros((100,100,3),dtype=np.uint8)
    image[20:50,20:50]=(0,0,220)
    tracker=Tracker()
    first=tracker.update(image,0,[detection()])
    tracker.update(image,3,[])
    second=tracker.update(image,6,[detection()])
    assert first['p']==second['p']
    assert len(tracker.export())==1

def test_track_expiry_creates_new_identity():
    image=np.zeros((100,100,3),dtype=np.uint8)
    image[20:50,20:50]=(0,0,220)
    tracker=Tracker(max_gap=10)
    first=tracker.update(image,0,[detection()])
    second=tracker.update(image,20,[detection()])
    assert first['p']!=second['p']

def test_invalid_box_is_not_tracked():
    tracker=Tracker()
    assert tracker.update(np.zeros((100,100,3),dtype=np.uint8),0,[detection(box=[1,1,0,0])])=={}
