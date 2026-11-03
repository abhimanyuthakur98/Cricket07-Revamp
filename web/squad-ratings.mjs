import {rateSquad} from './squad-rating-model.mjs';
import {formatForOvers} from './formats.mjs';
import {attachGameLayout} from './game-layout.mjs?v=wide-broadcast-v16';

// The Play Now screen has two opposing badges and native rating positions.
// Stadium and XI menus must not receive an overlay in those same positions.
const SELECTION_SCREENS = new Set([11]);
export function readSelection(buffer, inMenu) {
  if (!inMenu || buffer.byteLength <= 559432) return null;
  const view = new DataView(buffer), base = view.getUint32(559428, true);
  if (!base || base + 0x95bfec > buffer.byteLength) return null;
  const screen = view.getUint32(base + 0x95bfe8, true);
  if (!screen || base + screen + 6 > buffer.byteLength) return null;
  if (!SELECTION_SCREENS.has(view.getUint16(base + screen + 4, true))) return null;
  return {teams:[view.getUint32(base + 0x92f8e8, true), view.getUint32(base + 0x9303e0, true)],
    overs:view.getInt32(base + 0x930eb4, true)};
}

export function attachSquadRatings(M, data) {
  const stage = document.getElementById('stage'), releaseLayout = attachGameLayout(stage);
  const canvas = stage.querySelector('canvas');
  // Retire the earlier footer and load the matching style revision together.
  for (const old of stage.querySelectorAll('#squad-ratings, #team-badge-ratings')) old.remove();
  const stylesheet = document.createElement('link');stylesheet.rel = 'stylesheet';
  stylesheet.href = '/game-layout.css?v=full-canvas-v5';
  let stylesReady = false;
  stylesheet.onload = () => {stylesReady = true;tick();};
  stylesheet.onerror = () => console.warn('Team rating styles could not load.');
  const overlay = document.createElement('section');overlay.id = 'team-badge-ratings';overlay.hidden = true;
  overlay.setAttribute('aria-label', 'Team squad strengths by format, out of 99');stage.append(overlay);
  // Follow the rendered canvas, including fullscreen and letterboxing.
  function align() {
    if (overlay.hidden || !canvas) return;
    const game = canvas.getBoundingClientRect(), parent = stage.getBoundingClientRect();
    Object.assign(overlay.style, {left:`${game.left-parent.left-stage.clientLeft}px`,
      top:`${game.top-parent.top-stage.clientTop}px`, width:`${game.width}px`, height:`${game.height}px`});
    // Native frontend controls use a centred 640 × 480 coordinate space.
    overlay.style.setProperty('--rating-unit', `${game.height / 480}px`);
  }
  const resize = new ResizeObserver(align);resize.observe(stage);if (canvas) resize.observe(canvas);
  let previous = '', warned = false;
  const metric = value => value === null ? '—' : String(Math.round(value));
  function tick() {
    try {
      const selection = stylesReady ? readSelection(M.wasmMemory.buffer, !!M._c07_in_menu?.()) : null;
      overlay.hidden = !selection;stage.dataset.squadRatings = selection ? 'true' : 'false';
      if (!selection) return;
      align();
      const key = JSON.stringify(selection);if (previous === key) return;previous = key;
      const active = formatForOvers(selection.overs);overlay.replaceChildren();
      for (const id of selection.teams) {
        const ratings = document.createElement('dl');ratings.className = 'squad-rating-team';
        ratings.setAttribute('aria-label', `${data.teamNames?.[id] || 'Team '+id} squad strength out of 99`);
        for (const format of ['T20', 'ODI', 'Test']) {
          const team = data.formats[format]?.teams[id], rating = rateSquad(team, format);
          const row = document.createElement('div');row.dataset.active = String(format === active);
          row.title = team ? `${rating.reason}. Latest ${format} XI: ${team.latestMatch}${team.stale ? ' (older squad)' : ''}. Batting ${metric(rating.batting)}, bowling ${metric(rating.bowling)}. ${format === 'T20' ? 'Used for matches of 20 overs or fewer. ' : ''}* limited recent sample; — insufficient data.` : 'No complete recent squad available';
          const label = document.createElement('dt'), value = document.createElement('dd');
          label.textContent = format;value.textContent = metric(rating.overall);
          if (rating.overall !== null && (rating.limited || rating.coverage < 1)) {
            const limited = document.createElement('sup');limited.textContent = '*';value.append(limited);
          }
          row.append(label, value);ratings.append(row);
        }
        overlay.append(ratings);
      }
    } catch (error) {
      overlay.hidden = true;stage.dataset.squadRatings = 'false';
      if (!warned) {console.warn('Squad strengths unavailable:', error);warned = true;}
    }
  }
  const timer = setInterval(tick, 150);document.head.append(stylesheet);tick();
  return () => {clearInterval(timer);resize.disconnect();stylesheet.onload = null;stylesheet.remove();overlay.remove();delete stage.dataset.squadRatings;releaseLayout();};
}
