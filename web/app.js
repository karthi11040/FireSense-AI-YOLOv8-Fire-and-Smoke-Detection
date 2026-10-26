import {AnnotatedRecording,downloadBlob,outputName} from './downloads.mjs';
const $ = id => document.getElementById(id);
const feed = $('feed'), fc = feed.getContext('2d');
const video = $('video'), capture = $('capture'), cc = capture.getContext('2d');
let ready=false, source='camera', mode='idle', running=false, stream=null, image=null, objectUrl=null;
let boxes=[], frames=0, epoch=0, controller=null, events=[], lastVideoTime=-1;
let frameHandle=null, fallbackTimer=null, frameTimes=[], lastResultAt=0;
let inputName='firesense',hasFrame=false;
const recording=new AnnotatedRecording(feed,updateDownloads,message=>error(message));
if(location.search.includes('view=simulator'))history.replaceState(null,'','/');

function log(title, detail) {
  const entry={time:new Date().toISOString(),title,detail,source:mode};
  events.unshift(entry); events=events.slice(0,50);
  const list=$('event-list'); list.replaceChildren();
  for (const e of events) {
    const li=document.createElement('li'), time=document.createElement('time'), content=document.createElement('div');
    time.dateTime=e.time; time.textContent=new Date(e.time).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
    const title=document.createElement('strong'), detail=document.createElement('p');
    title.textContent=e.title; detail.textContent=e.detail; content.append(title,detail); li.append(time,content); list.append(li);
  }
  $('export').disabled=false;
}
function error(message) { $('error').textContent=message; $('error').hidden=!message; }
function controls() {
  $('start').disabled=running || recording.finalizing || !ready || (source!=='camera' && !$('upload').files.length);
  $('sample').disabled=!ready || running || recording.finalizing;
  $('stop').disabled=!running; $('confidence').disabled=running;
  $('precision-filter').disabled=running;$('strict-filter').disabled=running;
  $('record-video').disabled=running || recording.finalizing || !recording.supported;
  $('start').textContent=source==='camera'?'Start camera':source==='video'?'Play & detect':'Analyze image';
}
function stop(reason='', record=true) {
  const wasRunning=running; running=false; epoch++; controller?.abort(); controller=null;
  if(frameHandle!==null)video.cancelVideoFrameCallback?.(frameHandle);
  frameHandle=null;clearTimeout(fallbackTimer);fallbackTimer=null;
  if (stream) {stream.getTracks().forEach(t=>t.stop());stream=null;}
  video.pause();
  recording.stop(reason || 'Stopped early',mode==='camera' || (mode==='video' && video.ended));
  if (wasRunning) {
    $('source-status').textContent='● Stopped'; $('source-status').className='chip';
    $('feed-caption').textContent=reason || 'Stopped · last frame retained';
    if (record) log('Monitoring stopped',reason || 'Last analyzed frame retained.');
  }
  controls();
}
function resetState() {
  boxes=[];frames=0;lastVideoTime=-1;frameTimes=[];lastResultAt=0;hasFrame=false;
  $('download-image').disabled=true;
  $('frame-count').textContent='0';$('fire-count').textContent='0';$('smoke-count').textContent='0';
  $('top-confidence').textContent='—';$('latency').textContent='Waiting for a source';
  $('processed-rate').textContent='Inference rate —';$('frame-age').textContent='Waiting for live frames';
}
function begin(kind, label) {
  stop('',false);resetState();error('');mode=kind;running=true;
  inputName=label;
  $('source-status').textContent='● '+label;
  $('source-status').className='chip ready';
  $('feed-caption').textContent='Local inference · '+label;
  $('confidence-caption').textContent='Raw model score, not accuracy';
  log('Source started',label);controls();
  return epoch;
}
function accept(detections, elapsed) {
  boxes=detections;frames++;hasFrame=true;$('download-image').disabled=false;
  lastResultAt=performance.now();frameTimes.push(lastResultAt);frameTimes=frameTimes.filter(t=>lastResultAt-t<2000);
  const fire=boxes.filter(d=>d.label==='fire'),smoke=boxes.filter(d=>d.label==='smoke');
  $('fire-count').textContent=fire.length; $('smoke-count').textContent=smoke.length;
  $('top-confidence').textContent=boxes.length?Math.round(Math.max(...boxes.map(d=>d.confidence))*100)+'%':'—';
  $('frame-count').textContent=frames;
  $('latency').textContent=`Latest inference · ${elapsed} ms`;
  $('processed-rate').textContent=mode==='image'?'Single image':frameTimes.length>1?`Inference rate · ${((frameTimes.length-1)*1000/(frameTimes.at(-1)-frameTimes[0])).toFixed(1)} fps`:'Measuring inference rate…';
  if(frames===1)updateDownloads();
}
function fit(w,h) {
  const display=Math.min(1280/w,720/h,1),analysis=Math.min(640/w,480/h,1);
  feed.width=Math.round(w*display);feed.height=Math.round(h*display);
  capture.width=Math.round(w*analysis);capture.height=Math.round(h*analysis);
}
function overlay() {
  for (const d of boxes) {
    const [x1,y1,x2,y2]=d.box, color=d.label==='fire'?'#ffc077':'#8dd8ff';
    const x=x1*feed.width,y=y1*feed.height,w=(x2-x1)*feed.width,h=(y2-y1)*feed.height;
    fc.strokeStyle=color;fc.lineWidth=3;fc.strokeRect(x,y,w,h);fc.font='bold 14px Segoe UI';
    const text=`${d.label} ${Math.round(d.confidence*100)}%`,tw=fc.measureText(text).width+12;
    const left=Math.max(0,Math.min(x,feed.width-tw)),top=Math.max(0,y-24);
    fc.fillStyle='#101719';fc.fillRect(left,top,tw,23);fc.fillStyle=color;fc.fillText(text,left+6,top+16);
  }
}
async function inferOnce(target, token) {
  cc.drawImage(target,0,0,capture.width,capture.height);
  const blob=await new Promise(resolve=>capture.toBlob(resolve,'image/jpeg',.85));
  if (!running || token!==epoch) return;
  controller=new AbortController();
  const response=await fetch(`/api/detections?confidence=${$('confidence').value}`,{method:'POST',headers:{'Content-Type':'image/jpeg'},body:blob,signal:controller.signal});
  const data=await response.json();
  if (!response.ok) throw new Error(data.error || 'Detection failed.');
  if (!running || token!==epoch) return;
  accept(data.detections,data.elapsedMs);
  if (mode==='image') {fc.drawImage(image,0,0,feed.width,feed.height);overlay();}
}
function scheduleFrame(token) {
  if(!running || token!==epoch)return;
  if(video.requestVideoFrameCallback)frameHandle=video.requestVideoFrameCallback((now,metadata)=>{frameHandle=null;monitor(token,metadata.mediaTime);});
  else fallbackTimer=setTimeout(()=>monitor(token,video.currentTime),16);
}
async function monitor(token, mediaTime) {
  try {
    if (!running || epoch!==token) return;
    if (video.ended) {stop('Video ended · last evidence retained');return;}
    if (!video.paused && video.readyState>=2 && mediaTime!==lastVideoTime) {
      lastVideoTime=mediaTime;await inferOnce(video,token);
    }
    scheduleFrame(token);
  } catch(e) {if(e.name!=='AbortError' && token===epoch){stop('Input or inference error');error(e.message);}}
}
async function openImage(url, label) {
  const token=begin('image',label);
  try {
    const next=new Image();next.src=url;await next.decode();
    if (!running || token!==epoch) return;
    if (next.naturalWidth*next.naturalHeight>20_000_000) throw new Error('Choose an image smaller than 20 megapixels.');
    image=next;fit(image.naturalWidth,image.naturalHeight);fc.drawImage(image,0,0,feed.width,feed.height);
    $('file-info').textContent=`${label} · ${image.naturalWidth} × ${image.naturalHeight} pixels`;
    await inferOnce(image,token);
    if (token!==epoch) return;
    running=false;$('source-status').textContent='● Image analyzed';$('source-status').className='chip ready';
    $('feed-caption').textContent='Single image · model detections';$('frame-age').textContent='Image analyzed · ready to download';
    log('Image analyzed',`${boxes.length} detections in the selected image.`);controls();updateDownloads();
  } catch(e) {if(e.name!=='AbortError' && token===epoch){stop('Image analysis failed');error(e.message);}}
}
async function start() {
  error('');
  if (source==='image') {
    const file=$('upload').files[0];if(!file)return;
    if(file.size>20*1024*1024){error('Choose an image smaller than 20 MB.');return;}
    if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=URL.createObjectURL(file);await openImage(objectUrl,file.name);return;
  }
  const token=begin(source,source==='camera'?'Camera live':$('upload').files[0]?.name || 'Video file');
  try {
    if(source==='camera') {
      if(!navigator.mediaDevices?.getUserMedia) throw new Error('Camera access needs localhost in Chrome or Edge.');
      const requested=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:960},height:{ideal:540}},audio:false});
      if(token!==epoch || !running){requested.getTracks().forEach(t=>t.stop());return;}
      stream=requested;video.srcObject=stream;
      stream.getVideoTracks()[0].addEventListener('ended',()=>{if(running && token===epoch){stop('Camera disconnected');error('Camera disconnected. The last analyzed frame is retained.');}});
    } else {
      const file=$('upload').files[0];if(!file)throw new Error('Choose a video first.');
      if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=URL.createObjectURL(file);video.srcObject=null;video.src=objectUrl;
    }
    await video.play();
    if(token!==epoch || !running)return;
    fit(video.videoWidth,video.videoHeight);
    fc.drawImage(video,0,0,feed.width,feed.height);
    $('file-info').textContent=`${inputName} · ${video.videoWidth} × ${video.videoHeight}${mode==='video'?' · '+clock(video.duration):' pixels'}`;
    if($('record-video').checked){
      try{recording.start(inputName);}catch(e){error(e.message);}
    }
    scheduleFrame(token);
  } catch(e) {if(token===epoch){stop('Could not open source');error(e.name==='NotAllowedError'?'Camera permission was denied. Allow it in your browser or use a video/image.':e.message);}}
}
for(const tab of document.querySelectorAll('[data-source]')) tab.addEventListener('click',()=>{
  stop('Source changed');source=tab.dataset.source;video.srcObject=null;video.removeAttribute('src');
  document.querySelectorAll('[data-source]').forEach(t=>t.setAttribute('aria-pressed',String(t===tab)));
  $('upload').hidden=source==='camera';$('upload-label').hidden=source==='camera';
  $('upload').accept=source==='video'?'video/*':'image/jpeg,image/png,image/webp';$('upload').value='';
  $('source-hint').textContent=source==='camera'?'Start your camera to detect fire and smoke live. Your browser will ask for camera permission.':source==='video'?'Choose a video, then select Play & detect. Recording saves the annotated playback.':'Choose an image, then select Analyze image to create a downloadable result.';
  $('file-help').hidden=source==='camera';$('file-help').textContent=source==='video'?'MP4 (H.264) or WebM. Playback support depends on your browser.':'JPEG, PNG or WebP · Maximum 20 MB and 20 megapixels.';
  $('upload-label').textContent=source==='video'?'Upload a video':'Upload an image';
  $('file-info').textContent=source==='camera'?'Camera inactive':'No file selected';
  $('record-option').hidden=source==='image';$('record-video').checked=source==='video' && recording.supported;
  controls();updateDownloads();
});
$('upload').addEventListener('change',()=>{
  stop('File selection changed');const file=$('upload').files[0];
  $('file-info').textContent=file?`${file.name} · ${fileSize(file.size)}`:'No file selected';
  error('');controls();
});
video.addEventListener('ended',()=>{if(running && mode==='video')stop('Video ended · last evidence retained');});
$('start').addEventListener('click',start);$('stop').addEventListener('click',()=>stop('Stopped by user · last evidence retained'));
$('sample').addEventListener('click',()=>openImage('/sample.jpg','Included held-out sample'));
function updateFilter(){
  const value=Number($('confidence').value);$('confidence-value').textContent=Math.round(value*100)+'%';
  $('confidence').setAttribute('aria-valuetext',`${Math.round(value*100)} percent minimum score`);
  $('filter-note').textContent=value>=.9?'90%+ filter hides lower-score detections and can miss real fire or smoke. A high score does not guarantee correctness.':'Higher thresholds reduce false detections but also miss more objects. Score is model confidence, not measured accuracy.';
}
$('confidence').addEventListener('input',updateFilter);
$('precision-filter').addEventListener('click',()=>{$('confidence').value='.5';updateFilter();});
$('strict-filter').addEventListener('click',()=>{$('confidence').value='.9';updateFilter();});
updateFilter();
$('export').addEventListener('click',()=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify({events},null,2)],{type:'application/json'}));a.href=url;a.download='firesense-events.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('download-image').addEventListener('click',()=>{
  if(!hasFrame)return;
  const filename=outputName(inputName,'png');
  feed.toBlob(blob=>{
    if(!blob){error('Image export failed. Try processing the image again.');return;}
    downloadBlob(blob,filename);log('Image downloaded','Annotated PNG at preview resolution.');
  },'image/png');
});
$('download-video').addEventListener('click',()=>{
  if(!recording.clip || recording.busy)return;
  downloadBlob(recording.clip.blob,recording.clip.name);log('Video downloaded',recording.clip.complete?'Annotated WebM recording, without audio.':'Partial annotated WebM recording, without audio.');
});
function updateDownloads(){
  $('download-video').disabled=recording.busy || !recording.clip;
  $('download-image').disabled=!hasFrame;
  $('download-status').textContent=recording.finalizing?'Finalizing your video…':recording.busy?'Recording annotated preview. Stop playback to prepare the download.':recording.clip?`${recording.clip.complete?'Video ready':'Partial video ready'} · ${fileSize(recording.clip.blob.size)} · ${recording.clip.name}${recording.clip.complete?'':' · '+recording.clip.reason}`:hasFrame?'Image ready to download. Enable recording before starting a video to save a clip.':'Process an image or start monitoring to enable image download.';
  controls();
}
function fileSize(bytes){return bytes<1024*1024?`${Math.max(1,Math.round(bytes/1024))} KB`:`${(bytes/1024/1024).toFixed(1)} MB`;}
function clock(seconds){
  if(!Number.isFinite(seconds))return '—';
  return `${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;
}
if(!recording.supported)$('record-support').textContent='Video recording is not supported here. Use Chrome or Edge. Image downloads remain available.';
window.addEventListener('pagehide',()=>stop('',false));

let lastUi=0;
function animate(now) {
  if(running && (mode==='camera'||mode==='video') && video.readyState>=2){
    fc.drawImage(video,0,0,feed.width,feed.height);if(now-lastResultAt<750)overlay();
  }
  if(now-lastUi>100){
    lastUi=now;
    if(lastResultAt && running)$('frame-age').textContent=`Overlay age · ${Math.round(now-lastResultAt)} ms${now-lastResultAt>=750?' · updating…':''}`;
    $('video-progress').value=mode==='video' && Number.isFinite(video.duration) && video.duration>0?video.currentTime/video.duration:0;
    $('video-time').textContent=mode==='video'?`${clock(video.currentTime)} / ${clock(video.duration)}`:mode==='camera' && running?'Camera live':mode==='image'?'Still image':'No video playing';
  }
  requestAnimationFrame(animate);
}requestAnimationFrame(animate);
async function status() {
  try {
    const response=await fetch('/api/status');if(!response.ok)throw new Error('Server unavailable');const data=await response.json();ready=data.state==='ready';
    const modelText=ready?`● Detector ready · ${data.device==='cpu'?'CPU':'GPU'}`:data.state==='error'?'● Detector unavailable':'● Loading detector';
    if($('model-status').textContent!==modelText)$('model-status').textContent=modelText;
    $('model-status').className='chip '+(ready?'ready':'');
    $('model-name').textContent=data.model;$('benchmark-map').textContent=data.testMap50==null?'—':Number(data.testMap50).toFixed(2);
    if(data.state==='error')error(data.error);controls();
  } catch(e){ready=false;$('model-status').textContent='● Server disconnected';$('model-status').className='chip';if(running){stop('Server disconnected');error('Server disconnected. Restart dashboard.py to reconnect.');}controls();}
  setTimeout(status,2500);
}status();controls();
