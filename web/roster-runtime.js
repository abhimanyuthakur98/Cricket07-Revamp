// Verified against executable SHA-1 prefix 9e9d0deeeab9. Stadium selection commits
// its overs value before Match Conditions and Selections are constructed.
export function formatForOvers(overs) {
  if (overs === -1) return 'Test';
  if (overs > 0 && overs <= 20) return 'T20';
  if (overs === 50) return 'ODI';
  return null;
}

export function attach(M) {
  let base = -1, active = null, probeAt = 0;
  const message = document.getElementById('revamp-message');
  function tick() {
    const memory = new Uint8Array(M.wasmMemory.buffer);
    if (base < 0) {
      if (performance.now()<probeAt) return;
      probeAt=performance.now()+500;
      for (let p=0x400000;p<Math.min(memory.length-0x640000,0x10000000);p+=4) {
        if (memory[p]===77 && memory[p+1]===90 && memory[p+0x3c]===0x28 && memory[p+0x3d]===1) {
          const candidate=p-0x400000;
          if (memory[candidate+0x487930]===0xb8 && memory[candidate+0x487931]===0xe8) {
            base=candidate; break;
          }
        }
      }
      if (base<0) return;
    }
    if (M._c07_in_menu && !M._c07_in_menu()) return;
    const view=new DataView(memory.buffer);
    const overs=view.getInt32(base+0x930eb4,true);
    const format=formatForOvers(overs);
    if (!format || format===active) return;
    const database=window.revampDatabases[format];
    if (database?.length!==620140) throw new Error('Unsupported roster layout');
    const dataView=new DataView(database.buffer,database.byteOffset,database.byteLength);
    let anchor=4;
    while (anchor<432004 && dataView.getUint16(anchor,true)===0) anchor+=360;
    // Wait for the native CDF load; otherwise its startup copy could undo ours.
    if (anchor>=432004 || view.getUint16(base+0x845c30+anchor-4,true)!==dataView.getUint16(anchor,true)) return;
    memory.set(database.subarray(4,432004),base+0x845c30);
    memory.set(database.subarray(432004),base+0x817d48);
    // Team selection has already cached both squads. Refresh IDs/captain before
    // the game constructs its XI, keeper and bowling assignments.
    for (const cached of [0x92f8c0,0x9303b8]) {
      const teamId=view.getUint32(base+cached+40,true);
      if (teamId<67) {
        const team=432004+teamId*2808;
        memory.set(database.subarray(team,team+48),base+cached);
      }
    }
    active=format;
    message.textContent=`${format==='T20'?'T20 international':format} · latest available match squads`;
    console.info('REVAMP roster selected',format,'overs',overs);
  }
  const timer=setInterval(tick,16);
  tick();
  return ()=>clearInterval(timer);
}
