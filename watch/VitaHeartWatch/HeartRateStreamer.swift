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

    func start() async {
        guard await requestAccess() else { return }
        status = "Asking the television…"
        guard let live = try? await client.liveSession() else { status = "The television has not started a session"; return }
        tvSession = live.id
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
            status = "Streaming to the television"
        } catch {
            status = "Could not start: \(error.localizedDescription)"
        }
    }

    func stop() async {
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
