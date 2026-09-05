import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
// eslint-disable-next-line @amazon-devices/kepler/sdl-package-version-check-imports -- system library, understood
import {TVFocusGuideView} from '@amazon-devices/react-native-kepler';
import {ApiError, Board, Dose, LiveEvent, VitaHeartApi} from './api/client';
import {API_BASE_URL, DEFAULT_HOUSEHOLD} from './config';
import {color, space, type} from './design/tokens';
import {useLiveEvents} from './live/useLiveEvents';
import {ClockSetup, Slot} from './screens/ClockSetup';
import {Family} from './screens/Family';
import {HeartSession, SessionSource} from './screens/HeartSession';
import {SessionState, current, start as startEngine, summarize} from './session/engine';
import {MedicationMoment} from './screens/MedicationMoment';
import {MorningBoard} from './screens/MorningBoard';
import {Pairing} from './screens/Pairing';

type Screen = 'pairing' | 'board' | 'meds' | 'clock' | 'session' | 'family';

type Props = {apiBaseUrl?: string; household?: string | null};

/**
 * `household` undefined: use the demo household (what the simulator and the
 * judges see). `household` null: start on the pairing screen.
 */
export const App = ({apiBaseUrl = API_BASE_URL, household: initialHousehold = DEFAULT_HOUSEHOLD}: Props) => {
  const [household, setHousehold] = useState<string | null>(initialHousehold);
  const [screen, setScreen] = useState<Screen>(initialHousehold ? 'board' : 'pairing');
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checkinPending, setCheckinPending] = useState(false);
  const [dosePending, setDosePending] = useState<string | null>(null);
  const [clockPending, setClockPending] = useState(false);
  const [session, setSession] = useState<{id: string; source: SessionSource; state: SessionState} | null>(null);
  const [latestBpm, setLatestBpm] = useState<number | null>(null);
  const [coachLine, setCoachLine] = useState('');
  const [familyRefresh, setFamilyRefresh] = useState(0);
  const sessionRef = useRef(session);
  sessionRef.current = session;

  const api = useMemo(() => (household ? new VitaHeartApi(apiBaseUrl, household) : null), [apiBaseUrl, household]);

  const refresh = useCallback(async () => {
    if (!api) {
      return;
    }
    try {
      setBoard(await api.board());
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    }
  }, [api]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onEvent = useCallback(
    (e: LiveEvent) => {
      // Every event kind that changes what the board shows triggers a refetch.
      // Cheap, correct, and it keeps one source of truth: the API.
      if (['message', 'checkin', 'dose', 'board', 'med'].includes(e.kind)) {
        refresh();
      }
      if (['message', 'summary', 'med', 'signal'].includes(e.kind)) {
        setFamilyRefresh(n => n + 1);
      }
      if (e.kind === 'hr' && sessionRef.current && e.data.session === sessionRef.current.id) {
        setLatestBpm(Number(e.data.bpm));
      }
    },
    [refresh],
  );
  const live = useLiveEvents(api, onEvent);

  const checkin = useCallback(async () => {
    if (!api) {
      return;
    }
    setCheckinPending(true);
    try {
      await api.checkin();
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    } finally {
      setCheckinPending(false);
    }
  }, [api, refresh]);

  const confirmDose = useCallback(
    async (dose: Dose) => {
      if (!api) {
        return;
      }
      setDosePending(dose.id);
      try {
        await api.confirmDose(dose.id);
        await refresh();
      } catch (e) {
        setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
      } finally {
        setDosePending(null);
      }
    },
    [api, refresh],
  );

  const saveClock = useCallback(
    async (times: Record<string, string>) => {
      if (!api) {
        return;
      }
      setClockPending(true);
      try {
        await api.setClock(times);
        await refresh();
        setScreen('meds');
      } catch (e) {
        setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
      } finally {
        setClockPending(false);
      }
    },
    [api, refresh],
  );

  const startSession = useCallback(
    async (source: SessionSource) => {
      if (!api || !board) {
        return;
      }
      try {
        const {id} = await api.startSession(source);
        setLatestBpm(null);
        setCoachLine(source === 'watch' ? 'Start the Vita Heart app on your Watch when you are ready.' : 'Sit comfortably. We begin gently.');
        setSession({id, source, state: startEngine(board.person.age ?? 70)});
        setScreen('session');
      } catch (e) {
        setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
      }
    },
    [api, board],
  );

  const onSessionTick = useCallback(
    (next: SessionState) => {
      setSession(prev => (prev ? {...prev, state: next} : prev));
      // A new block: ask the Coach for one line. Never block the session on it.
      const prevPhase = sessionRef.current ? current(sessionRef.current.state).phase : null;
      const nextPhase = current(next).phase;
      if (api && prevPhase !== nextPhase && nextPhase !== 'done') {
        const last = next.samples[next.samples.length - 1];
        api
          .coach({phase: nextPhase, elapsedSeconds: next.elapsed, lastBpm: last?.bpm ?? null, zone: next.zones, adaptations: next.adaptations.map(a => a.kind)})
          .then(r => r.line && setCoachLine(r.line))
          .catch(() => {});
      }
    },
    [api],
  );

  const onSessionFinish = useCallback(
    (final: SessionState) => {
      if (api && sessionRef.current) {
        api.finishSession(sessionRef.current.id, summarize(final) as unknown as Record<string, unknown>).catch(() => {});
      }
    },
    [api],
  );

  const stopSession = useCallback(() => {
    if (api && sessionRef.current && !sessionRef.current.state.finished) {
      api.finishSession(sessionRef.current.id, {...summarize(sessionRef.current.state), stoppedEarly: true}).catch(() => {});
    }
    setSession(null);
    setScreen('board');
    refresh();
  }, [api, refresh]);

  const slotsNeeded = Array.from(new Set((board?.dueDoses ?? []).map(d => d.slot))) as Slot[];

  return (
    <View style={styles.root}>
      <View style={styles.rail}>
        <Text style={styles.brand}>Vita Heart</Text>
        <Text style={styles.railItem}>{household ?? '—'}</Text>
      </View>
      <TVFocusGuideView style={styles.content} autoFocus>
        {screen === 'pairing' ? (
          <Pairing
            initial={DEFAULT_HOUSEHOLD}
            onPaired={code => {
              setHousehold(code);
              setScreen('board');
            }}
          />
        ) : screen === 'family' && api ? (
          <Family api={api} onBack={() => setScreen('board')} refreshKey={familyRefresh} />
        ) : screen === 'session' && session ? (
          <HeartSession state={session.state} onTick={onSessionTick} latestBpm={latestBpm} source={session.source} coachLine={coachLine} onFinish={onSessionFinish} onStop={stopSession} />
        ) : screen === 'clock' && board ? (
          <ClockSetup slotsNeeded={slotsNeeded} initial={board.clock} onConfirm={saveClock} onBack={() => setScreen('meds')} pending={clockPending} />
        ) : screen === 'meds' && board ? (
          <MedicationMoment doses={board.dueDoses} onConfirm={confirmDose} onBack={() => setScreen('board')} onSetClock={() => setScreen('clock')} pendingId={dosePending} />
        ) : (
          <MorningBoard board={board} error={error} live={live} onCheckin={checkin} onOpenMeds={() => setScreen('meds')} onStartSession={startSession} onOpenFamily={() => setScreen('family')} checkinPending={checkinPending} />
        )}
      </TVFocusGuideView>
    </View>
  );
};

const styles = StyleSheet.create({
  root: {flex: 1, flexDirection: 'row', backgroundColor: color.ground},
  rail: {width: 260, paddingVertical: space.xl, paddingHorizontal: space.l, gap: space.l, borderRightWidth: 1, borderRightColor: color.line},
  brand: {color: color.warm, fontSize: type.body, fontWeight: '700'},
  railItem: {color: color.textDim, fontSize: type.small},
  content: {flex: 1, paddingHorizontal: space.xl, paddingVertical: space.xl},
});
