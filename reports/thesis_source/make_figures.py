"""Build dissertation figures from saved experiments, without rerunning a model."""
from pathlib import Path
import csv, json, sys
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from reportlab.lib import colors
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
OUT = HERE / 'figures'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT))
from evaluate import fixed_predictions, match_predictions, gallery
from pipeline import parse_label

def load(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))

def save(d, name):
    pdf = OUT / (name+'.pdf')
    renderPDF.drawToFile(d, str(pdf))
    document = pdfium.PdfDocument(str(pdf))
    bitmap = document[0].render(scale=2.5)
    bitmap.to_pil().convert('RGB').save(OUT/(name+'.png'))
    document.close()

def chart(title, labels, series, legend, name, ymax=100):
    d = Drawing(600, 300)
    d.add(String(35, 280, title, fontName='Helvetica-Bold', fontSize=14))
    c = VerticalBarChart()
    c.x, c.y, c.width, c.height = 55, 60, 510, 185
    c.data = series
    c.categoryAxis.categoryNames = labels
    c.categoryAxis.labels.fontSize = 9
    c.valueAxis.valueMin, c.valueAxis.valueMax = 0, ymax
    c.valueAxis.labels.fontSize = 9
    for i, color in enumerate(['#14776E','#426A9A','#A15E36']):
        c.bars[i].fillColor = colors.HexColor(color)
        c.bars[i].strokeColor = None
    d.add(c)
    for i, item in enumerate(legend):
        d.add(Rect(60+i*175, 20, 10,10, fillColor=c.bars[i].fillColor, strokeColor=None))
        d.add(String(75+i*175,20,item,fontSize=10))
    save(d,name)

