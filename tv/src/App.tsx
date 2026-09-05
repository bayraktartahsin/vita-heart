import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
// eslint-disable-next-line @amazon-devices/kepler/sdl-package-version-check-imports -- system library, understood
import {TVFocusGuideView} from '@amazon-devices/react-native-kepler';
import {ApiError, Board, Dose, LiveEvent, VitaHeartApi} from './api/client';
import {API_BASE_URL, DEFAULT_HOUSEHOLD} from './config';
import {color, space, type} from './design/tokens';
import {useLiveEvents} from './live/useLiveEvents';
import {MedicationMoment} from './screens/MedicationMoment';
import {MorningBoard} from './screens/MorningBoard';
import {Pairing} from './screens/Pairing';

type Screen = 'pairing' | 'board' | 'meds';

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
      if (['message', 'checkin', 'dose', 'board'].includes(e.kind)) {
        refresh();
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
        ) : screen === 'meds' && board ? (
          <MedicationMoment doses={board.dueDoses} onConfirm={confirmDose} onBack={() => setScreen('board')} pendingId={dosePending} />
        ) : (
          <MorningBoard board={board} error={error} live={live} onCheckin={checkin} onOpenMeds={() => setScreen('meds')} checkinPending={checkinPending} />
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
