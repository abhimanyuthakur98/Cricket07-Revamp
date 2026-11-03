import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
for (const basePointer of [559428, 559636]) {
const binary=execFileSync(process.env.PYTHON||'python',['-c',
  `import sys; from roster.tests.test_engine_patch import hook_fixture; sys.stdout.buffer.write(hook_fixture(${basePointer}))`]);
for (const enabled of [true,false]) for (const side of [0,1]) {
  const memory=new WebAssembly.Memory({initial:256}), guestBase=0x1000;
  const view=new DataView(memory.buffer,guestBase), host=new DataView(memory.buffer);
  const cpu=0x1000, app=0x2000, selector=0x3000, teamId=13, team=0x817d48+teamId*2808;
  // A nonzero, relocated guest base catches a hook using the wrong symbol.
  host.setUint32(basePointer,guestBase,true);
  host.setUint32(cpu+4,selector,true);
  view.setUint32(selector+52,side,true);
  view.setUint32(selector+56,teamId,true);
  view.setUint32(team+40,teamId,true);
  new Uint8Array(memory.buffer)[guestBase+0xb00000+teamId]=enabled?1:0;
  for(let i=0;i<20;i++) view.setUint16(team+i*2,i+1,true);
  let nativeCalled=false;
  const {instance}=await WebAssembly.instantiate(binary,{env:{memory,native(ptr){
    nativeCalled=true;
    // The real engine may reorder the XI. When enabled, bench players must not
    // enter its keeper/bowling selection pool in place of the latest-match XI.
    assert.equal(view.getUint16(team+22,true),enabled?0:12);
    for(let i=0;i<11;i++)view.setUint16(app+0xfc+side*22+i*2,11-i,true);
    view.setUint16(app+0x128+side*2,3,true);
    view.setUint16(app+0x12c+side*12,9,true);
    host.setUint32(ptr+4,app+0xe0,true);
  }}});
  instance.exports.run(cpu);
  assert.ok(nativeCalled);
  for(let i=0;i<11;i++)assert.equal(view.getUint16(app+0xfc+side*22+i*2,true),enabled?i+1:11-i);
  assert.equal(view.getUint16(app+0x128+side*2,true),3);
  assert.equal(view.getUint16(app+0x12c+side*12,true),9);
  for(let i=0;i<9;i++){
    assert.equal(view.getUint16(team+22+i*2,true),12+i);
    if(enabled)assert.equal(view.getUint16(app+0x168+side*18+i*2,true),12+i);
  }
  if(enabled)assert.equal(view.getUint8(app+0x18c+side),8);
}
}
console.log('Native XI order, reserve restoration and selection assignments passed.');

