import sys, json, cv2, numpy as np
import mediapipe as mp

src, out = sys.argv[1], sys.argv[2]
cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
pose = mp.solutions.pose.Pose(static_image_mode=False, model_complexity=1,
                              smooth_landmarks=True, enable_segmentation=False,
                              min_detection_confidence=0.5, min_tracking_confidence=0.5)
frames = []
while True:
    ok, img = cap.read()
    if not ok:
        break
    res = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if res.pose_world_landmarks:
        w = [[l.x, l.y, l.z, l.visibility] for l in res.pose_world_landmarks.landmark]
        n = [[l.x, l.y, l.z, l.visibility] for l in res.pose_landmarks.landmark]
    else:
        w = n = None
    frames.append({"world": w, "norm": n})
json.dump({"fps": fps, "frames": frames}, open(out, "w"))
print(len(frames), "frames,", sum(f["world"] is None for f in frames), "missing, fps", fps)