def lines(title, rows, keys, legend, name, ymax=None):
    d=Drawing(600,300)
    d.add(String(35,280,title,fontName='Helvetica-Bold',fontSize=14))
    c=LinePlot(); c.x,c.y,c.width,c.height=55,60,510,185
    c.data=[[(i+1,float(r[k])) for i,r in enumerate(rows)] for k in keys]
    c.xValueAxis.valueMin=1; c.xValueAxis.valueMax=len(rows)
    c.xValueAxis.valueStep=max(1,len(rows)//5)
    c.yValueAxis.valueMin=0
    if ymax: c.yValueAxis.valueMax=ymax
    for i,color in enumerate(['#14776E','#426A9A','#A15E36']):
        c.lines[i].strokeColor=colors.HexColor(color); c.lines[i].strokeWidth=1.7
    d.add(c)
    d.add(String(260,40,'Completed epoch',fontSize=10))
    for i,item in enumerate(legend):
        d.add(Line(60+i*175,22,72+i*175,22,strokeColor=c.lines[i].strokeColor,strokeWidth=2))
        d.add(String(77+i*175,18,item,fontSize=9))
    save(d,name)

def diagram(title, nodes, edges, name, height=430):
    d=Drawing(600,height)
    d.add(String(20,height-25,title,fontName='Helvetica-Bold',fontSize=15))
    for a,b in edges:
        x,y,w,h,_=nodes[a]; xx,yy,ww,hh,_=nodes[b]
        if name=='runtime' and (a,b)==(8,2):
            d.add(Line(x+w,y+h/2,592,y+h/2,strokeColor=colors.HexColor('#526472')))
            d.add(Line(592,y+h/2,592,yy+hh/2,strokeColor=colors.HexColor('#526472')))
            d.add(Line(592,yy+hh/2,xx+ww,yy+hh/2,strokeColor=colors.HexColor('#526472')))
            d.add(Polygon([xx+ww,yy+hh/2,xx+ww+8,yy+hh/2+4,xx+ww+8,yy+hh/2-4],fillColor=colors.HexColor('#526472'),strokeColor=None))
            continue
        if abs(y-yy)<10:
            start=(x+w,y+h/2) if xx>x else (x,y+h/2)
            end=(xx,yy+hh/2) if xx>x else (xx+ww,yy+hh/2)
        else:
            start=(x+w/2,y) if yy<y else (x+w/2,y+h)
            end=(xx+ww/2,yy+hh) if yy<y else (xx+ww/2,yy)
        d.add(Line(*start,*end,strokeColor=colors.HexColor('#526472'),strokeWidth=1.4))
        ex,ey=end; sx,sy=start
        import math
        angle=math.atan2(ey-sy,ex-sx)
        pts=[ex,ey,ex-8*math.cos(angle-.4),ey-8*math.sin(angle-.4),ex-8*math.cos(angle+.4),ey-8*math.sin(angle+.4)]
        d.add(Polygon(pts,fillColor=colors.HexColor('#526472'),strokeColor=None))
    for x,y,w,h,text in nodes:
        d.add(Rect(x,y,w,h,rx=5,ry=5,fillColor=colors.HexColor('#F0F6F5'),strokeColor=colors.HexColor('#26796D'),strokeWidth=1))
        items=text.split('\n')
        for j,t in enumerate(items):
            d.add(String(x+w/2,y+h/2+7*(len(items)-1)-14*j,t,textAnchor='middle',fontSize=10,fontName='Helvetica'))
    save(d,name)

def main():
    audit=load('evidence/data_audit.json')['counts']
    chart('Usable images in the retained source split',['Train','Validation','Test'],[[audit[s]['images'] for s in ['train','val','test']]],['Images'],'dataset',4200)
    chart('Annotated objects by split',['Train','Validation','Test'],[[audit[s]['fire_boxes'] for s in ['train','val','test']],[audit[s]['smoke_boxes'] for s in ['train','val','test']]],['Fire boxes','Smoke boxes'],'class_distribution',3200)
    rows=list(csv.DictReader((ROOT/'runs/train/yolov8n/results.csv').open()))
    lines('Original nano training losses',rows,['train/box_loss','train/cls_loss','train/dfl_loss'],['Box loss','Classification loss','Distribution focal loss'],'training_loss')
    lines('Original nano validation performance',rows,['metrics/mAP50(B)','metrics/mAP50-95(B)'],['mAP at IoU 0.50','mAP at IoU 0.50 to 0.95'],'training_map',1)
    old=load('evidence/test_metrics.json')
    ref=load('evidence/optimization_test_yolov8n_refined.json')[0]
    dom=load('evidence/optimization_test_yolov8n_domain.json')[0]
    chart('Held-out test comparison under unequal training budgets',['Small 8','Nano 20','Nano 20+4','Nano 20+4+3'],[[100*x['map50'] for x in [old['s'],old['n'],ref,dom]],[100*x['map50_95'] for x in [old['s'],old['n'],ref,dom]]],['mAP at IoU 0.50 (%)','mAP at IoU 0.50 to 0.95 (%)'],'comparison')
    thresholds=[.25,.5,.75,.9]
    chart('Measured operating points on the same test set',[str(t) for t in thresholds],[[100*dom['thresholds'][str(t)]['overall']['precision'] for t in thresholds],[100*dom['thresholds'][str(t)]['overall']['recall'] for t in thresholds]],['Precision (%)','Recall (%)'],'thresholds')
    diagram('FireSense AI system architecture',[
      (20,310,160,55,'Camera or video file\nStill image'),(220,310,160,55,'Browser decoding\nCapture and resize'),(420,310,160,55,'Local inference API\nValidated image request'),
      (420,190,160,65,'YOLOv8 nano\nSelected domain weights\n416 pixel inference'),(220,190,160,65,'JSON boxes and scores\nNormalized coordinates'),(20,190,160,65,'Canvas preview\nBoxes and source labels'),
      (20,70,160,55,'PNG frame download\nSilent WebM recording'),(220,70,160,55,'Local evidence\nProfile and model hash'),(420,70,160,55,'Offline pipeline\nDataset and checkpoints')],[(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(8,7),(7,3)],'architecture')
    diagram('Training and evaluation workflow',[
      (20,310,160,55,'Public YOLO dataset\nLicense and source audit'),(220,310,160,55,'Image and label checks\nOriginal split retained'),(420,310,160,55,'Train original nano\nCompare small baseline'),
      (420,190,160,65,'Refine nano checkpoint\nTraining only close-ups\nThree epoch adaptation'),(220,190,160,65,'Validation selection\nDevelopment video review\nPredeclared acceptance'),(20,190,160,65,'Held-out test metrics\nPer-class errors and AP'),
      (20,70,160,55,'Document limitations\nSave test evidence'),(220,70,160,55,'Deploy local profile\nKeep rollback weights'),(420,70,160,55,'Browser checks\nExports and accessibility')],[(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8)],'workflow')
    diagram('YOLOv8 detection path used in this project',[
      (30,315,145,60,'RGB input\n416 pixel letterbox'),(225,315,145,60,'Backbone\nConv and C2f blocks'),(425,315,145,60,'SPPF\nSpatial feature pooling'),
      (425,190,145,65,'Neck\nUpsample and concatenate\nC2f feature fusion'),(225,190,145,65,'Multi-scale Detect head\nFire and smoke scores\nBounding box regression'),(30,190,145,65,'Postprocessing\nScore filter and NMS\nCoordinate mapping'),
      (225,65,145,55,'Rendered detections\nOriginal image space')],[(0,1),(1,2),(2,3),(3,4),(4,5),(5,6)],'model_architecture')
    diagram('Live browser analysis and export workflow',[
      (20,310,160,55,'Select source\nCamera video or image'),(220,310,160,55,'Decode source\nRender independent preview'),(420,310,160,55,'Capture current frame\nOne request in flight'),
      (420,190,160,65,'Infer with selected model\nReturn boxes and scores'),(220,190,160,65,'Render matching overlay\nExpire stale detections'),(20,190,160,65,'Record preview if enabled\nKeep raw source timing'),
      (20,70,160,55,'Stop or reach video end\nFinalize recording'),(220,70,160,55,'Download PNG or WebM\nPartial output labelled'),(420,70,160,55,'Continue until stop\nNext decoded frame')],[(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(4,8),(8,2)],'runtime')
    records=load('runs/optimization/test_yolov8n_domain_416/predictions.json')
    predictions=fixed_predictions(records,.5)
    image_rows=[]
    for path in sorted((ROOT/'data/prepared/test/images').glob('*.jpg')):
        with Image.open(path) as im: w,h=im.size
        labels=parse_label((ROOT/f'data/prepared/test/labels/{path.stem}.txt').read_text())
        gt=[[c,(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h] for c,x,y,bw,bh in labels]
        pred=predictions.get(path.stem,[])
        tp,fp,fn=match_predictions(gt,pred)
        image_rows.append(dict(image=str(path),gt=gt,pred=pred,tp=tp,fp=fp,fn=fn))
    successes=[r for r in image_rows if sum(r['tp'])>0 and sum(r['fp'])+sum(r['fn'])==0]
    failures=sorted((r for r in image_rows if sum(r['fn'])+sum(r['fp'])>0),key=lambda r:sum(r['fn'])+sum(r['fp']),reverse=True)
    chosen_success=[successes[i] for i in [0,len(successes)//2,len(successes)-1]]
    gallery(chosen_success,OUT/'test_successes.jpg','Current model | score >= 0.50 | match IoU >= 0.50')
    gallery(failures[:3],OUT/'test_failures.jpg','Current model | highest object-error counts at score >= 0.50')
    (OUT/'gallery_selection.json').write_text(json.dumps(dict(successes=chosen_success,failures=failures[:3]),indent=2))
    total=[sum(sum(r[k]) for r in image_rows) for k in ['tp','fp','fn']]
    assert total==[1083,81,498],total
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
    canvas=Image.new('RGB',(900,710),'white');draw=ImageDraw.Draw(canvas)
    for col,(file,label) in enumerate([('baseline_raw_frames.json','Previous refined model'),('candidate_final.json','Current domain adapted model')]):
        row=load('evidence/user_video/'+file)['frames'][3]
        with Image.open(ROOT/'evidence/user_video/frame_3.jpg') as im:
            im=im.convert('RGB');im.thumbnail((420,620))
        overlay=ImageDraw.Draw(im)
        for box in row['detections']:
            if box['confidence']<.5:continue
            xy=[box['box'][i]*([im.width,im.height][i%2]) for i in range(4)]
            overlay.rectangle(xy,outline='#00DD55',width=4)
            overlay.text((xy[0],max(0,xy[1]-25)),f"{box['label']} {box['confidence']:.0%}",font=font,fill='#00DD55',stroke_width=1,stroke_fill='black')
        draw.text((15+450*col,12),label,font=font,fill='black')
        canvas.paste(im,(15+450*col,55))
    canvas.save(OUT/'video_comparison.jpg')
    # One page per test case makes the annotation-to-prediction comparison readable.
    case_dir=OUT/'test_cases';case_dir.mkdir(exist_ok=True)
    def case_key(row):
        name=Path(row['image']).stem
        return int(name.split('_')[-1]) if name.split('_')[-1].isdigit() else name
    good=sorted(successes,key=case_key)
    bad=sorted(failures,key=lambda r:(-(sum(r['fp'])+sum(r['fn'])),case_key(r)))
    selected=[]
    for kind,items in [('success',good),('error',bad)]:
        for j in range(15):
            row=items[min(len(items)-1,round(j*(len(items)-1)/14))]
            selected.append((kind,row))
    case_manifest=[]
    for index,(kind,row) in enumerate(selected,1):
        width,height=1400,760
        sheet=Image.new('RGB',(width,height),'white');draw=ImageDraw.Draw(sheet)
        large=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
        small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
        for col,field in enumerate(['gt','pred']):
            with Image.open(row['image']) as src:
                original_w,original_h=src.size;im=src.convert('RGB');im.thumbnail((660,680))
            overlay=ImageDraw.Draw(im);scale_x=im.width/original_w;scale_y=im.height/original_h
            boxes=row[field]
            for box in boxes:
                cls=int(box[0]);coords=box[1:] if field=='gt' else box[2:]
                xy=[coords[0]*scale_x,coords[1]*scale_y,coords[2]*scale_x,coords[3]*scale_y]
                color='#16803A' if cls==0 else '#1265A8'
                overlay.rectangle(xy,outline=color,width=4)
                label=['fire','smoke'][cls]+(f' {box[1]:.2f}' if field=='pred' else '')
                overlay.text((xy[0],max(0,xy[1]-24)),label,font=small,fill=color,stroke_width=2,stroke_fill='white')
            x=20+col*700
            draw.text((x,15),'Ground truth' if field=='gt' else 'Model predictions',font=large,fill='#111111')
            sheet.paste(im,(x,60))
        path=case_dir/f'case-{index:02}.jpg';sheet.save(path,quality=92)
        case_manifest.append(dict(index=index,kind=kind,image=Path(row['image']).name,
            tp=sum(row['tp']),fp=sum(row['fp']),fn=sum(row['fn']),
            truth_count=len(row['gt']),pred_count=len(row['pred']),path=str(path.relative_to(HERE))))
    (OUT/'test_case_manifest.json').write_text(json.dumps(case_manifest,indent=2))
    with Image.open(ROOT/'evidence/download_checks/desktop.png') as im:
        im.crop((0,0,im.width,min(im.height,1000))).save(OUT/'dashboard.png')
    (OUT/'figure_checks.json').write_text(json.dumps(dict(test_counts=total,success_count=len(successes),error_image_count=len(failures),source='saved test predictions',threshold=.5),indent=2))
    print('Created measured charts, four diagrams and prediction galleries',total)

if __name__=='__main__':main()
