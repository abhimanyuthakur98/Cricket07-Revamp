import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../../web/broadcast-state.js',import.meta.url));
const {readMatch,readDeliveries,overCells,nativeStripVisible,oversText,MATCH}=await import('data:text/javascript;base64,'+source.toString('base64'));
const code=execFileSync('python',['-c','from roster.tests.test_ui import delivery_fixture; import sys; sys.stdout.buffer.write(delivery_fixture())']);
const memory=new WebAssembly.Memory({initial:256});
const {instance}=await WebAssembly.instantiate(code,{env:{memory}});
const v=new DataView(memory.buffer),b=new Uint8Array(memory.buffer);
v.setUint32(559428,0,true); // Synthetic fixture uses guest base zero.
b[0xb00080]=1;
v.setUint32(MATCH+0x1c20,13,true);v.setUint32(MATCH+0xd564,13,true);v.setUint32(MATCH+0xd568,27,true);
v.setInt16(MATCH+0x58c4,20,true);
const p1=MATCH+0x1c2c,p2=p1+360,bowl=MATCH+0x4864;
function player(p,id,name){v.setUint16(p,id,true);b.set(new TextEncoder().encode(name),p+4);}
player(p1,1,'RG Sharma');player(p2,2,'V Kohli');player(bowl,3,'Shaheen Afridi');
v.setUint32(MATCH+0xd538,p1,true);v.setUint32(MATCH+0xd53c,p2,true);v.setUint32(MATCH+0xd540,bowl,true);v.setUint32(MATCH+0xd544,bowl,true);
v.setUint32(p1+0xa4,30<<20,true);v.setUint32(p1+0xa0,20<<21,true);
v.setUint32(bowl+0xb4,8<<18,true);v.setUint32(bowl+0xac,12,true);v.setUint32(bowl+0xa8,1<<20,true);
v.setUint16(MATCH+0x58dc,42,true);v.setUint16(MATCH+0x5910,1,true);
v.setUint16(MATCH+0x58e4,1,true);v.setUint16(MATCH+0x21214,2,true);
let s=readMatch(memory.buffer,0);
assert.equal(s.runs,42);assert.equal(s.wickets,1);assert.equal(s.striker.runs,30);assert.equal(s.striker.balls,20);
assert.equal(s.bowler.conceded,12);assert.equal(s.bowler.wickets,1);assert.equal(oversText(s.legalBalls),'1.2');
const shared=new SharedArrayBuffer(memory.buffer.byteLength);new Uint8Array(shared).set(b);
assert.equal(readMatch(shared,0).striker.name,'RG Sharma','Real browser engine uses SharedArrayBuffer');
const before=b.slice(MATCH,MATCH+0x21300);
for(const [flags,wicket,runs,kind] of [[16,0,4,1],[2,0,1,2],[1,0,2,3],[0,1,0,4]]){
 b[MATCH+0x21218]=flags;b[MATCH+0x2121c]=wicket;v.setUint16(MATCH+0x21216,runs,true);
 const snapshot=b.slice(MATCH,MATCH+0x21300);instance.exports.run(0);
 assert.deepEqual(b.slice(MATCH,MATCH+0x21300),snapshot,'Hook must never write native state');
 const event=readDeliveries(memory.buffer,0).at(-1);assert.equal(event.kind,kind);assert.equal(event.runs,runs);assert.equal(event.bowler,3);
}
// Ring wrap and disabled hook; no lost or duplicated events through polling.
for(let i=0;i<140;i++)instance.exports.run(0);
assert.equal(readDeliveries(memory.buffer,0).length,128);
const count=v.getUint32(0xb01004,true);b[0xb00080]=0;instance.exports.run(0);assert.equal(v.getUint32(0xb01004,true),count);
const extraEvents=[{over:0,flags:2,kind:2},{over:0,flags:1,kind:3}];
assert.equal(overCells(extraEvents).length,8,'Two illegal deliveries require eight total slots');
assert.equal(overCells([...extraEvents,...Array.from({length:6},()=>({over:0,flags:0,kind:1}))]).filter(Boolean).length,8);
assert.equal(overCells([...extraEvents,{over:1,flags:0,kind:1}]).length,6,'New over resets extra slots');
assert.equal(overCells(Array.from({length:20},()=>({over:0,flags:2,kind:2}))).length,26,'No truncation of extra balls');
for(const graphic of [false,true]){
 const wasm=execFileSync('python',['-c',`from roster.tests.test_ui import render_fixture; import sys; sys.stdout.buffer.write(render_fixture(${graphic?'True':'False'}))`]);
 const {instance:draw}=await WebAssembly.instantiate(wasm,{env:{memory}});
 const cpu=0x1000,scene=0x400100,node=0x400200;
 v.setUint32(0x95bfe8,scene,true);v.setUint16(scene+4,1,true);v.setUint32(cpu+4,node,true);b[0xb00081]=1;
 v.setUint32(0xb00094,20,true);
 for(const [id,hidden] of (graphic?[[1000,true],[1002,true],[1006,true],[4,true],[9,true],[1001,false],[70,false]]:[[10,true],[420,true],[20,false],[50,false]])){
  v.setUint16(node+4,id,true);v.setFloat32(node+8,-92,true);v.setUint32(cpu+16,0x500000,true);v.setUint32(0xb000a0,0,true);
  const pulse=v.getUint32(0xb00084,true);draw.exports.run(cpu);
  assert.equal(v.getUint32(0xb000a0,true),hidden?0:1,`Native draw gate ${id}`);
  if(hidden)assert.equal(v.getUint32(cpu+16,true),0x500008,'Native ret 4 stack balance');
  if(id===10)assert.equal(v.getUint32(0xb00084,true),pulse+1);
 }
 if(graphic){v.setUint32(0xb00094,50,true);v.setUint16(node+4,4,true);v.setUint32(0xb000a0,0,true);draw.exports.run(cpu);assert.equal(v.getUint32(0xb000a0,true),1,'Radar graphic with same ID remains');}
 b[0xb00081]=0;v.setUint16(node+4,graphic?1000:10,true);v.setUint32(0xb000a0,0,true);draw.exports.run(cpu);
 assert.equal(v.getUint32(0xb000a0,true),1,'Other native screens are untouched');
}
v.setUint32(MATCH+0xd538,0xfffffff0,true);assert.equal(readMatch(memory.buffer,0),null);
const root=0x400100,win=0x400300,list=0x400400,backdrop=0x400500;
v.setUint32(0x95bfe8,root,true);v.setUint16(root+4,1,true);
v.setUint32(0xb00088,win,true);v.setUint16(win+4,10,true);v.setUint32(win+0x34,list,true);
v.setUint32(list+8,backdrop,true);v.setUint32(list+16,list,true);v.setUint16(backdrop+4,299,true);
b[backdrop+0x35]=4;b[backdrop+0x67]=255;v.setFloat32(backdrop+8,-92,true);
assert.equal(nativeStripVisible(memory.buffer,0),true);
v.setFloat32(backdrop+8,-946,true);assert.equal(nativeStripVisible(memory.buffer,0),false,'Native slide-out hides replacement');
v.setFloat32(backdrop+8,-92,true);b[backdrop+0x67]=0;assert.equal(nativeStripVisible(memory.buffer,0),false,'Native fade-out hides replacement');
b[backdrop+0x67]=255;v.setUint16(root+4,32,true);assert.equal(nativeStripVisible(memory.buffer,0),false,'Coin toss does not show ticker');
console.log('Broadcast native delivery hook, ring, score reader and read-only safety passed.');
