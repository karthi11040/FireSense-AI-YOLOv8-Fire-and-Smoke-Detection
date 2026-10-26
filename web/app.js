import {Simulation} from './simulation.mjs';
const $ = id => document.getElementById(id);
const sim = new Simulation(), feed = $('feed'), fc = feed.getContext('2d'), room = $('room'), rc = room.getContext('2d');
const video = $('video'), capture = $('capture'), cc = capture.getContext('2d');
let ready=false, source='camera', mode='idle', running=false, stream=null, image=null, objectUrl=null;
let boxes=[], frames=0, epoch=0, controller=null, incident=null, events=[], demoStart=0, lastVideoTime=-1;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

function log(title, detail) {
  const entry={time:new Date().toISOString(),title,detail,source:mode,incidentId:incident,simulationOnly:true};
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
  if (stream) {stream.getTracks().forEach(t=>t.stop());stream=null;}
  video.pause();
  if (wasRunning) {
    $('source-status').textContent='● Stopped'; $('source-status').className='chip';
    $('feed-caption').textContent=reason || 'Stopped · last frame retained';
    if (record) log('Monitoring stopped',reason || 'Last evidence retained; incident remains latched until reset.');
  }
  controls();
}
function resetState() {
  sim.reset(); boxes=[];frames=0;incident=null;lastVideoTime=-1;
  $('frame-count').textContent='0';$('fire-count').textContent='0';$('smoke-count').textContent='0';
  $('top-confidence').textContent='—';$('latency').textContent='Waiting for a source';
}
function begin(kind, label) {
  stop('',false);resetState();error('');mode=kind;running=true;$('empty').hidden=true;
  $('source-status').textContent=kind==='demo'?'● Demo · scripted':'● '+label;
  $('source-status').className='chip '+(kind==='demo'?'demo':'ready');
  $('feed-caption').textContent=kind==='demo'?'Scripted detections · no AI inference':'Local inference · '+label;
  $('confidence-caption').textContent=kind==='demo'?'Scripted demo confidence':'Detector output, not event risk';
  log('Source started',label+(kind==='demo'?' — scripted detections, not model results.':''));controls();
  return epoch;
}
function accept(detections, elapsed) {
  boxes=detections;frames++;
  const fire=boxes.filter(d=>d.label==='fire'),smoke=boxes.filter(d=>d.label==='smoke');
  $('fire-count').textContent=fire.length; $('smoke-count').textContent=smoke.length;
  $('top-confidence').textContent=boxes.length?Math.round(Math.max(...boxes.map(d=>d.confidence))*100)+'%':'—';
  $('frame-count').textContent=frames;
  $('latency').textContent=mode==='demo'?'Scripted demo frames':`Latest inference · ${elapsed} ms`;
  if (sim.observe(fire.length>0,smoke.length>0)) {
    incident=crypto.randomUUID();
    log('Fire confirmed',`3 of 5 analyzed frames positive. Incident ${incident.slice(0,8)}. Confirmation is not emergency certification.`);
    if (sim.sprinkler) log('Virtual sprinkler opened','Toy response simulation started. No physical actuation.');
  }
}
function fit(w,h) {const scale=Math.min(960/w,720/h,1);feed.width=capture.width=Math.round(w*scale);feed.height=capture.height=Math.round(h*scale);}
function overlay() {
  for (const d of boxes) {
    const [x1,y1,x2,y2]=d.box, color=d.label==='fire'?'#ffad72':'#80caff';
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
async function monitor(token) {
  try {
    if (!running || epoch!==token) return;
    if (video.ended) {stop('Video ended · last evidence retained');return;}
    if (!video.paused && video.readyState>=2 && video.currentTime!==lastVideoTime) {
      lastVideoTime=video.currentTime;await inferOnce(video,token);
    }
    if (running && epoch===token) setTimeout(()=>monitor(token),350);
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
    $('feed-caption').textContent='Single image · no temporal confirmation';log('Image analyzed','One image cannot satisfy the 3-frame confirmation gate.');controls();
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
      stream.getVideoTracks()[0].addEventListener('ended',()=>{if(running && token===epoch){stop('Camera disconnected');error('Camera disconnected. The last incident state is retained.');}});
    } else {
      const file=$('upload').files[0];if(!file)throw new Error('Choose a video first.');
      if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=URL.createObjectURL(file);video.srcObject=null;video.src=objectUrl;
    }
    await video.play();
    if(token!==epoch || !running)return;
    fit(video.videoWidth,video.videoHeight);monitor(token);
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
$('start').addEventListener('click',start);$('stop').addEventListener('click',()=>stop('Stopped by user · last evidence retained'));
$('sample').addEventListener('click',()=>openImage('/sample.jpg','Included held-out sample'));
$('confidence').addEventListener('input',()=>{$('confidence-value').textContent=Number($('confidence').value).toFixed(2);});
$('automatic').addEventListener('change',()=>{sim.auto=$('automatic').checked;log('Virtual response setting',sim.auto?'Automatic virtual water enabled for the next confirmation.':'Manual virtual water mode.');});
$('water').addEventListener('click',()=>{sim.sprinkler=!sim.sprinkler;log('Virtual sprinkler '+(sim.sprinkler?'opened':'closed'),'Manual simulation action. No physical actuation.');});
$('reset').addEventListener('click',()=>{stop('',false);resetState();mode='idle';image=null;fc.clearRect(0,0,feed.width,feed.height);$('empty').hidden=false;$('source-status').textContent='● Idle';$('source-status').className='chip';$('feed-caption').textContent='Session reset · no source connected';error('');log('Session reset','Incident latch, evidence window and toy intensity cleared.');controls();});
$('export').addEventListener('click',()=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify({simulationOnly:true,policy:'3-of-5 fire-positive analyzed frames',events},null,2)],{type:'application/json'}));a.href=url;a.download='firesense-events.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('demo').addEventListener('click',()=>{
  begin('demo','Virtual response demo');fit(960,540);demoStart=performance.now();const token=epoch;
  const sample=()=>{
    if(!running || token!==epoch)return;
    const active=(performance.now()-demoStart)>900;
    accept(active?[{label:'fire',confidence:.94,box:[.57,.46,.72,.84]},{label:'smoke',confidence:.83,box:[.54,.21,.76,.5]}]:[],0);
    setTimeout(sample,400);
  };sample();
});
window.addEventListener('pagehide',()=>stop('',false));

