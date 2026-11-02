// Native layout verified against the pinned browser engine used by engine_patch.py.
// Read-only: no simulation, roster, selection or scoring memory is modified.
export const MATCH = 0x9a48b0;
export const TEAMS = {
  0:['AUS','Australia','au'],1:['BAN','Bangladesh','bd'],3:['CAN','Canada','ca'],
  7:['ENG','England','gb-eng'],13:['IND','India','in'],15:['KEN','Kenya','ke'],
  20:['NAM','Namibia','na'],21:['NED','Netherlands','nl'],23:['NZ','New Zealand','nz'],
  27:['PAK','Pakistan','pk'],30:['SA','South Africa','za'],32:['SL','Sri Lanka','lk'],
  39:['WI','West Indies','wi'],43:['ZIM','Zimbabwe','zw'],57:['SCO','Scotland','gb-sct'],
  58:['USA','United States','us'],59:['BER','Bermuda','bm'],60:['IRE','Ireland','ie'],
  61:['SCO','Scotland','gb-sct'],62:['IRE','Ireland','ie']
};
export const oversText = balls => `${Math.floor(balls/6)}.${balls%6}`;
export function nativeStripVisible(buffer,base){
  const v=new DataView(buffer);
  const valid=p=>p>0x400000&&base+p+128<buffer.byteLength;
  const u32=p=>v.getUint32(base+p,true);
  const root=u32(0x95bfe8);
  if(!valid(root)||v.getUint16(base+root+4,true)!==1)return false;
  const win=u32(0xb00088);
  if(!valid(win)||v.getUint16(base+win+4,true)!==10)return false;
  let list=u32(win+0x34);const seen=new Set();
  for(let i=0;i<64&&valid(list)&&!seen.has(list);i++){
    seen.add(list);const item=u32(list+8);
    if(valid(item)&&v.getUint16(base+item+4,true)===299){
      return (v.getUint8(base+item+0x35)&4)!==0&&v.getUint8(base+item+0x67)>0&&v.getFloat32(base+item+8,true)>-200;
    }
    list=u32(list+16);
  }
  return false;
}
export function readMatch(buffer,base) {
  const view=new DataView(buffer), bytes=new Uint8Array(buffer);
  const valid=p=>Number.isInteger(p)&&p>0x400000&&base+p+360<bytes.length;
  const u32=p=>view.getUint32(base+p,true),u16=p=>view.getUint16(base+p,true),u8=p=>bytes[base+p];
  if(base<0||base+MATCH+0x21300>=bytes.length)return null;
  const teamA=u32(MATCH+0x1c20),batting=u32(MATCH+0xd564),fielding=u32(MATCH+0xd568);
  if(!TEAMS[batting]||!TEAMS[fielding]||batting===fielding)return null;
  const innings=u8(MATCH+0x58c9);
  if(innings>3)return null;
  const text=p=>new TextDecoder('windows-1252').decode(Uint8Array.from(bytes.subarray(base+p+4,base+p+20))).split('\0')[0].trim();
  function player(p){
    if(!valid(p))return null;
    const name=text(p);if(!name||!/^[\w .'-]+$/.test(name))return null;
    const a0=u32(p+0xa0),a4=u32(p+0xa4),a8=u32(p+0xa8),ac=u32(p+0xac);
    const legal=(u32(p+0xb4)>>>18)&4095;
    return {id:u16(p),name,runs:(a4>>>20)&2047,balls:(a0>>>21)&2047,
      bowlingOvers:Math.floor(legal/6),maidens:(a8>>>11)&511,wickets:(a8>>>20)&511,
      conceded:ac&4095,bowlingBalls:legal%6,legalBalls:legal};
  }
  const striker=player(u32(MATCH+0xd538)),nonStriker=player(u32(MATCH+0xd53c)),bowler=player(u32(MATCH+0xd540));
  if(!striker||!nonStriker||!bowler)return null;
  const slot=batting===teamA?0:1;
  const runs=Math.max(0,view.getInt16(base+MATCH+0x58dc+innings*2,true));
  const wickets=Math.max(0,view.getInt16(base+MATCH+0x5910+innings*2,true));
  // The native innings over count and current-over legal deliveries reset
  // together at the over boundary. Illegal deliveries never advance them.
  const legalBalls=u16(MATCH+0x58e4+innings*2)*6+u16(MATCH+0x21214);
  const limit=view.getInt16(base+MATCH+0x58c4,true);
  if(runs>4000||wickets>10||legalBalls>30000||bowler.bowlingBalls>5)return null;
  return {batting,fielding,innings,runs,wickets,legalBalls,limit,striker,nonStriker,bowler,
    key:`${teamA}:${batting}:${fielding}:${innings}`,slot};
}

// Delivery records are supplied by the native completed-ball hook. This keeps
// wides/no-balls distinct and survives tab throttling without guessing deltas.
export function readDeliveries(buffer,base) {
  const v=new DataView(buffer),start=base+0xb01000;
  if(start+0x1010>buffer.byteLength||v.getUint32(start,true)!==0x43303742)return [];
  const count=v.getUint32(start+4,true),out=[];
  for(let n=Math.max(0,count-128);n<count;n++){
    const p=start+16+(n%128)*32;
    out.push({sequence:n,innings:v.getUint32(p,true),over:v.getUint32(p+4,true),
      runs:v.getUint32(p+8,true),kind:v.getUint32(p+12,true),
      wickets:v.getUint32(p+16,true),bowler:v.getUint32(p+20,true),flags:v.getUint32(p+24,true)});
  }
  return out;
}

export function overCells(events){
  if(!events.length)return Array(6).fill(null);
  const over=events.at(-1).over;
  const balls=events.filter(e=>e.over===over);
  const legal=balls.filter(e=>!(e.flags&3)).length;
  return [...balls,...Array(Math.max(0,6-legal)).fill(null)];
}
