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

export type Summary = {day: string; text: string; signals: {kind: string; note: string; weight: number}[]; ts: string};
export type TraceStep = {ts?: string; agent: string; tool: string; said?: string; med?: string};
export type Message = {ts: string; author: string; text: string};

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

  /**
   * At most a few requests at once.
   *
   * Every event used to start its own board fetch. A batch of ten arriving together —
   * a reset, or a rehearsal — fired ten at once, and after a burst like that the
   * television stopped talking to the API altogether while still rendering its last
   * frame and reporting itself live. The long poll is exempt: it is one request that is
   * meant to be held open, and nothing should ever queue behind it.
   */
  private inFlight = 0;
  private waiting: (() => void)[] = [];

  private async gate<T>(fn: () => Promise<T>): Promise<T> {
    if (this.inFlight >= 3) {
      await new Promise<void>(r => this.waiting.push(r));
    }
    this.inFlight += 1;
    try {
      return await fn();
    } finally {
      this.inFlight -= 1;
      this.waiting.shift()?.();
    }
  }

  /**
   * Every request has a deadline.
   *
   * Vega's fetch has none of its own. A long-poll whose socket dies quietly leaves the
   * await pending for ever: no rejection, so no retry, and the screen goes on saying
   * "live" while nothing reaches it again. That is how a recording dies without
   * producing a single error — the television simply stops obeying, still lit.
   */
  private async json<T>(input: string, init?: {method?: string; body?: string},
                        timeoutMs = 20000, held = false): Promise<T> {
    return held ? this.request<T>(input, init, timeoutMs)
                : this.gate(() => this.request<T>(input, init, timeoutMs));
  }

  private async request<T>(input: string, init?: {method?: string; body?: string},
                           timeoutMs = 20000): Promise<T> {
    const ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const run = async (): Promise<T> => {
      const res = await fetch(input, {
        ...init, headers: {'content-type': 'application/json'}, signal: ctrl?.signal,
      } as any);
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
    };
    // Promise.race as well as the abort: if this runtime ignores the signal, the loop
    // must still be released, or the deadline is decorative.
    const deadline = new Promise<never>((_resolve, reject) => {
      timer = setTimeout(() => {
        ctrl?.abort();
        reject(new ApiError(0, `no answer within ${timeoutMs} ms`));
      }, timeoutMs);
    });
    try {
      return await Promise.race([run(), deadline]);
    } finally {
      if (timer !== undefined) {
        clearTimeout(timer);
      }
    }
  }

  board(): Promise<Board> {
    return this.json<Board>(this.url('/board'));
  }

  events(since: string | undefined, waitSeconds = 25): Promise<{events: LiveEvent[]; cursor: string}> {
    // the server holds the request for `waitSeconds`; anything past that plus a margin
    // is a socket that is never going to answer
    return this.json(this.url('/events', {since, wait: waitSeconds}), undefined,
                     waitSeconds * 1000 + 10000, true);
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

  summary(): Promise<{summary: Summary | null}> {
    return this.json(this.url('/family/summary'));
  }

  trace(): Promise<{steps: TraceStep[]}> {
    return this.json(this.url('/trace'));
  }

  messages(): Promise<{messages: Message[]}> {
    return this.json(this.url('/family/messages'));
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
