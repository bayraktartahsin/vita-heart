import {shift} from '../src/screens/ClockSetup';

test('shift wraps around midnight in both directions', () => {
  expect(shift('08:00', 30)).toBe('08:30');
  expect(shift('23:45', 30)).toBe('00:15');
  expect(shift('00:10', -30)).toBe('23:40');
});
