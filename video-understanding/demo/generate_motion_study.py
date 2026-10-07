"""Generate an opt-in actual video input, not precomputed analysis.

Synthetic geometric motion footage: starts/stops, short occlusion, two objects,
and simulated camera panning. No people, alarms, or security events are claimed.
"""
from pathlib import Path
import subprocess
import cv2
import numpy as np
from backend.ingestion import ffmpeg_binary

def generate():
    folder=Path(__file__).resolve().parent
    raw=folder/'motion-study.avi'
    writer=cv2.VideoWriter(str(raw),cv2.VideoWriter_fourcc(*'MJPG'),24,(960,540))
    if not writer.isOpened():raise RuntimeError('Could not create demo input video.')
    for index in range(24*24):
        t=index/24
        image=np.full((540,960,3),238,np.uint8)
        camera_shift=round(35*max(0,min(1,(t-16)/5)))
        for x in range(0,1100,80):cv2.line(image,(x-camera_shift,100),(x-camera_shift,460),(215,219,224),1)
        cv2.line(image,(0,370),(960,370),(180,187,198),2)
        if t<2:x=90
        elif t<7:x=90+65*(t-2)
        elif t<10:x=415
        elif t<15:x=415+50*(t-10)
        else:x=665
        x=round(x-camera_shift)
        cv2.rectangle(image,(x,265),(x+65,330),(50,95,205),-1)
        cv2.putText(image,'A',(x+20,307),cv2.FONT_HERSHEY_SIMPLEX,.8,(255,255,255),2)
        y=440-round(14*max(0,min(10,t-8)))
        cv2.circle(image,(820-camera_shift,y),29,(175,122,55),-1)
        cv2.putText(image,'B',(807-camera_shift,y+8),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),2)
        # Foreground obstacle visibly blocks object A while it moves behind it.
        cv2.rectangle(image,(510-camera_shift,235),(580-camera_shift,365),(90,96,110),-1)
        cv2.putText(image,'MOTION STUDY / SYNTHETIC INPUT',(42,55),cv2.FONT_HERSHEY_SIMPLEX,.65,(93,101,116),1)
        cv2.putText(image,f'{t:05.2f}s',(830,55),cv2.FONT_HERSHEY_SIMPLEX,.65,(93,101,116),1)
        writer.write(image)
    writer.release()
    subprocess.run([ffmpeg_binary(),'-nostdin','-y','-i',str(raw),'-c:v','libx264','-pix_fmt','yuv420p','-crf','22','-movflags','+faststart',str(folder/'motion-study.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    raw.unlink()
    print(folder/'motion-study.mp4')

if __name__=='__main__':generate()
