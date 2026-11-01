'use strict';
(() => {
  const element = id => document.getElementById(id);
  let snapshot;
  function render() {
    const teams = snapshot?.formats[element('format').value]?.teams || [];
    const team = teams.find(t => t.name === element('team').value);
    element('players').replaceChildren();
    element('empty').hidden = !!team;
    element('team-title').textContent = team?.name || 'Players';
    element('freshness').textContent = team?.stale ? 'Latest match over 30 days old' : '';
    element('team-meta').textContent = team ? `${team.players.length} recent players · Latest source match ${team.latestMatch}` : '';
    for (const player of team?.players || []) {
      const row = document.createElement('tr');
      const values = [player.name, player.ratings.batting ?? '—', player.ratings.bowling ?? '—',
        player.matches, player.stats.runs, player.stats.wickets, player.lastPlayed, player.ratings.confidence];
      values.forEach((value, i) => {
        const cell = document.createElement('td');
        cell.textContent = value;
        if (i === 1 || i === 2) cell.className = 'rating';
        row.append(cell);
      });
      element('players').append(row);
    }
  }
  function updateTeams() {
    const previous = element('team').value;
    const teams = snapshot?.formats[element('format').value]?.teams || [];
    element('team').replaceChildren(...teams.map(team => {
      const option = document.createElement('option');
      option.value = option.textContent = team.name;
      return option;
    }));
    if (teams.some(t => t.name === previous)) element('team').value = previous;
    else if (teams.some(t => t.name === 'India')) element('team').value = 'India';
    render();
  }
  async function load() {
    element('reload').disabled = true;
    element('error').hidden = true;
    try {
      // Static snapshots also work on GitHub Pages; local server exposes the same JSON at /api/rosters.
      const response = await fetch('data/rosters.json', {cache: 'no-store'});
      if (!response.ok) throw new Error('No roster snapshot available. Run python -m roster.refresh.');
      const next = await response.json();
      if (next.schemaVersion !== 1 || !next.formats) throw new Error('Unsupported roster snapshot.');
      snapshot = next;
      const age = Math.floor((Date.now() - new Date(next.generatedAt).getTime()) / 86400000);
      element('status').textContent = `Snapshot date ${next.asOf} · Refreshed ${new Date(next.generatedAt).toLocaleString()}${age >= 2 ? ' · Outdated snapshot: refresh the source data.' : ''}`;
      element('squad-policy').textContent = next.squadPolicy;
      element('rating-policy').textContent = next.ratingPolicy;
      updateTeams();
    } catch (error) {
      element('error').textContent = error.message;
      element('error').hidden = false;
      element('status').textContent = snapshot ? 'Reload failed. Showing the previous dated snapshot.' : 'Roster data unavailable.';
    } finally {
      element('reload').disabled = false;
    }
  }
  element('format').addEventListener('change', updateTeams);
  element('team').addEventListener('change', render);
  element('reload').addEventListener('click', load);
  load();
})();