function drawRoom(ctx,w,h,level,water,t) {
  ctx.clearRect(0,0,w,h);ctx.fillStyle='#141c1f';ctx.fillRect(0,0,w,h);
  ctx.strokeStyle='#394c52';ctx.lineWidth=1.2;
  const x=w*.13,y=h*.19,rw=w*.74,rh=h*.63;
  ctx.fillStyle='#1a272b';ctx.fillRect(x,y,rw,rh);ctx.strokeRect(x,y,rw,rh);
  ctx.beginPath();ctx.moveTo(x,y+rh*.68);ctx.lineTo(x+rw,y+rh*.68);ctx.moveTo(x,y+rh);ctx.lineTo(w*.03,h*.94);ctx.moveTo(x+rw,y+rh);ctx.lineTo(w*.97,h*.94);ctx.moveTo(w*.03,h*.94);ctx.lineTo(w*.97,h*.94);ctx.stroke();
  for(let i=1;i<6;i++){ctx.beginPath();ctx.moveTo(x+rw*i/6,y+rh*.68);ctx.lineTo(w*(i/6),h*.94);ctx.stroke();}
  ctx.strokeStyle=water?'#73d6c3':'#718b8c';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(w*.09,h*.27);ctx.lineTo(w*.91,h*.27);ctx.stroke();
  for(const px of [.28,.5,.72]) {
    ctx.beginPath();ctx.moveTo(w*px,h*.27);ctx.lineTo(w*px,h*.34);ctx.stroke();
    ctx.fillStyle=water?'#73d6c3':'#718b8c';ctx.fillRect(w*px-7,h*.34,14,4);
    if(water)for(let i=0;i<18;i++){
      const f=((t*.65+i*.061)%1),side=Math.sin(i*23.1)*f*w*.15;
      ctx.strokeStyle=`rgba(115,214,223,${.65*(1-f)})`;ctx.lineWidth=1.3;ctx.beginPath();ctx.moveTo(w*px+side,h*.36+f*h*.48);ctx.lineTo(w*px+side-2,h*.36+f*h*.48+7);ctx.stroke();
    }
  }
  ctx.strokeStyle='#59747a';ctx.lineWidth=1;ctx.strokeRect(w*.2,h*.45,w*.18,h*.31);ctx.strokeRect(w*.74,h*.48,w*.08,h*.26);
  if(level>0) {
    const fx=w*.64,fy=h*.81,scale=Math.max(.15,level/100),fh=h*.36*scale,fw=w*.105*scale;
    const sway=reducedMotion?0:Math.sin(t*9)*fw*.15;
    ctx.fillStyle='#ff8d4d';ctx.beginPath();ctx.moveTo(fx-fw,fy);ctx.bezierCurveTo(fx-fw*1.5,fy-fh*.5,fx+sway,fy-fh*.7,fx,fy-fh);ctx.bezierCurveTo(fx+fw*.25,fy-fh*.5,fx+fw*1.7,fy-fh*.3,fx+fw,fy);ctx.closePath();ctx.fill();
    ctx.fillStyle='#ffd18b';ctx.beginPath();ctx.moveTo(fx-fw*.5,fy);ctx.quadraticCurveTo(fx-fw*.7,fy-fh*.3,fx,fy-fh*.58);ctx.quadraticCurveTo(fx+fw*.7,fy-fh*.15,fx+fw*.5,fy);ctx.fill();
    for(let i=0;i<5;i++){ctx.fillStyle=`rgba(154,171,176,${.10-i*.012})`;ctx.beginPath();ctx.ellipse(fx+Math.sin(t+i)*fw*.4,fy-fh-h*.03*i,fw*(.6+i*.13),h*.04,0,0,Math.PI*2);ctx.fill();}
  }
  ctx.fillStyle='#a7b4b8';ctx.font=`${Math.max(10,w*.019)}px Segoe UI`;ctx.fillText('VIRTUAL RESPONSE ZONE',w*.15,h*.14);
}
let previous=performance.now(),lastPaint=0;
function animate(now) {
  const dt=Math.min((now-previous)/1000,.1);previous=now;
  if(running)sim.tick(dt);
  if(now-lastPaint>33){
    lastPaint=now;const t=reducedMotion?0:now/1000;
    drawRoom(rc,room.width,room.height,sim.intensity,sim.sprinkler,t);
    if(running && mode==='demo'){drawRoom(fc,feed.width,feed.height,sim.fire?80:0,false,t);overlay();}
    else if(running && (mode==='camera'||mode==='video') && video.readyState>=2){fc.drawImage(video,0,0,feed.width,feed.height);overlay();}
    $('intensity').textContent=Math.round(sim.intensity);$('intensity-bar').value=sim.intensity;
    $('water-status').textContent=sim.sprinkler?'Open · virtual only':'Closed';
    $('incident-status').textContent=sim.confirmed?'Fire confirmed · latched':sim.fire?'Fire candidate':sim.smoke?'Smoke observed':'Awaiting evidence';
    $('incident-status').className=sim.confirmed?'confirmed':sim.fire?'candidate':sim.smoke?'smoke':'idle';
    $('gate-count').textContent=`${sim.history.filter(Boolean).length} / 5 fire-positive frames`;
    [...$('gate-dots').children].forEach((dot,i)=>dot.classList.toggle('positive',Boolean(sim.history[i])));
  }
  requestAnimationFrame(animate);
}requestAnimationFrame(animate);
async function status() {
  try {
    const response=await fetch('/api/status');if(!response.ok)throw new Error('Server unavailable');const data=await response.json();ready=data.state==='ready';
    $('model-status').textContent=ready?`● Detector ready · ${data.device==='cpu'?'CPU':'GPU'}`:data.state==='error'?'● Detector unavailable':'● Loading detector';
    $('model-status').className='chip '+(ready?'ready':'');
    if(data.state==='error')error(data.error);controls();
  } catch(e){ready=false;$('model-status').textContent='● Server disconnected';$('model-status').className='chip';if(running && mode!=='demo'){stop('Server disconnected');error('Server disconnected. Restart dashboard.py to reconnect.');}controls();}
  setTimeout(status,2500);
}status();controls();
