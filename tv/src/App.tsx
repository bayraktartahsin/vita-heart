import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
// eslint-disable-next-line @amazon-devices/kepler/sdl-package-version-check-imports -- system library, understood
import {TVFocusGuideView} from '@amazon-devices/react-native-kepler';
import {ApiError, Board, Dose, LiveEvent, VitaHeartApi} from './api/client';
import {HelpKeys, Shell} from './components/Shell';
import {API_BASE_URL, DEFAULT_HOUSEHOLD} from './config';
import {useLiveEvents} from './live/useLiveEvents';
import {ClockSetup, Slot} from './screens/ClockSetup';
import {Family} from './screens/Family';
import {HeartSession, SessionSource} from './screens/HeartSession';
import {MedicationMoment} from './screens/MedicationMoment';
import {MorningBoard} from './screens/MorningBoard';
import {Pairing} from './screens/Pairing';
import {SessionState, current, start as startEngine, summarize} from './session/engine';

type Screen = 'pairing' | 'board' | 'meds' | 'clock' | 'session' | 'family';

const GREETING_SPLIT = (greeting: string): [string, string] => {
  const i = greeting.lastIndexOf(', ');
  return i > 0 ? [greeting.slice(0, i + 2), greeting.slice(i + 2)] : [greeting, ''];
};

