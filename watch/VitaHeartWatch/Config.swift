import Foundation

/// Where the television's API lives and which household this wrist belongs to.
/// The household code is typed once on the Watch (the same code the TV shows).
enum Config {
    static let apiBase = URL(string: "https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com")!
    static var household: String {
        get { UserDefaults.standard.string(forKey: "household") ?? "AHMET1" }
        set { UserDefaults.standard.set(newValue.uppercased(), forKey: "household") }
    }
}
