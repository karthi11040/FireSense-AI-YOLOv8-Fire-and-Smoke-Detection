// Browser-compatible WebM from held-out stills, for UI testing, not event evaluation.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs');
(async()=>{
  const sources=['test_1118.jpg','test_10.jpg','test_410.jpg'];
  const images=sources.map(name=>fs.readFileSync(`data/prepared/test/images/${name}`).toString('base64'));
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try {
    const page=await browser.newPage();
    const bytes=await page.evaluate(async images=>{
      const pictures=await Promise.all(images.map(data=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=reject;im.src='data:image/jpeg;base64,'+data;})));
      const canvas=document.createElement('canvas');canvas.width=960;canvas.height=540;
      const ctx=canvas.getContext('2d'),stream=canvas.captureStream(10),parts=[];
      const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp8',videoBitsPerSecond:1200000});
      const done=new Promise(resolve=>{recorder.ondataavailable=e=>parts.push(e.data);recorder.onstop=resolve;});
      recorder.start(1000);const start=performance.now();
      while(performance.now()-start<20000){
        const elapsed=(performance.now()-start)/1000,index=elapsed<4?0:elapsed<12?1:2,im=pictures[index];
        ctx.fillStyle='#111827';ctx.fillRect(0,0,960,540);
        const scale=Math.min(960/im.width,504/im.height),w=im.width*scale,h=im.height*scale;
        ctx.drawImage(im,(960-w)/2,(504-h)/2,w,h);
        ctx.fillStyle='#ffffff';ctx.font='16px Arial';ctx.fillText('FIRESENSE TEST SEQUENCE · HELD-OUT STILL IMAGES · '+Math.floor(elapsed)+' / 20 s',20,528);
        await new Promise(resolve=>setTimeout(resolve,100));
      }
      recorder.stop();await done;stream.getTracks().forEach(t=>t.stop());
      return [...new Uint8Array(await new Blob(parts,{type:'video/webm'}).arrayBuffer())];
    },images);
    fs.writeFileSync('web/sample-video.webm',Buffer.from(bytes));
    fs.writeFileSync('evidence/sample_video_provenance.json',JSON.stringify({sources,seconds:20,format:'WebM / VP8',license:'Home Fire Dataset CC BY-NC 4.0; Peng and Kim, 2025',purpose:'Generated from still images for upload/inference/UI testing; not real incident footage or an event benchmark'},null,2));
    console.log('Created web/sample-video.webm');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
