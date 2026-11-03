import {readMatch,readDeliveries,readShot,readDismissal,readNativePanel,readBallStart,liveMatchVisible,chaseState,ShotFeedback,DismissalNotice,
  PANEL_IDS,PANEL_STATE,overCells,nativeStripVisible,readDeliverySpeed,BowlerDeliveries,TEAMS,oversText} from './broadcast-state.js?v=result-feedback-v18';
import {formatLabel} from './formats.mjs';
import {attachGameLayout} from './game-layout.mjs?v=wide-broadcast-v16';
import {readGuestBase} from './engine-layout.mjs?v=engine-compat-v19';

export function attachBroadcast(M){
  const stage=document.getElementById('stage');
  const releaseLayout=attachGameLayout(stage);
  const stylesheet=document.createElement('link');stylesheet.rel='stylesheet';
  stylesheet.href='/broadcast.css?v=result-feedback-v18';let stylesReady=false;
  stylesheet.onload=()=>{stylesReady=true;tick();};
  stage.classList.add('broadcast-stage');
  const hud=document.createElement('div');hud.id='broadcast-ui';stage.append(hud);
  const bar=document.createElement('section');
  bar.id='broadcast';bar.className='broadcast-surface';bar.hidden=true;bar.setAttribute('aria-label','Live match score');
  bar.innerHTML=`<div class="flag"><img data-field="batFlag" alt=""></div>
    <div class="batters panel"><div class="batter"><i>▶</i><b data-field="striker"></b><strong data-field="strikerRuns"></strong><span data-field="strikerBalls"></span></div>
    <div class="batter"><i></i><b data-field="nonStriker"></b><strong data-field="nonStrikerRuns"></strong><span data-field="nonStrikerBalls"></span></div></div>
    <div class="match"><div class="scoreline"><b data-field="teams"></b><strong data-field="score"></strong><span><b data-field="overs"></b><small>OVERS</small></span></div><div class="context" data-field="context"></div><div class="chase" data-field="chase" hidden></div></div>
    <div class="bowling panel"><div class="bowler"><b data-field="bowler"></b><strong data-field="figures"></strong><span data-field="bowlerOvers"></span></div><div class="deliveries" data-field="deliveries"></div></div>
    <div class="flag"><img data-field="bowlFlag" alt=""></div>
    <div id="broadcast-feedback" hidden>
      <div id="broadcast-timing" hidden><span>Shot Timing :</span><strong data-timing="label"></strong></div>
      <div id="broadcast-speed" hidden aria-label="Delivery speed"><span>Delivery Speed</span><strong data-field="speed"></strong></div>
    </div>`;
  hud.append(bar);
  const card=document.createElement('aside');card.id='broadcast-card';card.className='broadcast-surface';card.hidden=true;
  card.setAttribute('aria-label','Match update');hud.append(card);
  const timing=bar.querySelector('#broadcast-timing'),timingLabel=timing.querySelector('[data-timing="label"]');
  const feedbackRow=bar.querySelector('#broadcast-feedback'),speedReadout=bar.querySelector('#broadcast-speed');
  timing.setAttribute('aria-label','Shot timing');
  const fields=Object.fromEntries([...bar.querySelectorAll('[data-field]')].map(e=>[e.dataset.field,e]));
  const set=(k,v)=>{if(fields[k].textContent!==String(v))fields[k].textContent=v;};
  let last='',warned=false;
  let initialized=false;
  let pulse=0,lastPulse=-Infinity;
  const bowlerDeliveries=new BowlerDeliveries();
  const feedback=new ShotFeedback(),wicketNotice=new DismissalNotice();
  const panelPulses=Array(PANEL_IDS.length).fill(0),panelTimes=Array(PANEL_IDS.length).fill(-Infinity);
  let lastCard='';
  function nativePanel(buffer,base,id){
    if(!initialized)return null;
    const p=base+PANEL_STATE+PANEL_IDS.indexOf(id)*8;
    return readNativePanel(buffer,base,new DataView(buffer).getUint32(p+4,true));
  }
  function updateCard(buffer,base,now,inMenu,dismissal){
    card.hidden=true;if(inMenu||!initialized)return;
    if(dismissal.active){
      if(!dismissal.player)return;
      const p=dismissal.player,key=JSON.stringify(['out',p]);card.hidden=false;
      card.dataset.kind='dismissal';
      if(key===lastCard)return;lastCard=key;card.replaceChildren();
      const title=document.createElement('p');title.className='card-eyebrow';title.textContent='BATTER DISMISSED';
      const name=document.createElement('h2');name.textContent=p.name;
      const metrics=document.createElement('dl');metrics.className='card-metrics';
      for(const [label,value] of [['RUNS',p.runs],['BALLS',p.balls],['STRIKE RATE',p.balls?(p.runs*100/p.balls).toFixed(1):'—']]){
        const metric=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');
        dt.textContent=label;dd.textContent=value;metric.append(dt,dd);metrics.append(metric);
      }
      card.append(title,name,metrics);return;
    }
    const v=new DataView(buffer),panels=[];
    for(let i=0;i<PANEL_IDS.length;i++){
      // Routine batter/bowler/over statistics already live in the score footer.
      // Only exceptional match messages and player-of-match notices get cards.
      if(![360,500].includes(PANEL_IDS[i]))continue;
      const p=base+PANEL_STATE+i*8,pulse=v.getUint32(p,true);
      if(pulse!==panelPulses[i]){panelPulses[i]=pulse;panelTimes[i]=now;}
      if(now-panelTimes[i]<200){
        const panel=readNativePanel(buffer,base,v.getUint32(p+4,true));
        if(panel)panels.push(panel);
      }
    }
    const panel=panels.at(-1);
    if(!panel)return;
    card.dataset.kind='update';
    card.hidden=false;
    const key=JSON.stringify(panel);if(key===lastCard)return;lastCard=key;
    card.replaceChildren();
    const title=document.createElement('p');title.className='card-eyebrow';
    title.textContent=({101:'AT THE CREASE',102:'BATTER STATISTICS',103:'BATTER DISMISSED',201:'BOWLER',202:'BOWLING FIGURES',300:'NEXT OVER',360:'PLAYER OF THE MATCH',370:'PARTNERSHIP',400:'CAPTAIN',500:'MATCH MESSAGE'})[panel.id]??'MATCH UPDATE';
    card.append(title);
    const labels=panel.texts.filter(t=>t.id>=100);
    const values=panel.texts.filter(t=>t.id<100);
    const metrics=document.createElement('dl');metrics.className='card-metrics';
    for(const value of values){
      const label=labels.find(t=>t.id-80===value.id||(panel.id===103&&t.id===100&&value.id===12));
      if(label){
        const metric=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');
        dt.textContent=label.text;dd.textContent=value.text;metric.append(dt,dd);metrics.append(metric);
      }else{
        const row=document.createElement(value.id===11?'h2':'p');row.textContent=value.text;card.append(row);
      }
    }
    if(metrics.childElementCount)card.append(metrics);
  }
  function tick(){
    try{
      const buffer=M.wasmMemory.buffer,v=new DataView(buffer);
      const base=readGuestBase(buffer);
      if(base===null){bar.hidden=true;card.hidden=true;timing.hidden=true;return;}
      if(base>0 && base+0xb02010<buffer.byteLength && !initialized){
        if(v.getUint8(base+0xb00080)!==1){
          new Uint8Array(buffer).fill(0,base+0xb01000,base+0xb02010);
          new Uint8Array(buffer).fill(0,base+0xb000c0,base+0xb00200);
          new Uint8Array(buffer).fill(0,base+0xb00200,base+0xb00220);
          new Uint8Array(buffer).fill(0,base+0xb00240,base+0xb00250);
          new Uint8Array(buffer).fill(0,base+0xb00280,base+0xb002a4);
        }
        new Uint8Array(buffer)[base+0xb00080]=1;initialized=true;
      }
      const match=readMatch(buffer,base);
      const history=match?readDeliveries(buffer,base):[];
      const events=match?bowlerDeliveries.update(match,history):[];
      const inMenu=!!(M._c07_in_menu&&M._c07_in_menu()),now=performance.now();
      if(initialized)new Uint8Array(buffer)[base+0xb00081]=inMenu?0:1;
      const ball=readBallStart(buffer,base);
      const dismissal=wicketNotice.update(readDismissal(buffer,base),match,nativePanel(buffer,base,103),{ball,inMenu});
      // Keep the game's original duck sprite and frame callback on the canvas.
      const duck=!!(initialized&&!inMenu&&match&&nativePanel(buffer,base,310));
      updateCard(buffer,base,now,inMenu,dismissal);
      const nextPulse=base>0?v.getUint32(base+0xb00084,true):0;
      if(nextPulse!==pulse){pulse=nextPulse;lastPulse=performance.now();}
      const playing=!!(match&&stylesReady&&!inMenu&&!dismissal.active&&!duck&&card.hidden&&liveMatchVisible(buffer,base));
      const speed=playing?readDeliverySpeed(buffer,base,{match,ball}):null;
      set('speed',speed??'');
      const lastTiming=feedback.update(match,history,readShot(buffer,base),now,playing,{ball});
      // Brief native score-strip slide-outs must not consume the shot's timer.
      // Keep feedback in the compact strip; menus, dismissals and replays hide it.
      const visible=playing&&((now-lastPulse<200&&nativeStripVisible(buffer,base))||lastTiming||speed);
      bar.hidden=!visible;timing.hidden=!lastTiming;
      speedReadout.hidden=!speed;feedbackRow.hidden=!lastTiming&&!speed;
      stage.dataset.broadcastFeedback=String(!feedbackRow.hidden);
      timing.dataset.quality=lastTiming?.kind??'none';timingLabel.textContent=lastTiming?.label??'';
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
      set('context',`${formatLabel(s.limit)} · ${s.innings+1}${['ST','ND','RD','TH'][s.innings]} INN · CRR ${rate}`);
      const chase=chaseState(s);fields.chase.hidden=!chase;
      if(chase){
        const message=chase.needed===0?'TARGET REACHED':chase.finished?'INNINGS COMPLETE':
          chase.balls===null?`NEED ${chase.needed} TO WIN`:`NEED ${chase.needed} FROM ${chase.balls} BALL${chase.balls===1?'':'S'}`;
        set('chase',`${message} · TARGET ${chase.target}${chase.rate===null?'':` · RRR ${chase.rate.toFixed(2)}`}`);
      }
      for(const [key,id] of [['batFlag',s.batting],['bowlFlag',s.fielding]]){
        const url='/assets/flags/'+TEAMS[id][2]+'.svg';
        if(fields[key].getAttribute('src')!==url){fields[key].src=url;fields[key].alt=TEAMS[id][1];}
      }
      const balls=overCells(events);
      fields.deliveries.style.setProperty('--delivery-rows',Math.max(1,Math.ceil(balls.length/9)));
      fields.deliveries.replaceChildren();
      fields.deliveries.setAttribute('aria-label','This over: deliveries and balls remaining');
      for(let i=0;i<balls.length;i++){
        const e=balls[i],chip=document.createElement('span');
        chip.className='ball'+(!e?' empty':e.kind===4?' wicket':e.runs>=4?' boundary':'');
        chip.textContent=!e?'':e.kind===4?'W':e.kind===2?(e.runs>1?e.runs:'')+'Wd':e.kind===3?(e.runs>1?e.runs:'')+'Nb':String(e.runs);
        fields.deliveries.append(chip);
      }
    }catch(error){bar.hidden=true;card.hidden=true;timing.hidden=true;if(!warned){console.warn('Broadcast HUD unavailable:',error);warned=true;}}
  }
  const timer=setInterval(tick,100);document.head.append(stylesheet);tick();
  return ()=>{clearInterval(timer);stylesheet.onload=null;stylesheet.remove();hud.remove();stage.classList.remove('broadcast-stage');delete stage.dataset.broadcastFeedback;stage.style.removeProperty('--extra-rows');releaseLayout();};
}
