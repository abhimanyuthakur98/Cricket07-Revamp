// Hosted playtest: the launcher's manifest installs the prepared archive.
// Only small roster databases are fetched at launch; no Python server required.
window.revampBeforeLaunch=async function(){
  const response=await fetch('/data/playtest.json',{cache:'no-store'});
  if(!response.ok)throw new Error('Playtest configuration unavailable. Reload the page.');
  const config=await response.json();
  window.revampDatabases=Object.fromEntries(await Promise.all(['T20','ODI','Test'].map(async format=>{
    const r=await fetch(config.formats[format]+'?v='+config.version,{cache:'no-store'});
    if(!r.ok)throw new Error('The '+format+' squad database could not load.');
    const data=new Uint8Array(await r.arrayBuffer());
    if(data.length!==620140)throw new Error('Incomplete '+format+' squad database.');
    return [format,data];
  })));
  const ratings=await fetch(config.squadRatings+'?v='+config.version,{cache:'no-store'});
  if(!ratings.ok)throw new Error('Squad strength data unavailable. Reload the page.');
  window.revampSquadRatings=await ratings.json();
  document.getElementById('revamp-message').textContent='Playtest · squads follow your confirmed overs.';
};
window.revampAttach=async function(M){
  const {attach}=await import('/roster-runtime.js');window.revampStop=attach(M);
  window.revampStopSquadRatings?.();
  const {attachSquadRatings}=await import('/squad-ratings.mjs?v=wide-broadcast-v16');
  window.revampStopSquadRatings=attachSquadRatings(M,window.revampSquadRatings);
  window.revampStopBroadcast?.();
  const {attachBroadcast}=await import('/broadcast.js?v=result-feedback-v18');window.revampStopBroadcast=attachBroadcast(M);
};
