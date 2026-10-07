import cv2
import numpy as np

def iou(a, b):
    x1,y1,x2,y2 = max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])
    overlap = max(0,x2-x1)*max(0,y2-y1)
    union = (a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-overlap
    return overlap/union if union > 0 else 0

def appearance(image, box):
    h,w = image.shape[:2]
    x1,y1,x2,y2 = [int(value*size) for value,size in zip(box,[w,h,w,h])]
    crop = image[y1:y2,x1:x2]
    if not crop.size:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv],[0,1],None,[16,16],[0,180,0,256])
    return cv2.normalize(hist,hist).flatten()

class Tracker:
    '''Conservative appearance + camera-compensated spatial association.

    This is short-term tracking, not biometric identity or guaranteed re-ID.
    Tracks remain available for 30 seconds during occlusion. Ambiguous matches
    produce uncertain new tracks instead of merging two people.
    '''
    def __init__(self, max_gap=30):
        self.tracks = []
        self.max_gap = max_gap
        self.previous_gray = None
        self.last_frame_time = None

    def compensate_camera(self, image, time):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if self.previous_gray is not None and self.previous_gray.shape == gray.shape:
            points = cv2.goodFeaturesToTrack(self.previous_gray, maxCorners=150, qualityLevel=.02, minDistance=12)
            if points is not None and len(points) >= 12:
                moved, status, _ = cv2.calcOpticalFlowPyrLK(self.previous_gray, gray, points, None)
                if moved is not None and status is not None:
                    good = status.ravel() == 1
                    if good.sum() >= 12:
                        matrix, inliers = cv2.estimateAffinePartial2D(points[good], moved[good], method=cv2.RANSAC, ransacReprojThreshold=3)
                        if matrix is not None and inliers is not None and inliers.mean() >= .6:
                            h,w = gray.shape
                            for track in self.tracks:
                                corners = np.array([[track['box'][0]*w,track['box'][1]*h,1],[track['box'][2]*w,track['box'][3]*h,1]]) @ matrix.T
                                track['box'] = np.clip([corners[0,0]/w,corners[0,1]/h,corners[1,0]/w,corners[1,1]/h],0,1).tolist()
        self.previous_gray = gray
        self.last_frame_time = time

    def update(self, image, time, detections):
        self.compensate_camera(image, time)
        used, mapping = set(), {}
        for detection in sorted(detections, key=lambda d: -d.confidence):
            box = detection.box
            if not all(np.isfinite(v) and 0 <= v <= 1 for v in box) or box[2] <= box[0] or box[3] <= box[1]:
                continue
            hist = appearance(image, box)
            candidates = []
            for index, track in enumerate(self.tracks):
                if index in used or time-track['last_seen'] > self.max_gap or track['label'].lower() != detection.label.lower():
                    continue
                similarity = max(0,cv2.compareHist(hist.astype('float32'),track['hist'].astype('float32'),cv2.HISTCMP_CORREL)) if hist is not None and track['hist'] is not None else 0
                spatial = iou(box,track['box'])
                # Re-entry requires strong appearance; spatial-only associations
                # are allowed only close in time and with supporting appearance.
                if (similarity > .90) or (spatial > .25 and similarity > .65 and time-track['last_seen'] < 5):
                    candidates.append((.75*similarity+.25*spatial,index))
            candidates.sort(reverse=True)
            ambiguous = len(candidates) > 1 and candidates[0][0]-candidates[1][0] < .12
            if candidates and candidates[0][0] >= .70 and not ambiguous:
                score,index = candidates[0]
                track = self.tracks[index]
                track['identity_confidence'] = min(track['identity_confidence'],score,detection.confidence)
                track['identity_uncertain'] |= score < .85
                used.add(index)
            else:
                index = len(self.tracks)
                track = {'id': f'{detection.category[:-1] if detection.category in ("Vehicles","Objects") else "Person" if detection.category == "People" else "Entity"}_{index+1:02d}', 'label': detection.label, 'category': detection.category, 'appearance': detection.appearance, 'first_seen': time, 'last_seen': time, 'identity_confidence': detection.confidence, 'identity_uncertain': ambiguous or detection.confidence < .85, 'observations': []}
                self.tracks.append(track)
                used.add(index)
            track.update(box=box, hist=hist, last_seen=time)
            track['observations'].append({'time':time,'box':box,'confidence':detection.confidence})
            mapping[detection.local_id] = track['id']
        return mapping

    def export(self):
        return [{key:value for key,value in track.items() if key != 'hist'} for track in self.tracks]
