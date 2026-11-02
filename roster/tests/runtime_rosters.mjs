import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../../web/roster-runtime.js',import.meta.url));
const {formatForOvers,attach}=await import('data:text/javascript;base64,'+source.toString('base64'));
for (const n of [1,5,10,15,20]) assert.equal(formatForOvers(n),'T20');
assert.equal(formatForOvers(50),'ODI');
assert.equal(formatForOvers(-1),'Test');
assert.equal(formatForOvers(0),null);
assert.equal(formatForOvers(30),null);
const buffer=new ArrayBuffer(0x1000000), memory=new Uint8Array(buffer), view=new DataView(buffer);
memory.set([77,90],0x400000); memory[0x40003c]=0x28; memory[0x40003d]=1;
memory.set([0xb8,0xe8],0x487930);
view.setUint16(0x845c30,1,true);
view.setUint32(0x9303b8+40,13,true);
let callback, inMenu=true;
globalThis.setInterval=f=>{callback=f;return 1;};
globalThis.clearInterval=()=>{};
globalThis.document={getElementById:()=>({textContent:''})};
globalThis.window={revampDatabases:{}};
for (const [format,marker] of [['T20',20],['ODI',50],['Test',99]]) {
  const data=new Uint8Array(620140), v=new DataView(data.buffer);
  v.setUint16(4,1,true); data[8]=marker;
  for (const teamId of [0,13]) {
    v.setUint16(432004+teamId*2808,marker,true);
    v.setUint32(432004+teamId*2808+40,teamId,true);
  }
  window.revampDatabases[format]=data;
}
view.setInt32(0x930eb4,20,true);
const stop=attach({wasmMemory:{buffer},_c07_in_menu:()=>inMenu});
assert.equal(memory[0x845c30+4],20);
view.setInt32(0x930eb4,50,true);callback();
assert.equal(memory[0x845c30+4],50);
assert.equal(view.getUint16(0x9303b8,true),50);
assert.equal(view.getUint32(0x9303b8+40,true),13);
inMenu=false;view.setInt32(0x930eb4,-1,true);callback();
assert.equal(memory[0x845c30+4],50);
inMenu=true;callback();assert.equal(memory[0x845c30+4],99);
stop();
console.log('Runtime roster switching passed.');
