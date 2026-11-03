// A transparent game squad model, on the same 1–99 scale as player form.
// ICC team points measure results and are not an average of player ratings.
export const BATTING_WEIGHTS = [1, 1, 1, 1, 1, .9, .8, .5, .35, .25, .2];

const validRating = value => Number.isFinite(value) && value >= 1 && value <= 99;

export function rateSquad(team, format, ids = team?.startingXI) {
  const unavailable = reason => ({overall:null, batting:null, bowling:null, reason});
  if (!team || !Array.isArray(ids) || ids.length !== 11 || new Set(ids).size !== 11)
    return unavailable('No complete rated XI');
  const players = new Map(team.players.map(p => [p.id, p]));
  const xi = ids.map(id => players.get(id));
  if (xi.some(p => !p)) return unavailable('XI contains players without recent data');
  let battingTotal = 0, knownWeight = 0, battingKnown = 0;
  xi.forEach((p, i) => {
    if (validRating(p.ratings?.batting)) {
      battingTotal += p.ratings.batting * BATTING_WEIGHTS[i];
      knownWeight += BATTING_WEIGHTS[i];
      battingKnown++;
    }
  });
  const coverage = knownWeight / BATTING_WEIGHTS.reduce((a, b) => a + b, 0);
  const batting = battingKnown >= 6 && coverage >= .7 ? battingTotal / knownWeight : null;
  const attackSize = format === 'Test' ? 4 : 5;
  // Workload chooses the likely attack, rather than cherry-picking high-rated
  // occasional bowlers. Missing ratings never silently become average ability.
  const attack = xi.filter(p => p.legalBalls > 0 && (p.bowls || p.legalBalls >= 60))
    .sort((a, b) => b.legalBalls - a.legalBalls).slice(0, attackSize);
  const bowling = attack.length === attackSize && attack.every(p => validRating(p.ratings?.bowling))
    ? attack.reduce((sum, p) => sum + p.ratings.bowling, 0) / attackSize : null;
  const overall = batting !== null && bowling !== null ? 2 * batting * bowling / (batting + bowling) : null;
  const limited = xi.some(p => p.ratings?.confidence !== 'established');
  return {overall, batting, bowling, battingKnown, coverage, limited,
    attack:attack.map(p => p.id),
    reason:overall === null ? 'Insufficient recent batting or bowling data' :
      coverage < 1 || limited ? 'Limited recent sample' : 'Recent form'};
}
