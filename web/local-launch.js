// Install refreshed files before the WASM worker locks its OPFS handles.
window.revampBeforeLaunch = async function () {
  $('panel').classList.remove('hidden');
  show('loading');
  status('Refreshing latest international squads and player form…');
  const response=await fetch('/api/launch',{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({format:'T20'}),
  });
  const result=await response.json();
  if (!response.ok) throw new Error(result.error||'Roster preparation failed');
  status('Installing the updated team database…');
  const archive=await fetch('/local-game/Data/data.gob?v='+result.hash,{cache:'no-store'});
  if (!archive.ok) throw new Error('Updated game archive unavailable');
  const writer=await (await fileHandle(await gameDir(true),'Data/data.gob',true)).createWritable();
  await archive.body.pipeTo(writer);
  window.revampDatabases=Object.fromEntries(await Promise.all(['T20','ODI','Test'].map(async format=>{
    const response=await fetch('/local-game/'+format+'.cdf?v='+result.hash,{cache:'no-store'});
    if (!response.ok) throw new Error('Missing '+format+' roster');
    return [format,new Uint8Array(await response.arrayBuffer())];
  })));
  const ratings=await fetch('/local-game/squad-ratings.json?v='+result.hash,{cache:'no-store'});
  if (!ratings.ok) throw new Error('Squad strength data unavailable');
  window.revampSquadRatings=await ratings.json();
  document.getElementById('revamp-message').textContent=result.warning||'T20 international · squads follow the confirmed in-game overs';
};

window.revampAttach = async function (M) {
  const {attach}=await import('/roster-runtime.js');
  window.revampStop=attach(M);
  window.revampStopSquadRatings?.();
  const {attachSquadRatings}=await import('/squad-ratings.mjs?v=wide-broadcast-v16');
  window.revampStopSquadRatings=attachSquadRatings(M,window.revampSquadRatings);
  if (document.body.dataset.broadcastUi === 'true') {
    window.revampStopBroadcast?.();
    const {attachBroadcast}=await import('/broadcast.js?v=result-feedback-v18');
    window.revampStopBroadcast=attachBroadcast(M);
  }
};
