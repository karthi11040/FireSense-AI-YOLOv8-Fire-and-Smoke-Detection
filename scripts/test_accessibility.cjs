const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    await page.addInitScript({content:fs.readFileSync('tmp/axe.min.js','utf8')});
    await page.goto('http://localhost:8765');
    const checks=[];
    for(const source of ['Live camera','Video file','Image']){
      await page.getByRole('button',{name:source,exact:true}).click();
      for(const width of [320,1440]){
        await page.setViewportSize({width,height:1000});
        const result=await page.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','best-practice']}}));
        checks.push({source,width,violations:result.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))});
      }
    }
    await page.waitForFunction(()=>!document.querySelector('#sample').disabled);
    for(let i=0;i<3;i++){
      await page.locator('#sample').click();await page.getByText('● Image analyzed',{exact:true}).waitFor();
    }
    const populated=await page.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','best-practice']}}));
    checks.push({source:'Populated image results and scrollable activity',width:1440,violations:populated.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))});
    fs.writeFileSync('evidence/download_checks/accessibility.json',JSON.stringify(checks,null,2));
    assert.ok(checks.every(c=>c.violations.length===0),JSON.stringify(checks.filter(c=>c.violations.length),null,2));
    console.log('PASS: axe WCAG A/AA and best-practice checks for camera/video/image at mobile and desktop widths.');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
