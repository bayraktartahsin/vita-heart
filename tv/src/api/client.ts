/**
 * HTTP client for the Vita Heart API. Small on purpose: fetch, JSON, one
 * base URL, one household code. Errors surface as one plain sentence the
 * screen can show; nothing is swallowed.
 */
export type Dose = {
  id: string;
  medId: string;
  name: string | null;
  strength: string | null;
  slot: string;
  food: string | null;
  photo: string | null;
  dueAt: string | null;
  unscheduled: boolean;
  confirmed: boolean;
  recallCount: number;
  status: string;
};

export type Board = {
  household: string;
  greeting: string;
  person: {name: string; age?: number};
  family: {name: string; relation?: string; city?: string}[];
  dueDoses: Dose[];
  clock: Record<string, string>;
  restingHeartRate?: number | null;
  message: {author: string; text: string; ts: string} | null;
  checkedInToday: boolean;
  localHour: number;
  generatedAt: string;
};

export type LiveEvent = {ts: string; kind: string; data: Record<string, unknown>};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export class VitaHeartApi {
  constructor(public baseUrl: string, public household: string) {}

  private url(path: string, params: Record<string, string | number | undefined> = {}) {
    const q = Object.entries({household: this.household, ...params})
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      .join('&');
    return `${this.baseUrl}${path}${q ? `?${q}` : ''}`;
  }

  private async json<T>(input: string, init?: {method?: string; body?: string}): Promise<T> {
    const res = await fetch(input, {...init, headers: {'content-type': 'application/json'}});
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json()).detail ?? detail;
      } catch (_) {
        // the body was not JSON; the status text is the best we have
      }
      throw new ApiError(res.status, detail);
    }
    return (await res.json()) as T;
  }

  board(): Promise<Board> {
    return this.json<Board>(this.url('/board'));
  }

  events(since: string | undefined, waitSeconds = 20): Promise<{events: LiveEvent[]; cursor: string}> {
    return this.json(this.url('/events', {since, wait: waitSeconds}));
  }

  setClock(times: Record<string, string>): Promise<{clock: Record<string, string>}> {
    return this.json(this.url('/clock'), {
      method: 'POST',
      body: JSON.stringify({household: this.household, times}),
    });
  }

  confirmDose(doseId: string): Promise<{id: string; ts: string}> {
    return this.json(this.url('/doses/confirm'), {
      method: 'POST',
      body: JSON.stringify({household: this.household, dose_id: doseId, by: 'tv'}),
    });
  }

  startSession(source: 'watch' | 'recorded' | 'synthetic'): Promise<{id: string; source: string}> {
    return this.json(this.url('/session/start'), {method: 'POST', body: JSON.stringify({household: this.household, source})});
  }

  finishSession(session: string, summary: Record<string, unknown>): Promise<{id: string}> {
    return this.json(this.url('/session/finish'), {method: 'POST', body: JSON.stringify({household: this.household, session, summary})});
  }

  coach(numbers: Record<string, unknown>): Promise<{line: string; fallback: boolean}> {
    return this.json(this.url('/session/coach'), {method: 'POST', body: JSON.stringify({household: this.household, numbers})});
  }

  checkin(): Promise<{ts: string}> {
    return this.json(this.url('/checkin'), {
      method: 'POST',
      body: JSON.stringify({household: this.household, by: 'tv'}),
    });
  }

  health(): Promise<{ok: boolean}> {
    return this.json(`${this.baseUrl}/health`);
  }
}
