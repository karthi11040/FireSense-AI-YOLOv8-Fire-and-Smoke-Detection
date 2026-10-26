export function outputName(name, extension) {
  const base=(name || 'firesense').replace(/\.[^.]+$/,'').replace(/[<>:"/\\|?*\x00-\x1f]/g,'-').slice(0,90);
  return `${base || 'firesense'}-annotated.${extension}`;
}

export function downloadBlob(blob,name) {
  const url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export class AnnotatedRecording {
  constructor(canvas,onChange,onError) {
    this.canvas=canvas;this.onChange=onChange;this.onError=onError;this.session=null;this.clip=null;
  }
  get supported(){return typeof MediaRecorder!=='undefined' && Boolean(this.canvas.captureStream) &&
    ['video/webm;codecs=vp8','video/webm'].some(type=>MediaRecorder.isTypeSupported(type));}
  get busy(){return Boolean(this.session);}
  get finalizing(){return this.busy && this.session.recorder.state==='inactive';}
  start(name) {
    if(!this.supported)throw Error('Video recording is unavailable in this browser. Try Chrome or Edge; image download still works.');
    if(this.busy)throw Error('The previous recording is still finalizing.');
    const mimeType=['video/webm;codecs=vp8','video/webm'].find(type=>MediaRecorder.isTypeSupported(type));
    const stream=this.canvas.captureStream(15);
    const session={stream,chunks:[],bytes:0,name:outputName(name,'webm'),reason:'Stopped early',complete:false};
    try {
      session.recorder=new MediaRecorder(stream,{mimeType,videoBitsPerSecond:2500000});
      session.recorder.ondataavailable=({data})=>{
        if(this.session!==session)return;
        if(data.size){session.chunks.push(data);session.bytes+=data.size;}
        if(session.bytes>=100*1024*1024)this.stop('100 MB recording limit reached');
      };
      session.recorder.onerror=()=>{if(this.session!==session)return;this.onError('Video recording failed. Detection can continue; any saved clip may be partial.');this.stop('Recording error');};
      session.recorder.onstop=()=>{
        clearTimeout(session.timer);stream.getTracks().forEach(track=>track.stop());
        if(this.session!==session)return;
        this.session=null;
        if(session.chunks.length)this.clip={blob:new Blob(session.chunks,{type:mimeType}),name:session.name,reason:session.reason,complete:session.complete};
        this.onChange();
      };
      session.recorder.start(1000);
      this.session=session;this.clip=null;
      session.timer=setTimeout(()=>this.stop('10 minute recording limit reached'),10*60*1000);
      this.onChange();
    } catch(error) {
      stream.getTracks().forEach(track=>track.stop());throw error;
    }
  }
  stop(reason='Stopped early',complete=false) {
    const session=this.session;
    if(!session || session.recorder.state==='inactive')return;
    session.reason=reason;session.complete=complete;session.recorder.stop();this.onChange();
  }
}
