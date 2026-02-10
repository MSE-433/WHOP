export const EVENT_ROUNDS = new Set([6, 9, 12, 17, 21]);

export function roundToTime(round: number): string {
  // Round 1 = 12:00 PM (noon), each round = 1 hour
  const hour = (round + 11) % 24;
  const period = hour >= 12 ? 'PM' : 'AM';
  const display = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  return `${display}:00 ${period}`;
}

export function isEventRound(round: number): boolean {
  return EVENT_ROUNDS.has(round);
}
