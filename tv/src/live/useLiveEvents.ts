/**
 * The television's one live channel: a long-poll against /events.
 *
 * Why not SSE: the API runs on Lambda behind API Gateway, which buffers the
 * whole response. A long-poll gives sub-second delivery with the same shape
 * the client would use for a stream, and reconnects on its own.
 */
import {useEffect, useRef, useState} from 'react';
import type {LiveEvent, VitaHeartApi} from '../api/client';

export type LiveState = 'connecting' | 'live' | 'retrying';

export function useLiveEvents(api: VitaHeartApi | null, onEvent: (e: LiveEvent) => void): LiveState {
  const [state, setState] = useState<LiveState>('connecting');
  const handler = useRef(onEvent);
  handler.current = onEvent;

  useEffect(() => {
    if (!api) {
      return;
    }
    let alive = true;
    let cursor: string | undefined;
    let backoff = 1000;

    const loop = async () => {
      while (alive) {
        try {
          const {events, cursor: next} = await api.events(cursor);
          if (!alive) {
            return;
          }
          cursor = next;
          backoff = 1000;
          setState('live');
          events.forEach(e => handler.current(e));
        } catch {
          if (!alive) {
            return;
          }
          setState('retrying');
          await new Promise<void>(r => setTimeout(() => r(), backoff));
          backoff = Math.min(backoff * 2, 15000);
        }
      }
    };
    loop();
    return () => {
      alive = false;
    };
  }, [api]);

  return state;
}
