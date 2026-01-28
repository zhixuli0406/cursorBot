// CursorBotNode iOS App
// SwiftUI-based node application with Canvas, Voice Wake, Talk Mode, and Camera

import SwiftUI

@main
struct CursorBotNodeApp: App {
    @StateObject private var appState = NodeAppState.shared
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        WindowGroup {
            MainTabView()
                .environmentObject(appState)
        }
    }
}

class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        // Request permissions
        Task {
            await requestPermissions()
        }
        
        // Setup background modes
        setupBackgroundModes()
        
        return true
    }
    
    private func requestPermissions() async {
        // Request notification permissions
        let center = UNUserNotificationCenter.current()
        try? await center.requestAuthorization(options: [.alert, .sound, .badge])
        
        // Request microphone permissions
        await AVAudioSession.sharedInstance().requestRecordPermission { granted in
            print("Microphone permission: \(granted)")
        }
        
        // Request camera permissions
        AVCaptureDevice.requestAccess(for: .video) { granted in
            print("Camera permission: \(granted)")
        }
    }
    
    private func setupBackgroundModes() {
        // Configure audio session for background audio
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker, .allowBluetooth])
            try audioSession.setActive(true)
        } catch {
            print("Failed to setup audio session: \(error)")
        }
    }
}

import AVFoundation
import UserNotifications
