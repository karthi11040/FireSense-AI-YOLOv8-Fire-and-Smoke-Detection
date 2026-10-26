// Lightweight canvas scene. Illustrative response only; no physical fire model.
export function drawRoom(ctx,w,h,level,water,t,targeted=false) {
  ctx.clearRect(0,0,w,h);
  ctx.fillStyle='#f0f5f7';ctx.fillRect(0,0,w,h);
  const polygon=(points,fill,stroke='#c5d3da')=>{
    ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x*w,y*h):ctx.moveTo(x*w,y*h));
    ctx.closePath();ctx.fillStyle=fill;ctx.fill();ctx.strokeStyle=stroke;ctx.lineWidth=1;ctx.stroke();
  };
  polygon([[.12,.56],[.50,.36],[.88,.56],[.50,.83]],'#e3ecee');
  polygon([[.12,.28],[.50,.09],[.50,.36],[.12,.56]],'#ffffff');
  polygon([[.50,.09],[.88,.28],[.88,.56],[.50,.36]],'#eaf0f4');
  ctx.strokeStyle='#d2dee4';ctx.lineWidth=1;
  for(let i=1;i<6;i++) {
    const f=i/6;
    ctx.beginPath();ctx.moveTo((.12+.38*f)*w,(.56-.20*f)*h);ctx.lineTo((.50+.38*f)*w,(.83-.27*f)*h);ctx.stroke();
    ctx.beginPath();ctx.moveTo((.50+.38*f)*w,(.36+.20*f)*h);ctx.lineTo((.12+.38*f)*w,(.56+.27*f)*h);ctx.stroke();
  }
  polygon([[.20,.34],[.32,.28],[.32,.46],[.20,.52]],'#f2f6f8','#a9bcc5');
  polygon([[.64,.23],[.77,.30],[.77,.47],[.64,.40]],'#d9e4e9','#bacbd3');
  polygon([[.22,.57],[.30,.53],[.36,.57],[.28,.62]],'#c4d3d9');
  polygon([[.22,.57],[.28,.62],[.28,.70],[.22,.65]],'#d2dfe3');
  polygon([[.28,.62],[.36,.57],[.36,.65],[.28,.70]],'#acbfc8');
  const pipe=water?'#087e94':'#819aa8';
  ctx.strokeStyle=pipe;ctx.lineWidth=4;ctx.lineJoin='round';
  ctx.beginPath();ctx.moveTo(w*.19,h*.30);ctx.lineTo(w*.50,h*.145);ctx.lineTo(w*.81,h*.30);ctx.stroke();
  const heads=[[.32,.25],[.50,.16],[.68,.25]];
  if(targeted && water && level>0){
    polygon([[.50,.24],[.25,.54],[.39,.69]],'rgba(5,145,114,.14)','#6caa9e');
  }
  const tag=(text,x,y,color)=>{
    ctx.font=`${Math.max(9,w*.012)}px Segoe UI`;const width=ctx.measureText(text).width+8;
    ctx.fillStyle=color;ctx.fillRect(x*w,y*h,width,Math.max(13,w*.018));ctx.fillStyle='white';ctx.fillText(text,x*w+4,y*h+Math.max(10,w*.014));
  };
  for(const [x,y] of heads) {
    ctx.strokeStyle=pipe;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(x*w,y*h);ctx.lineTo(x*w,(y+.07)*h);ctx.stroke();
    ctx.fillStyle=pipe;ctx.fillRect(x*w-6,(y+.07)*h,12,4);
    if(targeted)tag(water && x===.50?'ACTIVE · DISCHARGING':'CLOSED',x+.015,y+.09,water && x===.50?'#27816b':'#768b95');
    if(water && (!targeted || x===.50)) {
      ctx.fillStyle='rgba(21,146,181,.07)';ctx.beginPath();ctx.moveTo(x*w,(y+.08)*h);ctx.lineTo((x-.09)*w,(y+.44)*h);ctx.lineTo((x+.09)*w,(y+.44)*h);ctx.closePath();ctx.fill();
      for(let i=0;i<(targeted?160:20);i++) {
        const f=(t*.85+i*.049)%1,dx=Math.sin(i*19.7)*f*w*(targeted?.12:.09);
        ctx.strokeStyle=`rgba(18,137,175,${.75*(1-f)})`;ctx.lineWidth=1.4;
        ctx.beginPath();ctx.moveTo(x*w+dx,(y+.09+f*.34)*h);ctx.lineTo(x*w+dx-1,(y+.09+f*.34)*h+6);ctx.stroke();
      }
    }
  }
  const fx=w*(targeted?.29:.52),fy=h*(targeted?.60:.72),scale=Math.max(.08,level/100),fw=w*.085*scale,fh=h*.30*scale;
  ctx.fillStyle=water?'rgba(28,141,166,.12)':'rgba(119,141,150,.10)';ctx.beginPath();ctx.ellipse(fx,fy+3,w*.105,h*.036,0,0,Math.PI*2);ctx.fill();
  if(level>0) {
    if(targeted){
      ctx.strokeStyle='#bb392d';ctx.lineWidth=2;
      for(const [x,y,sx,sy] of [[.20,.38,1,1],[.38,.38,-1,1],[.20,.69,1,-1],[.38,.69,-1,-1]]){
        ctx.beginPath();ctx.moveTo((x+sx*.025)*w,y*h);ctx.lineTo(x*w,y*h);ctx.lineTo(x*w,(y+sy*.035)*h);ctx.stroke();
      }
      tag('VIRTUAL FIRE TARGET',.14,.35,'#b43e30');
      if(water)tag('TARGET LOCK · SIMULATED',.52,.30,'#27816b');
    }
    for(let i=0;i<6;i++) {
      const f=(t*.23+i/6)%1;
      ctx.fillStyle=`rgba(117,132,143,${.19*(1-f)})`;ctx.beginPath();
      ctx.ellipse(fx+Math.sin(t+i)*w*.012,fy-fh-f*h*.24,w*(.023+f*.025),h*(.022+f*.015),0,0,Math.PI*2);ctx.fill();
    }
    const sway=Math.sin(t*7)*fw*.15;
    ctx.fillStyle='#ed6838';ctx.beginPath();ctx.moveTo(fx-fw,fy);
    ctx.bezierCurveTo(fx-fw*1.7,fy-fh*.45,fx-fw*.4,fy-fh*.48,fx-fw*.45,fy-fh*.74);
    ctx.quadraticCurveTo(fx-fw*.15,fy-fh*.50,fx+sway,fy-fh);
    ctx.bezierCurveTo(fx+fw*.15,fy-fh*.5,fx+fw*1.7,fy-fh*.38,fx+fw,fy);ctx.closePath();ctx.fill();
    ctx.fillStyle='#ffbb64';ctx.beginPath();ctx.moveTo(fx-fw*.6,fy);
    ctx.quadraticCurveTo(fx-fw*.7,fy-fh*.28,fx+sway*.5,fy-fh*.66);
    ctx.quadraticCurveTo(fx+fw*.9,fy-fh*.19,fx+fw*.6,fy);ctx.fill();
    ctx.fillStyle='#ffe6ad';ctx.beginPath();ctx.ellipse(fx,fy-h*.02,fw*.32,fh*.24,0,0,Math.PI*2);ctx.fill();
  }
}
