import React from 'react';
import {act, fireEvent, render, screen, waitFor} from '@testing-library/react-native';
import {App} from '../src/App';

const board = {
  household: 'AHMET1', greeting: 'Günaydın, Ahmet', person: {name: 'Ahmet', age: 72},
  family: [{name: 'Selin'}], dueDoses: [], restingHeartRate: 61,
  message: {author: 'Selin', text: 'Baba, akşam arayacağım.', ts: '2026-09-05T05:00:00+00:00'},
  checkedInToday: false, localHour: 8, generatedAt: '2026-09-05T05:00:00', clock: {},
};

const dose = {
  id: '2026-09-05#morning#m1', medId: 'm1', name: 'PARACETAMOL', strength: '500 mg', slot: 'morning', food: 'with food',
  photo: null, dueAt: '2026-09-05T05:00', unscheduled: false, confirmed: false, recallCount: 1, status: 'identified',
};

type Init = {method?: string; body?: string};
type FakeResponse = {ok: boolean; status: number; statusText: string; json: () => Promise<unknown>};

function mockFetch(routes: Record<string, (init?: Init) => unknown>) {
  global.fetch = jest.fn(async (url: string, init?: Init): Promise<FakeResponse> => {
    const path = new URL(url).pathname;
    const handler = routes[path];
    if (!handler) {
      return {ok: false, status: 404, statusText: 'not found', json: async () => ({detail: 'no route'})};
    }
    return {ok: true, status: 200, json: async () => handler(init)};
  }) as unknown as typeof fetch;
}

describe('Vita Heart TV', () => {
  it('shows the morning board from the API and lets Ahmet check in', async () => {
    let checkedIn = false;
    mockFetch({
      '/board': () => ({...board, checkedInToday: checkedIn}),
      '/events': () => new Promise(() => {}), // hold the long-poll open
      '/checkin': () => {
        checkedIn = true;
        return {ts: 'now', by: 'tv'};
      },
    });
    render(<App apiBaseUrl="https://api.test" household="AHMET1" />);
    await waitFor(() => expect(screen.getByTestId('greeting').props.children).toBe('Günaydın, Ahmet'));
    expect(screen.getByTestId('card-message')).toBeTruthy();
    await act(async () => {
      fireEvent.press(screen.getByTestId('checkin'));
    });
    await waitFor(() => expect(screen.getByTestId('checked-in')).toBeTruthy());
  });

  it('opens the medication moment and confirms a dose from the remote', async () => {
    let confirmed = false;
    mockFetch({
      '/board': () => ({...board, dueDoses: [{...dose, confirmed}]}),
      '/events': () => new Promise(() => {}),
      '/doses/confirm': () => {
        confirmed = true;
        return {id: dose.id, ts: 'now'};
      },
    });
    render(<App apiBaseUrl="https://api.test" household="AHMET1" />);
    await waitFor(() => expect(screen.getByTestId('open-meds')).toBeTruthy());
    fireEvent.press(screen.getByTestId('open-meds'));
    expect(screen.getByTestId('medication-moment')).toBeTruthy();
    expect(screen.getByText(/Ask the pharmacist/)).toBeTruthy();
    await act(async () => {
      fireEvent.press(screen.getByTestId(`confirm-${dose.id}`));
    });
    await waitFor(() => expect(screen.getByText('✓ Taken')).toBeTruthy());
  });

  it('lets the household set its own times when a dose has none', async () => {
    let clock: Record<string, string> = {};
    mockFetch({
      '/board': () => ({...board, clock, dueDoses: [{...dose, dueAt: null, unscheduled: Object.keys(clock).length === 0}]}),
      '/events': () => new Promise(() => {}),
      '/clock': init => {
        clock = JSON.parse(init?.body ?? '{}').times;
        return {clock};
      },
    });
    render(<App apiBaseUrl="https://api.test" household="AHMET1" />);
    await waitFor(() => expect(screen.getByTestId('open-meds')).toBeTruthy());
    fireEvent.press(screen.getByTestId('open-meds'));
    fireEvent.press(screen.getByTestId('set-clock'));
    expect(screen.getByTestId('time-morning').props.children).toBe('08:00');
    fireEvent.press(screen.getByTestId('earlier-morning'));
    expect(screen.getByTestId('time-morning').props.children).toBe('07:30');
    await act(async () => {
      fireEvent.press(screen.getByTestId('confirm-clock'));
    });
    expect(clock).toEqual({morning: '07:30'});
    await waitFor(() => expect(screen.queryByTestId('set-clock')).toBeNull());
  });

  it('says plainly when the API is unreachable', async () => {
    mockFetch({'/events': () => new Promise(() => {})});
    render(<App apiBaseUrl="https://api.test" household="NOBODY" />);
    await waitFor(() => expect(screen.getByTestId('board-error')).toBeTruthy());
  });

  it('starts on pairing when no household is known', () => {
    mockFetch({});
    render(<App apiBaseUrl="https://api.test" household={null} />);
    expect(screen.getByTestId('pairing')).toBeTruthy();
  });
});
