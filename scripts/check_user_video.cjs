// Run a supplied local video through the actual dashboard; retain raw API evidence.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
  const video=process.argv[2],tag=process.argv[3] || 'browser_check';
  if(!video || !/^[a-z0-9_-]+$/i.test(tag))throw Error('Provide a video path and a simple evidence tag');
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[],responses=[],pending=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('response',response=>{
      if(response.url().includes('/api/detections?'))pending.push((async()=>{
        const data=await response.json();responses.push({status:response.status(),...data});
      })());
    });
    await page.goto('http://localhost:8765');
    await page.waitForFunction(()=>!document.querySelector('#start').disabled,null,{timeout:180000});
    await page.getByRole('button',{name:'Video file',exact:true}).click();
    await page.locator('#upload').setInputFiles(video);
    await page.locator('#start').click();
    await page.getByText('● Stopped',{exact:true}).waitFor({timeout:90000});
    await Promise.all(pending);
    assert.ok(responses.length>0);assert.deepEqual(errors,[]);
    assert.ok(responses.every(r=>r.status===200));
    const positive=responses.filter(r=>r.detections.some(d=>d.label==='fire')).length;
    let downloadedVideo=null;
    if(process.argv.includes('--download')){
      await page.waitForFunction(()=>!document.querySelector('#download-video').disabled);
      const saved=page.waitForEvent('download');await page.locator('#download-video').click();
      const file=await saved;downloadedVideo=`evidence/user_video/${tag}.webm`;await file.saveAs(downloadedVideo);
      assert.ok(fs.statSync(downloadedVideo).size>1000);
    }
    const summary={file:video,model:await page.locator('#model-name').textContent(),
      minimumScore:Number(await page.locator('#confidence').inputValue()),processedFrames:responses.length,
      framesWithFire:positive,firePositiveFraction:positive/responses.length,downloadedVideo,pageErrors:errors,responses};
    fs.writeFileSync(`evidence/user_video/${tag}.json`,JSON.stringify(summary,null,2));
    await page.screenshot({path:`evidence/user_video/${tag}.png`,fullPage:true});
    console.log(JSON.stringify({...summary,responses:undefined},null,2));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
