// Short matches share the T20 squad, but keep their actual overs on screen.
export function formatForOvers(overs) {
  if (overs === -1) return 'Test';
  if (Number.isInteger(overs) && overs > 0 && overs <= 20) return 'T20';
  if (overs === 50) return 'ODI';
  return null;
}

export function formatLabel(overs) {
  if (overs === -1) return 'TEST';
  if (overs === 50) return 'ODI';
  if (Number.isInteger(overs) && overs > 0 && overs <= 20) return `T${overs}`;
  return overs > 0 ? `${overs} OVERS` : 'MATCH';
}
