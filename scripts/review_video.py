"""Review fixed video frames with the browser's input sizing and unmodified scores."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import ROOT, save_json


def review(video, weights, tag, samples=8):
    import cv2
    import numpy as np
    import torch
    from ultralytics import YOLO
    from PIL import Image, ImageDraw
    torch.set_num_threads(2)
    capture=cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ValueError(f'Cannot decode video: {video}')
    count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT));fps=capture.get(cv2.CAP_PROP_FPS)
    if count<=0 or fps<=0 or samples<2:
        raise ValueError('Need a video with frame count/FPS and at least two samples')
    model=YOLO(str(weights));rows=[];tiles=[]
    try:
        for index in np.linspace(0,count-1,samples).astype(int):
            capture.set(cv2.CAP_PROP_POS_FRAMES,int(index));ok,frame=capture.read()
            if not ok:
                raise ValueError(f'Cannot decode frame {index}')
            h,w=frame.shape[:2];scale=min(640/w,480/h,1)
            small=cv2.resize(frame,(round(w*scale),round(h*scale)))
            ok,jpeg=cv2.imencode('.jpg',small,[cv2.IMWRITE_JPEG_QUALITY,85])
            if not ok:
                raise ValueError('Cannot encode analysis frame')
            result=model.predict(cv2.imdecode(jpeg,1),imgsz=416,conf=.05,iou=.7,device='0',verbose=False)[0]
            detections=[dict(label=result.names[int(c)],confidence=float(s),box=b)
                for c,s,b in zip(result.boxes.cls.tolist(),result.boxes.conf.tolist(),result.boxes.xyxyn.tolist())]
            rows.append(dict(frame=int(index),time_seconds=float(index/fps),detections=detections))
            tile=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));tile.thumbnail((270,360));draw=ImageDraw.Draw(tile)
            for d in detections:
                if d['confidence']<.5:continue
                x1,y1,x2,y2=d['box'];x1*=tile.width;x2*=tile.width;y1*=tile.height;y2*=tile.height
                draw.rectangle([x1,y1,x2,y2],outline='lime' if d['label']=='fire' else 'cyan',width=3)
                draw.text((x1,max(0,y1-12)),f"{d['label']} {d['confidence']:.2f}",fill='white',stroke_width=1,stroke_fill='black')
            tiles.append(tile)
    finally:
        capture.release()
    output=ROOT/'evidence/user_video';output.mkdir(exist_ok=True)
    positives=sum(any(d['label']=='fire' and d['confidence']>=.5 for d in row['detections']) for row in rows)
    summary=dict(video=str(video),weights=str(weights),samples=samples,minimum_score=.5,
        sampled_frames_with_fire=positives,notes='Presence review, not box-annotated accuracy; this video is development data.',frames=rows)
    save_json(output/f'{tag}.json',summary)
    gallery=Image.new('RGB',(1200,((samples+3)//4)*400),'white');draw=ImageDraw.Draw(gallery)
    for i,(tile,row) in enumerate(zip(tiles,rows)):
        x=10+i%4*300;y=10+i//4*400;gallery.paste(tile,(x,y));draw.text((x,y+365),f"{row['time_seconds']:.1f}s | score >= 0.50",fill='black')
    gallery.save(output/f'{tag}.jpg')
    print(f'{weights}: {positives}/{samples} sampled frames contain a retained fire box',flush=True)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',required=True,type=Path)
    parser.add_argument('--weights',default=ROOT/'models/yolov8n_refined.pt',type=Path)
    parser.add_argument('--tag',default='review')
    args=parser.parse_args()
    if not args.tag.replace('_','').replace('-','').isalnum():
        raise SystemExit('Use a simple alphanumeric output tag')
    review(args.video,args.weights,args.tag)
