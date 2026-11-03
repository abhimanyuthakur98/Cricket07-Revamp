// Native layout verified against the pinned browser engine used by engine_patch.py.
// Read-only: no simulation, roster, selection or scoring memory is modified.
export const MATCH = 0x9a48b0;
export const PANEL_IDS = [101,102,103,201,202,300,360,370,400,500,310];
export const PANEL_STATE = 0xb00100;
export const SHOT = 0xb000c0;
export const WICKET = 0xb00200;
export const BALL_START = 0xb00240;
export const SPEED = 0xb00280;
const PANEL_LABELS={842:'BALLS',843:'FOURS',844:'SIXES',849:'RUNS',856:'Partnership',868:'Player of the Match'};
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
export function readPlayer(buffer,base,p){
  if(!Number.isInteger(p)||p<=0x400000||base+p+360>buffer.byteLength)return null;
  const v=new DataView(buffer),b=new Uint8Array(buffer),u32=o=>v.getUint32(base+p+o,true);
  const name=new TextDecoder('windows-1252').decode(Uint8Array.from(b.subarray(base+p+4,base+p+20))).split('\0')[0].trim();
  if(!name||!/^[\w .'-]+$/.test(name))return null;
  const a0=u32(0xa0),a4=u32(0xa4),a8=u32(0xa8),ac=u32(0xac),legal=(u32(0xb4)>>>18)&4095;
  return {id:v.getUint16(base+p,true),name,runs:(a4>>>20)&2047,balls:(a0>>>21)&2047,
    bowlingOvers:Math.floor(legal/6),maidens:(a8>>>11)&511,wickets:(a8>>>20)&511,
    conceded:ac&4095,bowlingBalls:legal%6,legalBalls:legal};
}

// Native active-batter control lookup, f_0055eb20. Input type 8 is Keyboard,
// 9 is Mouse (f_006f9cf0); a computer-controlled actor has no input device.
export function playerBatting(buffer,base){
  const v=new DataView(buffer),valid=(p,size)=>p>0x400000&&base+p+size<=buffer.byteLength;
  const u32=p=>v.getUint32(base+p,true);
  if(base<0||base+0x817584>buffer.byteLength)return false;
  const app=u32(0x817580);if(!valid(app,0x2744))return false;
  const team=u32(app+0x2740);if(!valid(team,0x94))return false;
  const slot=v.getUint8(base+team+6);if(slot>=20)return false;
  const actor=u32(team+0x44+slot*4);if(!valid(actor,8))return false;
  const control=u32(actor+4);return valid(control,0x2574)&&u32(control+0x2570)<=9;
}
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

// Native event 65 carries measured release speeds for human and AI bowling.
// The old scorebox swaps its text between speed, overs and RUN RATE; do not
// depend on that widget's contents, fade or visibility to obtain a speed.
export function readDeliverySpeed(buffer,base,{match=null,ball=null}={}){
  const v=new DataView(buffer),p=base+SPEED;
  if(p<0||p+36>buffer.byteLength||v.getUint32(p,true)!==0x43303756)return null;
  if(match&&(v.getUint32(p+20,true)!==match.innings||v.getUint32(p+24,true)!==match.bowler.id))return null;
  if(ball&&v.getUint32(p+16,true)!==ball.sequence)return null;
  const mph=!!v.getUint32(p+32,true),value=v.getFloat32(p+(mph?8:12),true);
  if(!Number.isFinite(value)||value<=0||value>(mph?160:260))return null;
  return `${Number(value.toFixed(1))} ${mph?'mph':'km/h'}`;
}

export function liveMatchVisible(buffer,base){
  const v=new DataView(buffer);
  if(base<0||base+MATCH+0x21200>buffer.byteLength)return false;
  const root=v.getUint32(base+0x95bfe8,true);
  return root>0x400000&&base+root+6<=buffer.byteLength&&
    v.getUint16(base+root+4,true)===1&&v.getUint32(base+MATCH+0x211fc,true)===0;
}

export function readBallStart(buffer,base){
  const v=new DataView(buffer),p=base+BALL_START;
  if(p<0||p+16>buffer.byteLength||v.getUint32(p,true)!==0x4330374e)return null;
  return {sequence:v.getUint32(p+4,true),delivery:v.getUint32(p+8,true),innings:v.getUint32(p+12,true)};
}

export function readBattingZone(buffer,base){
  const v=new DataView(buffer),valid=p=>p>0x400000&&base+p+0x2dc<=buffer.byteLength;
  if(base<0||base+0x817584>buffer.byteLength)return null;
  let p=v.getUint32(base+0x817580,true);if(!valid(p)||base+p+0x2744>buffer.byteLength)return null;
  p=v.getUint32(base+p+0x2740,true);if(!valid(p))return null;
  p=v.getUint32(base+p+0xb8,true);if(!valid(p))return null;
  const zone=v.getUint32(base+p+0x2d8,true);
  return zone>=0&&zone<=7?zone:null;
}
export function readMatch(buffer,base) {
  const view=new DataView(buffer), bytes=new Uint8Array(buffer);
  const u32=p=>view.getUint32(base+p,true),u16=p=>view.getUint16(base+p,true),u8=p=>bytes[base+p];
  if(base<0||base+MATCH+0x21300>=bytes.length)return null;
  const teamA=u32(MATCH+0x1c20),batting=u32(MATCH+0xd564),fielding=u32(MATCH+0xd568);
  if(!TEAMS[batting]||!TEAMS[fielding]||batting===fielding)return null;
  const innings=u8(MATCH+0x58c9);
  if(innings>3)return null;
  const player=p=>readPlayer(buffer,base,p);
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
  // Native team aggregates include the current innings (f_004491d0).
  const battingTotal=u16(MATCH+0x5874+slot*4),fieldingTotal=u16(MATCH+0x5874+(1-slot)*4);
  const target=limit>0&&innings===1?fieldingTotal+1:
    limit===-1&&innings===3?fieldingTotal-(battingTotal-runs)+1:null;
  return {batting,fielding,innings,runs,wickets,legalBalls,limit,striker,nonStriker,bowler,target,
    key:`${teamA}:${batting}:${fielding}:${innings}`,slot};
}

// Work in legal balls: 5.4 overs means 34 balls, not 5.4 decimal overs.
export function chaseState(match){
  if(!Number.isFinite(match.target)||match.target<=0)return null;
  const needed=Math.max(0,match.target-match.runs);
  const balls=match.limit>0?Math.max(0,match.limit*6-match.legalBalls):null;
  const finished=needed===0||match.wickets>=10||balls===0;
  const rate=needed===0?0:!finished&&balls!==null?needed*6/balls:null;
  return {target:match.target,needed,balls,rate,finished};
}

// The native contact zones are ordered 0,5,4,3,2,1,6; 7 means no shot.
// The two zones beside Ideal are grouped as Good, with early/late kept visible.
export function timingForZone(zone){
  return {
    0:{kind:'bad',label:'Too Early',detail:'Too early',position:0},
    5:{kind:'early',label:'Early',detail:'Early',position:17},
    4:{kind:'good',label:'Good',detail:'Early side',position:33},
    3:{kind:'perfect',label:'Ideal',detail:'Ideal timing',position:50},
    2:{kind:'good',label:'Good',detail:'Late side',position:67},
    1:{kind:'late',label:'Late',detail:'Late',position:83},
    6:{kind:'bad',label:'Too Late',detail:'Too late',position:100},
  }[zone]??null;
}

export function readShot(buffer,base){
  const v=new DataView(buffer),p=base+SHOT;
  if(p<0||p+24>buffer.byteLength||v.getUint32(p,true)!==0x43303754)return null;
  const zone=v.getUint32(p+8,true);
  return timingForZone(zone)?{sequence:v.getUint32(p+4,true),zone,
    delivery:v.getUint32(p+12,true),innings:v.getUint32(p+16,true),ball:v.getUint32(p+20,true)}:null;
}

export function readDismissal(buffer,base){
  const v=new DataView(buffer),p=base+WICKET;
  if(p<0||p+20>buffer.byteLength||v.getUint32(p,true)!==0x43303757)return null;
  // A notice from an older ball must not reappear after tab throttling or a pause.
  if(v.getUint32(p+4,true)!==v.getUint32(base+0xb01004,true))return null;
  const player=readPlayer(buffer,base,v.getUint32(p+12,true));
  return player?{sequence:v.getUint32(p+4,true),innings:v.getUint32(p+8,true),
    batting:v.getUint32(p+16,true),player}:null;
}

export class DismissalNotice {
  constructor(){this.key=null;this.snapshot=null;this.shown=false;this.finished=false;this.ball=null;}
  update(event,match,panel,{ball=null,inMenu=false}={}){
    const hidden={active:false,player:null};
    if(!event||!match){this.key=null;this.snapshot=null;return hidden;}
    if(event.innings!==match.innings||event.batting!==match.batting)return hidden;
    const key=event.batting+':'+event.innings+':'+event.sequence;
    if(key!==this.key){
      this.key=key;this.snapshot=null;this.shown=false;this.finished=false;this.ball=null;
    }
    if(inMenu)return hidden;
    // No browser duration: native window 103 owns the dismissal scene. A skip
    // hides it immediately. Never let its old contents return over a new ball.
    if(this.shown&&ball&&ball.innings===event.innings&&ball.sequence!==this.ball)this.finished=true;
    if(panel?.id!==103){if(this.shown)this.finished=true;return hidden;}
    if(this.finished)return hidden;
    if(!this.shown){
      this.snapshot={...event.player};this.shown=true;this.ball=ball?.sequence??null;
    }
    return {active:true,player:this.snapshot};
  }
}

export class ShotFeedback {
  constructor(){this.reset(null);}
  reset(key){
    this.key=key;this.delivery=-1;this.shot=0;this.ball=null;this.firstDelivery=0;
    this.activeDelivery=-1;this.contactDelivery=-1;this.until=0;this.timing=null;
  }
  update(match,events,shot,now,playing,{ball=null}={}){
    const completed=events.at(-1);
    if(this.key!==match?.key||(completed&&completed.sequence<this.delivery)||
       (ball&&this.ball!==null&&ball.sequence<this.ball)){
      this.reset(match?.key);this.delivery=completed?.sequence??-1;this.shot=shot?.sequence??0;
      this.ball=ball?.sequence??null;this.firstDelivery=ball?.delivery??this.delivery+1;
      return null;
    }
    if(ball&&ball.innings===match?.innings&&ball.sequence!==this.ball){
      this.ball=ball.sequence;this.firstDelivery=ball.delivery;this.until=0;this.timing=null;
      this.activeDelivery=-1;this.contactDelivery=-1;
    }
    let next=null,delivery=-1;
    // Read real contact first: the completed result can contain a clamped zone.
    if(shot&&shot.innings===match?.innings&&shot.sequence!==this.shot){
      this.shot=shot.sequence;
      if(shot.delivery>=this.delivery&&shot.delivery>=this.firstDelivery&&
         (!ball||shot.ball===ball.sequence)){
        next=timingForZone(shot.zone);delivery=shot.delivery;this.contactDelivery=delivery;
      }
    }
    if(completed&&completed.innings===match?.innings&&completed.sequence!==this.delivery){
      this.delivery=completed.sequence;
      if(!next&&completed.sequence>=this.firstDelivery&&completed.sequence!==this.contactDelivery){
        const attempted=timingForZone(completed.timing);
        if(attempted){
          next={...attempted,kind:'bad',label:[1,6].includes(completed.timing)?'Late Miss':'Miss'};
        }else if(completed.timing===7){
          next={kind:'leave',label:'Leave'};
        }
        if(next)delivery=completed.sequence;
      }
    }
    // BatTiming can change when the bowler releases the ball or AI plans its
    // shot. Only actual contact or a completed delivery can show feedback.
    if(!playing){
      if(delivery>=0)this.activeDelivery=delivery;
      this.until=0;return null;
    }
    if(next){
      if(delivery!==this.activeDelivery)this.until=now+5000;
      this.timing=next;this.activeDelivery=delivery;
    }
    return now<this.until?this.timing:null;
  }
}

export class TimingStats {
  constructor(){this.reset(null);}
  reset(key){this.key=key;this.sequence=-1;this.counts={bad:0,early:0,good:0,perfect:0,late:0};}
  update(match,events){
    const sequence=events.at(-1)?.sequence??-1;
    if(this.key!==match.key||sequence<this.sequence)this.reset(match.key);
    for(const e of events){
      if(e.sequence<=this.sequence||e.innings!==match.innings)continue;
      const timing=timingForZone(e.timing);
      if(timing)this.counts[timing.kind]++;
    }
    this.sequence=sequence;
    return {...this.counts};
  }
}

// Read the native formatted strings, including dismissal runs/balls, rather
// than rebuilding them from a potentially changed striker after a wicket.
export function readNativePanel(buffer,base,pointer){
  const v=new DataView(buffer),b=new Uint8Array(buffer);
  const valid=(p,size=128)=>Number.isInteger(p)&&p>0x400000&&base+p+size<=buffer.byteLength;
  const u32=p=>v.getUint32(base+p,true);
  if(!valid(pointer))return null;
  const id=v.getUint16(base+pointer+4,true);
  if(!PANEL_IDS.includes(id))return null;
  // f_004b0ab0 activates a native information window with state 2 and hides
  // it with state 3, including when the player skips the presentation.
  if(v.getUint32(base+pointer+0x30,true)!==2)return null;
  let list=u32(pointer+0x34),visible=false;
  const texts=[],seen=new Set();
  for(let i=0;i<128&&valid(list,20)&&!seen.has(list);i++){
    seen.add(list);const node=u32(list+8);
    if(valid(node)&&(b[base+node+0x35]&4)){
      const type=u32(node),ident=v.getUint16(base+node+4,true);
      if(type===0x7936d8&&ident===([310,500].includes(id)?0:10)){
        const x=v.getFloat32(base+pointer+8,true)+v.getFloat32(base+node+8,true);
        const y=v.getFloat32(base+pointer+12,true)+v.getFloat32(base+node+12,true);
        visible=b[base+node+0x53]>0&&x>(id===310?-128:-540)&&x<854&&y>-128&&y<480;
      }
      if(type===0x7936b4&&b[base+node+0x67]>0){
        const p=u32(node+0x7c);
        if(valid(p,1)){
          let end=base+p;while(end<Math.min(base+p+512,b.length)&&b[end])end++;
          let text=new TextDecoder('windows-1252').decode(Uint8Array.from(b.subarray(base+p,end))).trim();
          if(/^\$\d+$/.test(text))text=PANEL_LABELS[Number(text.slice(1))]??'';
          if(text)texts.push({id:ident,text});
        }
      }
    }
    list=u32(list+16);
  }
  return visible&&(texts.length||id===310)?{id,texts}:null;
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
      wickets:v.getUint32(p+16,true),bowler:v.getUint32(p+20,true),flags:v.getUint32(p+24,true),
      timing:v.getUint32(p+28,true)});
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

export class BowlerDeliveries {
  constructor(){this.key=null;this.start=0;this.sequence=-1;}
  update(match,events){
    const sequence=events.at(-1)?.sequence??-1;
    if(sequence<this.sequence)this.key=null;
    this.sequence=sequence;
    const key=match.key+':'+match.bowler.id;
    if(this.key!==key){
      this.start=this.key===null?0:(events.at(-1)?.sequence??-1)+1;
      this.key=key;
    }
    return events.filter(e=>e.innings===match.innings&&e.bowler===match.bowler.id&&e.sequence>=this.start);
  }
}
