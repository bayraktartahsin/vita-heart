import Foundation
import HealthKit

/// Live heart rate from the wrist while a session is running on the television.
///
/// An HKWorkoutSession keeps the sensor sampling every few seconds; the live
/// builder delivers each heart-rate sample as it arrives. Every sample is posted
/// to the API, which puts it on the TV's events channel within a second.
@MainActor
final class HeartRateStreamer: NSObject, ObservableObject {
    @Published var bpm: Int? = nil
    @Published var status = "Idle"
    @Published var sent = 0

    private let store = HKHealthStore()
    private var session: HKWorkoutSession?
    private var builder: HKLiveWorkoutBuilder?
    private var tvSession: String?
    private var waiter: Task<Void, Never>?
    private let client = SessionClient()

    func requestAccess() async -> Bool {
        guard HKHealthStore.isHealthDataAvailable() else { status = "Health data unavailable"; return false }
        let hr = HKQuantityType(.heartRate)
        do {
            try await store.requestAuthorization(toShare: [HKObjectType.workoutType()], read: [hr])
            return true
        } catch {
            status = "Health access refused"
            return false
        }
    }

    /// Tap Start once, before anything else. The sensor begins sampling immediately, so
    /// the wrist is already reading by the time the television opens a session; samples
    /// are only sent once one exists. The alternative — demanding a live session at the
    /// instant of the tap — means tapping the watch mid-sentence while reading a script,
    /// which is not something anyone can do on camera.
    func start() async {
        guard await requestAccess() else { return }
        let config = HKWorkoutConfiguration()
        config.activityType = .mixedCardio
        config.locationType = .indoor
        do {
            let s = try HKWorkoutSession(healthStore: store, configuration: config)
            let b = s.associatedWorkoutBuilder()
            b.dataSource = HKLiveWorkoutDataSource(healthStore: store, workoutConfiguration: config)
            b.delegate = self
            s.delegate = self
            session = s; builder = b
            s.startActivity(with: Date())
            try await b.beginCollection(at: Date())
        } catch {
            status = "Could not start: \(error.localizedDescription)"
            return
        }
        status = "Waiting for the television…"
        follow()
    }

    /// Follow the television: pick the session up when it opens, let go when it closes.
    private func follow() {
        waiter?.cancel()
        waiter = Task { [weak self] in
            var beat = 0
            while !Task.isCancelled {
                // every third pass, so the prompter knows within fifteen seconds
                if beat % 3 == 0 { await self?.client.announceWrist() }
                beat += 1
                let live = try? await self?.client.liveSession()
                await MainActor.run {
                    guard let self else { return }
                    // Only a session the television has labelled "watch". A recorded
                    // session already has a trace being fed into it, and two feeders
                    // are drawn interleaved as a violent zigzag between two smooth
                    // curves; worse, the screen would be saying "a recorded session"
                    // over a real heart. The label has to stay true.
                    if let live, live.source == "watch" {
                        if self.tvSession != live.id {
                            self.tvSession = live.id
                            self.status = "Streaming to the television"
                        }
                    } else {
                        if self.tvSession != nil { self.tvSession = nil }
                        self.status = live == nil
                            ? "Reading your wrist. Waiting for the television."
                            : "The television is playing a recorded session"
                    }
                }
                try? await Task.sleep(nanoseconds: 5_000_000_000)
            }
        }
    }

    func stop() async {
        waiter?.cancel(); waiter = nil
        session?.end()
        try? await builder?.endCollection(at: Date())
        _ = try? await builder?.finishWorkout()
        status = "Stopped"
        tvSession = nil
    }

    private func handle(_ quantity: HKQuantity) {
        let value = Int(quantity.doubleValue(for: HKUnit.count().unitDivided(by: .minute())).rounded())
        bpm = value
        guard let sid = tvSession else { return }
        Task { await client.send(bpm: value, sessionId: sid); sent += 1 }
    }
}

extension HeartRateStreamer: HKLiveWorkoutBuilderDelegate {
    nonisolated func workoutBuilder(_ workoutBuilder: HKLiveWorkoutBuilder, didCollectDataOf collectedTypes: Set<HKSampleType>) {
        let hrType = HKQuantityType(.heartRate)
        guard collectedTypes.contains(hrType),
              let stats = workoutBuilder.statistics(for: hrType),
              let latest = stats.mostRecentQuantity() else { return }
        Task { @MainActor in self.handle(latest) }
    }
    nonisolated func workoutBuilderDidCollectEvent(_ workoutBuilder: HKLiveWorkoutBuilder) {}
}

extension HeartRateStreamer: HKWorkoutSessionDelegate {
    nonisolated func workoutSession(_ workoutSession: HKWorkoutSession, didChangeTo toState: HKWorkoutSessionState, from fromState: HKWorkoutSessionState, date: Date) {}
    nonisolated func workoutSession(_ workoutSession: HKWorkoutSession, didFailWithError error: Error) {
        Task { @MainActor in self.status = "Session error: \(error.localizedDescription)" }
    }
}
