import {readMatch,readDeliveries,overCells,nativeStripVisible,BowlerDeliveries,TEAMS,oversText} from './broadcast-state.js';

export function attachBroadcast(M){
  const stage=document.getElementById('stage');
  const bar=document.createElement('section');
  bar.id='broadcast';bar.hidden=true;bar.setAttribute('aria-label','Live match score');
  bar.innerHTML=`<div class="flag"><img data-field="batFlag" alt=""></div>
    <div class="batters panel"><div class="batter"><i>▶</i><b data-field="striker"></b><strong data-field="strikerRuns"></strong><span data-field="strikerBalls"></span></div>
    <div class="batter"><i></i><b data-field="nonStriker"></b><strong data-field="nonStrikerRuns"></strong><span data-field="nonStrikerBalls"></span></div></div>
    <div class="match"><div class="scoreline"><b data-field="teams"></b><strong data-field="score"></strong><span><b data-field="overs"></b><small>OVERS</small></span></div><div class="context" data-field="context"></div></div>
    <div class="bowling panel"><div class="bowler"><b data-field="bowler"></b><strong data-field="figures"></strong><span data-field="bowlerOvers"></span></div><div class="deliveries" data-field="deliveries"></div></div>
    <div class="flag"><img data-field="bowlFlag" alt=""></div>`;
  stage.append(bar);
  const fields=Object.fromEntries([...bar.querySelectorAll('[data-field]')].map(e=>[e.dataset.field,e]));
  const set=(k,v)=>{if(fields[k].textContent!==String(v))fields[k].textContent=v;};
  let last='',warned=false;
  let initialized=false;
  let pulse=0,lastPulse=-Infinity;
  const bowlerDeliveries=new BowlerDeliveries();
  function tick(){
    try{
      const buffer=M.wasmMemory.buffer,v=new DataView(buffer);
      const base=v.getUint32(559428,true);
      if(base>0 && base+0xb02010<buffer.byteLength && !initialized){
        new Uint8Array(buffer).fill(0,base+0xb01000,base+0xb02010);
        new Uint8Array(buffer)[base+0xb00080]=1;initialized=true;
      }
      const match=readMatch(buffer,base);
      const events=match?bowlerDeliveries.update(match,readDeliveries(buffer,base)):[];
      if(base>0)new Uint8Array(buffer)[base+0xb00081]=match&&!(M._c07_in_menu&&M._c07_in_menu())?1:0;
      const nextPulse=base>0?v.getUint32(base+0xb00084,true):0;
      if(nextPulse!==pulse){pulse=nextPulse;lastPulse=performance.now();}
      // The native strip's own render lifecycle controls the replacement.
      // No score ticker in replays, cutscenes, menus or pauses without it.
      const visible=match&&performance.now()-lastPulse<200&&nativeStripVisible(buffer,base)&&!(M._c07_in_menu&&M._c07_in_menu());
      bar.hidden=!visible;
      if(!visible)return;
      const s=match;
      const key=JSON.stringify([s,events]);if(key===last)return;last=key;
      set('striker',s.striker.name);set('strikerRuns',s.striker.runs);set('strikerBalls',s.striker.balls);
      set('nonStriker',s.nonStriker.name);set('nonStrikerRuns',s.nonStriker.runs);set('nonStrikerBalls',s.nonStriker.balls);
      set('teams',TEAMS[s.batting][0]+' v '+TEAMS[s.fielding][0]);
      set('score',s.runs+'-'+s.wickets);set('overs',oversText(s.legalBalls));
      set('bowler',s.bowler.name);set('figures',s.bowler.wickets+'-'+s.bowler.conceded);
      set('bowlerOvers',s.bowler.bowlingOvers+'.'+s.bowler.bowlingBalls);
      const rate=s.legalBalls?(s.runs*6/s.legalBalls).toFixed(2):'0.00';
      set('context',`${s.limit===-1?'TEST':s.limit<=20?'T20 INTERNATIONAL':'ODI'} · ${s.innings+1}${['ST','ND','RD','TH'][s.innings]} INNINGS · RUN RATE ${rate}`);
      for(const [key,id] of [['batFlag',s.batting],['bowlFlag',s.fielding]]){
        const url='/assets/flags/'+TEAMS[id][2]+'.svg';
        if(fields[key].getAttribute('src')!==url){fields[key].src=url;fields[key].alt=TEAMS[id][1];}
      }
      const balls=overCells(events);
      bar.style.setProperty('--extra-rows',Math.floor((balls.length-1)/9));
      fields.deliveries.replaceChildren();
      fields.deliveries.setAttribute('aria-label','This over: deliveries and balls remaining');
      for(let i=0;i<balls.length;i++){
        const e=balls[i],chip=document.createElement('span');
        chip.className='ball'+(!e?' empty':e.kind===4?' wicket':e.runs>=4?' boundary':'');
        chip.textContent=!e?'':e.kind===4?'W':e.kind===2?(e.runs>1?e.runs:'')+'Wd':e.kind===3?(e.runs>1?e.runs:'')+'Nb':String(e.runs);
        fields.deliveries.append(chip);
      }
    }catch(error){bar.hidden=true;if(!warned){console.warn('Broadcast HUD unavailable:',error);warned=true;}}
  }
  const timer=setInterval(tick,100);tick();
  return ()=>{clearInterval(timer);bar.remove();};
}
