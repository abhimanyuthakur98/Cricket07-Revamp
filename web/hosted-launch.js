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
  document.getElementById('revamp-message').textContent='Playtest · squads follow your confirmed overs.';
};
window.revampAttach=async function(M){
  const {attach}=await import('/roster-runtime.js');window.revampStop=attach(M);
  const {attachBroadcast}=await import('/broadcast.js');window.revampStopBroadcast=attachBroadcast(M);
};
