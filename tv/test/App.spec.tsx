import React from 'react';
import {act, fireEvent, render, screen, waitFor} from '@testing-library/react-native';
import {App} from '../src/App';

const board = {
  household: 'AHMET1', greeting: 'Günaydın, Ahmet', person: {name: 'Ahmet', age: 72},
  family: [{name: 'Selin'}], dueDoses: [], restingHeartRate: 61,
  message: {author: 'Selin', text: 'Baba, akşam arayacağım.', ts: '2026-09-05T05:00:00+00:00'},
  checkedInToday: false, localHour: 8, generatedAt: '2026-09-05T05:00:00',
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