export const App = ({apiBaseUrl = API_BASE_URL, household: initialHousehold}: {apiBaseUrl?: string; household?: string}) => {
  const [household, setHousehold] = useState<string | null>(initialHousehold ?? null);
  const [screen, setScreen] = useState<Screen>(initialHousehold ? 'board' : 'pairing');
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checkinPending, setCheckinPending] = useState(false);
  const [dosePending, setDosePending] = useState<string | null>(null);
  const [clockPending, setClockPending] = useState(false);
  const [familyRefresh, setFamilyRefresh] = useState(0);
  const [session, setSession] = useState<{id: string; source: SessionSource; state: SessionState} | null>(null);
  const [latestBpm, setLatestBpm] = useState<number | null>(null);
  const [coachLine, setCoachLine] = useState('');
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

  const onEvent = useCallback((e: LiveEvent) => {
    if (['message', 'checkin', 'dose', 'board', 'med'].includes(e.kind)) {
      refresh();
    }
    if (['message', 'summary', 'med', 'signal'].includes(e.kind)) {
      setFamilyRefresh(n => n + 1);
    }
    if (e.kind === 'hr' && sessionRef.current && e.data.session === sessionRef.current.id) {
      setLatestBpm(Number(e.data.bpm));
    }
  }, [refresh]);
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

  const confirmDose = useCallback(async (dose: Dose) => {
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
  }, [api, refresh]);

  const saveClock = useCallback(async (times: Record<string, string>) => {
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
  }, [api, refresh]);

  const startSession = useCallback(async (source: SessionSource) => {
    if (!api || !board) {
      return;
    }
    try {
      const {id} = await api.startSession(source);
      setLatestBpm(null);
      setCoachLine(source === 'watch' ? 'Open Vita Heart on your Watch and press Start.' : 'Sit comfortably. We begin gently.');
      setSession({id, source, state: startEngine(board.person.age ?? 70)});
      setScreen('session');
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    }
  }, [api, board]);

  const onSessionTick = useCallback((next: SessionState) => {
    const prevPhase = sessionRef.current ? current(sessionRef.current.state).phase : null;
    setSession(prev => (prev ? {...prev, state: next} : prev));
    const nextPhase = current(next).phase;
    if (api && prevPhase !== nextPhase && nextPhase !== 'done') {
      const last = next.samples[next.samples.length - 1];
      api.coach({phase: nextPhase, elapsedSeconds: next.elapsed, lastBpm: last?.bpm ?? null, zone: next.zones,
        adaptations: next.adaptations.map(a => a.kind)})
        .then(r => r.line && setCoachLine(r.line))
        .catch(() => {});
    }
  }, [api]);

  const onSessionFinish = useCallback((final: SessionState) => {
    if (api && sessionRef.current) {
      api.finishSession(sessionRef.current.id, summarize(final) as unknown as Record<string, unknown>).catch(() => {});
    }
  }, [api]);

  const stopSession = useCallback(() => {
    if (api && sessionRef.current && !sessionRef.current.state.finished) {
      api.finishSession(sessionRef.current.id, {...summarize(sessionRef.current.state), stoppedEarly: true}).catch(() => {});
    }
    setSession(null);
    setScreen('board');
    refresh();
  }, [api, refresh]);

  const slotsNeeded = Array.from(new Set((board?.dueDoses ?? []).map(d => d.slot))) as Slot[];
  const openDoses = (board?.dueDoses ?? []).filter(d => !d.confirmed).length;
  const [greetHead, greetName] = GREETING_SPLIT(board?.greeting ?? 'Vita Heart');
  const liveLabel = live === 'live' ? 'live' : live === 'retrying' ? 'reconnecting' : 'connecting';

  const shell = {
    pairing: {tab: 'board', title: 'Vita ', accent: 'Heart', subtitle: 'The health room on this television',
      help: <HelpKeys items={[['↑ ↓', 'letter'], ['← →', 'move'], ['OK', 'connect']]} />},
    board: {tab: 'board', title: greetHead, accent: greetName, subtitle: new Date().toDateString(),
      help: <HelpKeys items={[['OK', 'choose'], ['← → ↑ ↓', 'move']]} note="Night Watch writes to the family at 21:00" />},
    meds: {tab: 'meds', title: openDoses === 1 ? 'One to take, ' : `${openDoses || 'Nothing'} to take, `, accent: 'this morning',
      subtitle: 'Photographed from the family\'s phone, read by the agents',
      help: <HelpKeys items={[['OK', 'I took it'], ['← →', 'other tablet'], ['Back', 'home']]} note="Confirmed doses appear on the family's phone at once" />},
    clock: {tab: 'meds', title: 'When do you usually ', accent: 'take them?', subtitle: 'The label said twice daily. It never said nine o\'clock.',
      help: <HelpKeys items={[['OK', 'choose'], ['← →', 'move']]} />},
    session: {tab: 'session', title: 'Ten minutes, ', accent: 'seated',
      subtitle: session ? `Minute ${Math.floor(session.state.elapsed / 60) + 1} of ${Math.round(session.state.plan.reduce((a, b) => a + b.seconds, 0) / 60)}` : undefined,
      help: <HelpKeys items={[['OK', 'pause'], ['Back', 'stop and save']]} />},
    family: {tab: 'family', title: 'What the family ', accent: 'will read', subtitle: 'Night Watch sends it at 21:00 · you see it first',
      help: <HelpKeys items={[['Back', 'home']]} note="Sent by email · a reply appears on this screen" />},
  }[screen];

  return (
    <Shell tab={shell.tab} title={shell.title} accent={shell.accent} subtitle={shell.subtitle}
      status={screen === 'session' ? (latestBpm === null ? 'waiting for the Watch' : 'Watch connected') : liveLabel}
      help={shell.help}>
      <TVFocusGuideView style={{flex: 1}} autoFocus>
        {screen === 'pairing' ? (
          <Pairing initial={DEFAULT_HOUSEHOLD} onPaired={code => {
            setHousehold(code);
            setScreen('board');
          }} />
        ) : screen === 'family' && api ? (
          <Family api={api} onBack={() => setScreen('board')} refreshKey={familyRefresh} />
        ) : screen === 'session' && session ? (
          <HeartSession state={session.state} onTick={onSessionTick} latestBpm={latestBpm} source={session.source}
            coachLine={coachLine} onFinish={onSessionFinish} onStop={stopSession} />
        ) : screen === 'clock' && board ? (
          <ClockSetup slotsNeeded={slotsNeeded} initial={board.clock} onConfirm={saveClock} onBack={() => setScreen('meds')} pending={clockPending} />
        ) : screen === 'meds' && board ? (
          <MedicationMoment doses={board.dueDoses} onConfirm={confirmDose} onBack={() => setScreen('board')}
            onSetClock={() => setScreen('clock')} pendingId={dosePending} />
        ) : (
          <MorningBoard board={board} error={error} live={live} onCheckin={checkin} onOpenMeds={() => setScreen('meds')}
            onOpenFamily={() => setScreen('family')} onStartSession={startSession} checkinPending={checkinPending} />
        )}
      </TVFocusGuideView>
    </Shell>
  );
};
