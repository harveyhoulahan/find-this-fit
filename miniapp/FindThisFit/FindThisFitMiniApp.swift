// Main app entrypoint (excluded from App Clip builds)
#if !APPCLIP
import SwiftUI

@main
struct FindThisFitMiniApp: App {
    var body: some Scene {
        WindowGroup {
            NavigationStack {
                CameraView()
            }
            .tint(Color(red: 1.0, green: 0.42, blue: 0.58))
        }
    }
}
#endif
