// Optional browser QA: use an installed Playwright module via PLAYWRIGHT_MODULE.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');

(async () => {
  const browser = await chromium.launch({channel:'msedge',headless:true,args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream']});
  try {
    const context = await browser.newContext({viewport:{width:1440,height:1100},permissions:['camera']});
    const page = await context.newPage(), errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://localhost:8765');
    await page.getByRole('heading',{name:'Live monitoring.'}).waitFor();
    assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).colorScheme),'light');
    await page.getByRole('link',{name:'Skip to monitor'}).focus();
    assert.ok((await page.getByRole('link',{name:'Skip to monitor'}).boundingBox()).y>=0);
    await page.keyboard.press('Tab');
    await page.getByRole('button',{name:'Run simulation demo'}).click();
    await page.getByText('Fire confirmed · latched',{exact:true}).waitFor();
    assert.match(await page.locator('#water-status').innerText(),/Open/);
    await page.screenshot({path:'evidence/dashboard_desktop.png',fullPage:true});
    await page.getByRole('button',{name:'Stop',exact:true}).click();
    assert.match(await page.locator('#incident-status').innerText(),/latched/);
    await page.getByRole('button',{name:'Reset session'}).click();
    await page.getByText('Awaiting evidence',{exact:true}).waitFor();
    assert.equal(await page.locator('#incident-status').innerText(),'Awaiting evidence');
    await page.waitForFunction(()=>!document.querySelector('#sample').disabled,null,{timeout:180000});
    await page.getByRole('button',{name:/Try sample image/}).click();
    await page.getByText('● Image analyzed',{exact:true}).waitFor({timeout:60000});
    await page.getByText('Fire candidate',{exact:true}).waitFor();
    assert.ok(Number(await page.locator('#fire-count').innerText())>=1);
    assert.equal(await page.locator('#incident-status').innerText(),'Fire candidate');
    await page.screenshot({path:'evidence/dashboard_image.png',fullPage:true});
    await page.getByRole('button',{name:'Reset session'}).click();
    await page.getByRole('button',{name:'Start camera',exact:true}).click();
    await page.waitForFunction(()=>Number(document.querySelector('#frame-count').textContent)>=2,null,{timeout:60000});
    await page.getByRole('button',{name:'Stop',exact:true}).click();
    await page.getByRole('button',{name:'Image',exact:true}).click();
    await page.locator('#upload').setInputFiles(path.resolve('web/sample.jpg'));
    await page.getByRole('button',{name:'Analyze image',exact:true}).click();
    await page.getByText('● Image analyzed',{exact:true}).waitFor({timeout:60000});
    assert.ok(Number(await page.locator('#fire-count').innerText())>=1);
    const videoBytes=await page.evaluate(async()=>{
      const canvas=document.createElement('canvas');canvas.width=320;canvas.height=180;
      const ctx=canvas.getContext('2d'),stream=canvas.captureStream(5),parts=[];
      const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp8'});
      const done=new Promise(resolve=>{recorder.ondataavailable=e=>parts.push(e.data);recorder.onstop=resolve;});
      recorder.start();for(let i=0;i<10;i++){ctx.fillStyle=i%2?'#52443a':'#283d39';ctx.fillRect(0,0,320,180);await new Promise(r=>setTimeout(r,120));}
      recorder.stop();await done;stream.getTracks().forEach(t=>t.stop());return [...new Uint8Array(await new Blob(parts).arrayBuffer())];
    });
    await page.getByRole('button',{name:'Video file',exact:true}).click();
    await page.locator('#upload').setInputFiles({name:'qa-video.webm',mimeType:'video/webm',buffer:Buffer.from(videoBytes)});
    await page.getByRole('button',{name:'Play & detect',exact:true}).click();
    await page.waitForFunction(()=>Number(document.querySelector('#frame-count').textContent)>=1,null,{timeout:60000});
    await page.getByText('● Stopped',{exact:true}).waitFor({timeout:60000});
    const sampleResponse=await context.request.get('http://localhost:8765/sample-video.webm');
    assert.equal(sampleResponse.status(),200);
    assert.ok((await sampleResponse.body()).length>100000);
    await page.locator('#upload').setInputFiles(path.resolve('web/sample-video.webm'));
    await page.getByRole('button',{name:'Play & detect',exact:true}).click();
    await page.getByText('Fire confirmed · latched',{exact:true}).waitFor({timeout:25000});
    await page.getByRole('button',{name:'Stop',exact:true}).click();
    await page.getByRole('button',{name:'Run simulation demo'}).click();
    await page.getByText('Fire confirmed · latched',{exact:true}).waitFor();
    const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:/Export log/}).click();
    const download=await downloadPromise;await download.saveAs('evidence/dashboard_export.json');
    const log=JSON.parse(fs.readFileSync('evidence/dashboard_export.json','utf8'));assert.equal(log.simulationOnly,true);
    assert.ok(log.events.some(e=>e.title==='Fire confirmed'));
    for(const width of [320,768,1024,1440]){
      await page.setViewportSize({width,height:1000});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`Overflow at ${width}px`);
    }
    await page.setViewportSize({width:390,height:844});
    await page.keyboard.press('Control+Home');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.screenshot({path:'evidence/dashboard_mobile.png',fullPage:true});
    assert.deepEqual(errors,[]);
    const realtime=await context.newPage();
    let active=0,maxActive=0,requests=0;
    await realtime.route('**/api/detections?*',async route=>{
      active++;requests++;maxActive=Math.max(active,maxActive);
      await new Promise(resolve=>setTimeout(resolve,80));
      await route.fulfill({json:{detections:[],elapsedMs:80}});active--;
    });
    await realtime.goto('http://localhost:8765');
    await realtime.waitForFunction(()=>!document.querySelector('#start').disabled);
    await realtime.getByRole('button',{name:'Start camera',exact:true}).click();
    await realtime.waitForFunction(()=>Number(document.querySelector('#frame-count').textContent)>=1);
    const started=Date.now();
    await realtime.waitForFunction(()=>Number(document.querySelector('#frame-count').textContent)>=10,null,{timeout:3000});
    const tenFramesMs=Date.now()-started;
    assert.ok(tenFramesMs<2800,`Delayed frame pipeline: ${tenFramesMs} ms`);
    assert.equal(maxActive,1);
    await realtime.getByRole('button',{name:'Stop',exact:true}).click();
    await new Promise(resolve=>setTimeout(resolve,200));const stoppedRequests=requests;
    await new Promise(resolve=>setTimeout(resolve,400));assert.equal(requests,stoppedRequests);
    await realtime.close();
    fs.writeFileSync('evidence/dashboard_browser_check.json',JSON.stringify({demoConfirmation:true,latchedStop:true,reset:true,sampleInference:true,imageUpload:true,syntheticCamera:true,videoUpload:true,sampleVideoConfirmation:true,logExport:true,lightTheme:true,responsiveWidths:[320,768,1024,1440],mockedRealtime:{maxActive,tenFramesMs,noRequestsAfterStop:true},pageErrors:errors},null,2));
    console.log('PASS: demo, gate, stop/reset, model inference, uploads, synthetic webcam, log export, mobile layout.');
    await page.getByRole('button',{name:'Stop',exact:true}).click();
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
