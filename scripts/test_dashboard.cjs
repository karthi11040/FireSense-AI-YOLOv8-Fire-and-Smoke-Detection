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
    await page.getByRole('button',{name:'Run simulation demo'}).click();
    await page.getByText('Fire confirmed · latched',{exact:true}).waitFor();
    const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:/Export log/}).click();
    const download=await downloadPromise;await download.saveAs('evidence/dashboard_export.json');
    const log=JSON.parse(fs.readFileSync('evidence/dashboard_export.json','utf8'));assert.equal(log.simulationOnly,true);
    assert.ok(log.events.some(e=>e.title==='Fire confirmed'));
    await page.setViewportSize({width:390,height:844});
    await page.keyboard.press('Control+Home');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.screenshot({path:'evidence/dashboard_mobile.png',fullPage:true});
    assert.deepEqual(errors,[]);
    fs.writeFileSync('evidence/dashboard_browser_check.json',JSON.stringify({demoConfirmation:true,latchedStop:true,reset:true,sampleInference:true,imageUpload:true,syntheticCamera:true,videoUpload:true,logExport:true,mobileNoOverflow:true,pageErrors:errors},null,2));
    console.log('PASS: demo, gate, stop/reset, model inference, uploads, synthetic webcam, log export, mobile layout.');
    await page.getByRole('button',{name:'Stop',exact:true}).click();
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
