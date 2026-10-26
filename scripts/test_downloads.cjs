const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');

(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true,args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream']});
  const directory='evidence/download_checks';fs.mkdirSync(directory,{recursive:true});
  try{
    const context=await browser.newContext({viewport:{width:1440,height:1100},permissions:['camera']});
    const page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://localhost:8765');
    assert.equal(await page.locator('#download-image').isDisabled(),true);
    assert.equal(await page.locator('#download-video').isDisabled(),true);
    await page.waitForFunction(()=>!document.querySelector('#sample').disabled,null,{timeout:180000});
    await page.locator('#sample').click();
    await page.getByText('● Image analyzed',{exact:true}).waitFor();
    assert.ok(Number(await page.locator('#fire-count').innerText())>0);
    const pngPromise=page.waitForEvent('download');await page.locator('#download-image').click();
    const png=await pngPromise;assert.match(png.suggestedFilename(),/-annotated\.png$/);
    const pngFile=path.join(directory,'annotated.png');await png.saveAs(pngFile);
    const pngCheck=await page.evaluate(async encoded=>{
      const result=new Image(),source=new Image();result.src='data:image/png;base64,'+encoded;source.src='/sample.jpg';
      await Promise.all([result.decode(),source.decode()]);
      const a=document.createElement('canvas'),b=document.createElement('canvas');a.width=b.width=result.width;a.height=b.height=result.height;
      a.getContext('2d').drawImage(result,0,0);b.getContext('2d').drawImage(source,0,0,b.width,b.height);
      const actual=a.getContext('2d').getImageData(0,0,a.width,a.height).data,raw=b.getContext('2d').getImageData(0,0,b.width,b.height).data;
      let changed=0;for(let i=0;i<actual.length;i+=4)if(Math.abs(actual[i]-raw[i])+Math.abs(actual[i+1]-raw[i+1])+Math.abs(actual[i+2]-raw[i+2])>30)changed++;
      return {width:a.width,height:a.height,changed};
    },fs.readFileSync(pngFile).toString('base64'));
    assert.ok(pngCheck.changed>200,'PNG is missing expected annotation pixels');
    const videoBytes=await page.evaluate(async()=>{
      const image=new Image();image.src='/sample.jpg';await image.decode();
      const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
      const ctx=canvas.getContext('2d'),stream=canvas.captureStream(10),chunks=[];
      const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp8'});
      const complete=new Promise(resolve=>{recorder.ondataavailable=e=>chunks.push(e.data);recorder.onstop=resolve;});
      recorder.start();
      for(let i=0;i<30;i++){ctx.drawImage(image,0,0);ctx.fillStyle='#fff';ctx.fillRect(i,canvas.height-2,2,2);await new Promise(resolve=>setTimeout(resolve,100));}
      recorder.stop();await complete;stream.getTracks().forEach(t=>t.stop());
      return [...new Uint8Array(await new Blob(chunks).arrayBuffer())];
    });
    const videoFile={name:'fire-fixture.webm',mimeType:'video/webm',buffer:Buffer.from(videoBytes)};
    await page.getByRole('button',{name:'Video file',exact:true}).click();
    assert.equal(await page.locator('#record-video').isChecked(),true);
    await page.locator('#upload').setInputFiles(videoFile);
    await page.locator('#start').click();
    await page.getByText('● Stopped',{exact:true}).waitFor({timeout:60000});
    await page.waitForFunction(()=>!document.querySelector('#download-video').disabled);
    assert.match(await page.locator('#download-status').innerText(),/Video ready/);
    const webmPromise=page.waitForEvent('download');await page.locator('#download-video').click();
    const webm=await webmPromise;assert.equal(webm.suggestedFilename(),'fire-fixture-annotated.webm');
    const webmFile=path.join(directory,'annotated.webm');await webm.saveAs(webmFile);
    assert.ok(fs.statSync(webmFile).size>1000);
    const webmCheck=await page.evaluate(async encoded=>{
      const video=document.createElement('video');video.muted=true;
      const bytes=Uint8Array.from(atob(encoded),character=>character.charCodeAt(0));
      const url=URL.createObjectURL(new Blob([bytes],{type:'video/webm'}));video.src=url;
      const ended=new Promise((resolve,reject)=>{video.onended=resolve;video.onerror=()=>reject(Error('Downloaded video cannot play'));});
      const start=performance.now();await video.play();await ended;
      const result={width:video.videoWidth,height:video.videoHeight,sourceSeconds:video.currentTime,playbackSeconds:(performance.now()-start)/1000};
      URL.revokeObjectURL(url);return result;
    },fs.readFileSync(webmFile).toString('base64'));
    assert.ok(webmCheck.width>0 && webmCheck.height>0);
    assert.ok(webmCheck.sourceSeconds>2 && webmCheck.sourceSeconds<5,'Recording has incorrect duration');
    assert.ok(Math.abs(webmCheck.sourceSeconds-webmCheck.playbackSeconds)<1,'Recording playback timing changed');
    await page.screenshot({path:path.join(directory,'desktop.png'),fullPage:true});
    await page.getByRole('button',{name:'Image',exact:true}).click();
    assert.equal(await page.locator('#download-video').isEnabled(),true,'Switching sources lost the completed recording');
    await page.locator('#upload').setInputFiles({name:'broken.png',mimeType:'image/png',buffer:Buffer.from('invalid image')});
    await page.locator('#start').click();await page.locator('#error').waitFor({state:'visible'});
    assert.equal(await page.locator('#download-video').isEnabled(),true);
    await page.getByRole('button',{name:'Video file',exact:true}).click();
    await page.locator('#upload').setInputFiles(videoFile);await page.locator('#start').click();
    await page.waitForFunction(()=>Number(document.querySelector('#frame-count').textContent)>=1);
    await page.locator('#stop').click();
    await page.waitForFunction(()=>!document.querySelector('#download-video').disabled);
    assert.match(await page.locator('#download-status').innerText(),/Partial video ready/);
    for(const width of [320,768,1024,1440]){
      await page.setViewportSize({width,height:1000});
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}`);
    }
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(directory,'mobile.png'),fullPage:true});
    await page.getByRole('link',{name:'Skip to monitor'}).focus();
    assert.ok((await page.getByRole('link',{name:'Skip to monitor'}).boundingBox()).y>=0);
    await page.getByRole('button',{name:'Live camera',exact:true}).click();
    assert.equal(await page.locator('#record-video').isChecked(),false);
    await page.locator('#record-video').check();await page.locator('#start').click();
    await page.waitForFunction(()=>Number(document.querySelector('#frame-count').textContent)>=2);
    await page.locator('#stop').click();
    await page.waitForFunction(()=>!document.querySelector('#download-video').disabled);
    assert.match(await page.locator('#download-status').innerText(),/Video ready/);
    const unsupported=await context.newPage();
    await unsupported.addInitScript(()=>{window.MediaRecorder=undefined;});
    await unsupported.goto('http://localhost:8765');
    assert.equal(await unsupported.locator('#record-video').isDisabled(),true);
    assert.match(await unsupported.locator('#record-support').innerText(),/not supported/);
    await unsupported.waitForFunction(()=>!document.querySelector('#sample').disabled);
    await unsupported.locator('#sample').click();
    await unsupported.getByText('● Image analyzed',{exact:true}).waitFor();
    assert.equal(await unsupported.locator('#download-image').isEnabled(),true);
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(directory,'browser_check.json'),JSON.stringify({pngCheck,webmCheck,videoDownload:true,syntheticCameraRecording:true,sourceSwitchPreservesClip:true,partialClip:true,invalidImageError:true,unsupportedRecorderFallback:true,widths:[320,768,1024,1440],keyboardSkip:true,pageErrors:errors},null,2));
    console.log('PASS: annotated PNG/WebM downloads, completion/partial state, source changes, errors, unsupported recording, responsive/keyboard checks.');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
