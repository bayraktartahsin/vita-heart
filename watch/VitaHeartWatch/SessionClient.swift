import Foundation

/// Talks to the Vita Heart API. Three calls: is the TV waiting, send a sample, done.
struct LiveSession: Decodable { let id: String; let source: String }
private struct LiveResponse: Decodable { let live: LiveSession? }

final class SessionClient {
    private let session = URLSession(configuration: .default)

    func liveSession() async throws -> LiveSession? {
        var comps = URLComponents(url: Config.apiBase.appendingPathComponent("session/live"), resolvingAgainstBaseURL: false)!
        comps.queryItems = [URLQueryItem(name: "household", value: Config.household)]
        let (data, _) = try await session.data(from: comps.url!)
        return try JSONDecoder().decode(LiveResponse.self, from: data).live
    }

    func send(bpm: Int, sessionId: String) async {
        var req = URLRequest(url: Config.apiBase.appendingPathComponent("session/hr"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "content-type")
        let body: [String: Any] = ["household": Config.household, "session": sessionId, "bpm": bpm,
                                   "at": ISO8601DateFormatter().string(from: Date())]
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)
        _ = try? await session.data(for: req)   // a lost sample is a lost sample; the next one is 5 s away
    }

    /// Tell the prompter the wrist is here, so nobody has to remember a toggle.
    ///
    /// Forgetting it means the television opens a "recorded" session, the replay trace is
    /// fed into it, and the screen says "a recorded session" while a real Watch sits on a
    /// real wrist doing nothing. That is a worse demo than either honest option.
    func announceWrist() async {
        var req = URLRequest(url: Config.apiBase.appendingPathComponent("prompter"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "content-type")
        req.httpBody = try? JSONSerialization.data(
            withJSONObject: ["household": Config.household, "cmd": "wrist"])
        _ = try? await session.data(for: req)
    }
}
