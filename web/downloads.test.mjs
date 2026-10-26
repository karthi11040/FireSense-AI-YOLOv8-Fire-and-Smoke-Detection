import test from 'node:test';
import assert from 'node:assert/strict';
import {AnnotatedRecording, outputName} from './downloads.mjs';

class Recorder {
  static isTypeSupported(){return true;}
  constructor(){this.state='inactive';Recorder.latest=this;}
  start(){this.state='recording';}
  stop(){this.state='inactive';queueMicrotask(()=>this.onstop());}
  emit(data=new Blob(['video'])){this.ondataavailable({data});}
}
const fixture=()=>{
  let stopped=false;
  const canvas={captureStream:()=>({getTracks:()=>[{stop(){stopped=true;}}]})};
  return {canvas,stopped:()=>stopped};
};

test('download names preserve useful text without path or invalid characters',()=>{
  assert.equal(outputName('fire clip.mp4','webm'),'fire clip-annotated.webm');
  assert.equal(outputName('../bad:name.png','png'),'..-bad-name-annotated.png');
});
test('completed clip finalizes asynchronously and releases capture tracks',async()=>{
  globalThis.MediaRecorder=Recorder;const f=fixture(),r=new AnnotatedRecording(f.canvas,()=>{},()=>{});
  r.start('fire.mp4');assert.equal(r.busy,true);Recorder.latest.emit();r.stop('Video ended',true);
  assert.equal(r.finalizing,true);await new Promise(queueMicrotask);
  assert.equal(r.busy,false);assert.equal(r.clip.complete,true);assert.equal(r.clip.blob.size,5);assert.ok(f.stopped());
  const previous=r.clip;r.stop();assert.equal(r.clip,previous);
});
test('recording byte limit preserves a partial clip and cleans up',async()=>{
  globalThis.MediaRecorder=Recorder;const f=fixture(),r=new AnnotatedRecording(f.canvas,()=>{},()=>{});
  r.start('camera');Recorder.latest.emit({size:101*1024*1024});await new Promise(queueMicrotask);
  assert.equal(r.busy,false);assert.equal(r.clip.complete,false);assert.match(r.clip.reason,/limit/i);assert.ok(f.stopped());
});
test('failed start preserves the previous download and stops capture tracks',()=>{
  globalThis.MediaRecorder=class extends Recorder{start(){throw Error('encoder failed');}};
  const f=fixture(),r=new AnnotatedRecording(f.canvas,()=>{},()=>{});r.clip={name:'previous.webm'};
  assert.throws(()=>r.start('new'),/encoder failed/);assert.equal(r.clip.name,'previous.webm');assert.ok(f.stopped());
});
