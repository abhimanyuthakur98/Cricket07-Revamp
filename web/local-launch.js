// This hook runs before the compiled game starts, while OPFS files are still unlocked.
window.revampBeforeLaunch = async function () {
  const format = document.getElementById('revamp-format').value;
  $('panel').classList.remove('hidden');
  show('loading');
  status('Refreshing current players and form…');
  const response = await fetch('/api/launch', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({format}),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Roster preparation failed');
  status('Installing the updated team database…');
  const archive = await fetch('/local-game/Data/data.gob?v=' + result.hash, {cache: 'no-store'});
  if (!archive.ok) throw new Error('Updated game archive unavailable');
  const writer = await (await fileHandle(await gameDir(true), 'Data/data.gob', true)).createWritable();
  await archive.body.pipeTo(writer);
  document.getElementById('revamp-format').disabled = true;
  document.getElementById('revamp-message').textContent = result.warning || `${result.players} players updated for ${format}.`;
};
