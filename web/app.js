const $ = id => document.getElementById(id);
const feed = $('feed'), fc = feed.getContext('2d');
const video = $('video'), capture = $('capture'), cc = capture.getContext('2d');
let ready=false, source='camera', mode='idle', running=false, stream=null, image=null, objectUrl=null;
let boxes=[], frames=0, epoch=0, controller=null, events=[], lastVideoTime=-1;
let frameHandle=null, fallbackTimer=null, frameTimes=[], lastResultAt=0;
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
  $('start').disabled=running || !ready || (source!=='camera' && !$('upload').files.length);
  $('sample').disabled=!ready || running;
  $('stop').disabled=!running; $('confidence').disabled=running;
  $('start').textContent=source==='camera'?'Start camera':source==='video'?'Play & detect':'Analyze image';
}
function stop(reason='', record=true) {
  const wasRunning=running; running=false; epoch++; controller?.abort(); controller=null;
  if(frameHandle!==null)video.cancelVideoFrameCallback?.(frameHandle);
  frameHandle=null;clearTimeout(fallbackTimer);fallbackTimer=null;
  if (stream) {stream.getTracks().forEach(t=>t.stop());stream=null;}
  video.pause();
  if (wasRunning) {
    $('source-status').textContent='● Stopped'; $('source-status').className='chip';
    $('feed-caption').textContent=reason || 'Stopped · last frame retained';
    if (record) log('Monitoring stopped',reason || 'Last analyzed frame retained.');
  }
  controls();
}
function resetState() {
  boxes=[];frames=0;lastVideoTime=-1;frameTimes=[];lastResultAt=0;
  $('frame-count').textContent='0';$('fire-count').textContent='0';$('smoke-count').textContent='0';
  $('top-confidence').textContent='—';$('latency').textContent='Waiting for a source';
  $('processed-rate').textContent='Inference rate —';$('frame-age').textContent='Waiting for live frames';
}
function begin(kind, label) {
  stop('',false);resetState();error('');mode=kind;running=true;
  $('source-status').textContent='● '+label;
  $('source-status').className='chip ready';
  $('feed-caption').textContent='Local inference · '+label;
  $('confidence-caption').textContent='Detector output, not event risk';
  log('Source started',label);controls();
  return epoch;
}
function accept(detections, elapsed) {
  boxes=detections;frames++;
  lastResultAt=performance.now();frameTimes.push(lastResultAt);frameTimes=frameTimes.filter(t=>lastResultAt-t<2000);
  const fire=boxes.filter(d=>d.label==='fire'),smoke=boxes.filter(d=>d.label==='smoke');
  $('fire-count').textContent=fire.length; $('smoke-count').textContent=smoke.length;
  $('top-confidence').textContent=boxes.length?Math.round(Math.max(...boxes.map(d=>d.confidence))*100)+'%':'—';
  $('frame-count').textContent=frames;
  $('latency').textContent=`Latest inference · ${elapsed} ms`;
  $('processed-rate').textContent=mode==='image'?'Single image':frameTimes.length>1?`Inference rate · ${((frameTimes.length-1)*1000/(frameTimes.at(-1)-frameTimes[0])).toFixed(1)} fps`:'Measuring inference rate…';

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
    await inferOnce(image,token);
    if (token!==epoch) return;
    running=false;$('source-status').textContent='● Image analyzed';$('source-status').className='chip ready';
    $('feed-caption').textContent='Single image · model detections';log('Image analyzed',`${boxes.length} detections in the selected image.`);controls();
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
    fit(video.videoWidth,video.videoHeight);scheduleFrame(token);
  } catch(e) {if(token===epoch){stop('Could not open source');error(e.name==='NotAllowedError'?'Camera permission was denied. Allow it in your browser or use a video/image.':e.message);}}
}
for(const tab of document.querySelectorAll('[data-source]')) tab.addEventListener('click',()=>{
  stop('Source changed');source=tab.dataset.source;video.srcObject=null;video.removeAttribute('src');
  document.querySelectorAll('[data-source]').forEach(t=>t.setAttribute('aria-pressed',String(t===tab)));
  $('upload').hidden=source==='camera';$('upload-label').hidden=source==='camera';
  $('upload').accept=source==='video'?'video/*':'image/jpeg,image/png,image/webp';$('upload').value='';
  $('source-hint').hidden=source!=='camera';$('upload-label').textContent=source==='video'?'Choose a local video (decoded in your browser)':'Choose a JPEG, PNG or WebP image';
  controls();
});
$('upload').addEventListener('change',()=>{stop('File selection changed');controls();});
video.addEventListener('ended',()=>{if(running && mode==='video')stop('Video ended · last evidence retained');});
$('start').addEventListener('click',start);$('stop').addEventListener('click',()=>stop('Stopped by user · last evidence retained'));
$('sample').addEventListener('click',()=>openImage('/sample.jpg','Included held-out sample'));
$('confidence').addEventListener('input',()=>{$('confidence-value').textContent=Number($('confidence').value).toFixed(2);});
$('export').addEventListener('click',()=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify({events},null,2)],{type:'application/json'}));a.href=url;a.download='firesense-events.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
window.addEventListener('pagehide',()=>stop('',false));

let lastUi=0;
function animate(now) {
  if(running && (mode==='camera'||mode==='video') && video.readyState>=2){
    fc.drawImage(video,0,0,feed.width,feed.height);if(now-lastResultAt<750)overlay();
  }
  if(now-lastUi>100){
    lastUi=now;
    if(lastResultAt && running)$('frame-age').textContent=`Overlay age · ${Math.round(now-lastResultAt)} ms${now-lastResultAt>=750?' · updating…':''}`;
  }
  requestAnimationFrame(animate);
}requestAnimationFrame(animate);
async function status() {
  try {
    const response=await fetch('/api/status');if(!response.ok)throw new Error('Server unavailable');const data=await response.json();ready=data.state==='ready';
    $('model-status').textContent=ready?`● Detector ready · ${data.device==='cpu'?'CPU':'GPU'}`:data.state==='error'?'● Detector unavailable':'● Loading detector';
    $('model-status').className='chip '+(ready?'ready':'');
    if(data.state==='error')error(data.error);controls();
  } catch(e){ready=false;$('model-status').textContent='● Server disconnected';$('model-status').className='chip';if(running){stop('Server disconnected');error('Server disconnected. Restart dashboard.py to reconnect.');}controls();}
  setTimeout(status,2500);
}status();controls();
