import SwiftUI

struct ContentView: View {
    @StateObject private var streamer = HeartRateStreamer()
    @State private var running = false
    @State private var household = Config.household

    var body: some View {
        VStack(spacing: 8) {
            Text(streamer.bpm.map(String.init) ?? "—")
                .font(.system(size: 56, weight: .bold, design: .rounded))
                .foregroundStyle(.red)
                .contentTransition(.numericText())
            Text("bpm").font(.footnote).foregroundStyle(.secondary)
            Text(streamer.status).font(.footnote).multilineTextAlignment(.center).foregroundStyle(.secondary)
            Button(running ? "Stop" : "Start") {
                Task {
                    if running { await streamer.stop() } else { await streamer.start() }
                    running.toggle()
                }
            }
            .tint(running ? .gray : .green)
            TextField("Household", text: $household)
                .textInputAutocapitalization(.characters)
                .onSubmit { Config.household = household }
                .font(.footnote)
            if streamer.sent > 0 { Text("\(streamer.sent) samples sent").font(.caption2).foregroundStyle(.secondary) }
        }
        .padding()
    }
}
