import assert from 'node:assert/strict';
import {rateSquad} from '../../web/squad-rating-model.mjs';
import {formatLabel, formatForOvers} from '../../web/formats.mjs';
import {readSelection} from '../../web/squad-ratings.mjs';

const players = Array.from({length:12}, (_, i) => ({id:String(i), slot:100 + i,
  ratings:{batting:60, bowling:40, confidence:'established'}, legalBalls:i >= 6 ? 300 : 0, bowls:i >= 6}));
const team = {players, startingXI:players.slice(0,11).map(p => p.id)};
let result = rateSquad(team, 'T20');
assert.equal(result.batting, 60);
assert.equal(result.bowling, 40);
assert.equal(result.overall, 48); // Harmonic balance, before display rounding.
assert.equal(result.limited, false);
// A strong reserve doesn't inflate the XI; an actual substitution does.
players[11].ratings.batting = 99;players[11].ratings.bowling = 99;
assert.equal(rateSquad(team, 'T20').overall, 48);
const swapped = [...team.startingXI];swapped[10] = '11';
assert.ok(rateSquad(team, 'T20', swapped).overall > 48);
// Batting order matters, and a cameo bowler cannot displace the main attack.
players[0].ratings.batting = 90;
const reverse = [...team.startingXI].reverse();
assert.ok(rateSquad(team, 'ODI').batting > rateSquad(team, 'ODI', reverse).batting);
players[0].bowls = true;players[0].legalBalls = 1;players[0].ratings.bowling = 99;
assert.ok(!rateSquad(team, 'ODI').attack.includes('0'));
players[6].legalBalls = 0;
players[0].legalBalls = 0;
assert.equal(rateSquad(team, 'ODI').bowling, null);
assert.equal(rateSquad(team, 'Test').bowling, 40); // Four bowlers suffice in Tests.
players[7].ratings.bowling = null;
assert.equal(rateSquad(team, 'Test').overall, null);
// Missing top-order data is not filled with a neutral 50 or ignored silently.
players.slice(0,5).forEach(p => p.ratings.batting = null);
assert.equal(rateSquad(team, 'T20').batting, null);
assert.equal(rateSquad(null, 'Test').overall, null);
assert.equal(rateSquad(team, 'Test', Array(11).fill('1')).overall, null);
assert.equal(rateSquad(team, 'Test', [...team.startingXI.slice(0,10), 'unknown']).overall, null);
for (const n of [1,5,10,15,20]) {
  assert.equal(formatLabel(n), `T${n}`);
  assert.equal(formatForOvers(n), 'T20');
}
assert.equal(formatLabel(50), 'ODI');assert.equal(formatLabel(-1), 'TEST');
assert.equal(formatLabel(30), '30 OVERS');assert.equal(formatLabel(0), 'MATCH');

const buffer = new ArrayBuffer(0x1100000), v = new DataView(buffer), base = 0x1000, root = 0xa00000;
v.setUint32(559428, base, true);v.setUint32(base + 0x95bfe8, root, true);
v.setUint16(base + root + 4, 11, true);
v.setUint32(base + 0x92f8e8, 13, true);v.setUint32(base + 0x9303e0, 0, true);
v.setInt32(base + 0x930eb4, 5, true);
assert.deepEqual(readSelection(buffer, true), {teams:[13,0], overs:5});
assert.equal(readSelection(buffer, false), null);
// Badge positions belong to team selection, never to stadium/XI menus or play.
for (const screen of [1,9,12]) {
  v.setUint16(base + root + 4, screen, true);assert.equal(readSelection(buffer, true), null);
}
v.setUint32(base + 0x95bfe8, 0xffffffff, true);assert.equal(readSelection(buffer, true), null);
console.log('Squad model, actual-overs labels and selection visibility passed.');
