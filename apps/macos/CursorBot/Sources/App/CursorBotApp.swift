// CursorBot macOS App
// SwiftUI-based full-featured application with Talk Mode, Debug Tools, and Remote Gateway

import SwiftUI

@main
struct CursorBotApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var appState = AppState.shared
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .frame(minWidth: 900, minHeight: 600)
        }
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("New Conversation") {
                    appState.startNewConversation()
                }
                .keyboardShortcut("n", modifiers: .command)
            }
            
            CommandMenu("Talk Mode") {
                Button(appState.isTalkModeActive ? "Stop Talk Mode" : "Start Talk Mode") {
                    appState.toggleTalkMode()
                }
                .keyboardShortcut("t", modifiers: [.command, .shift])
                
                Divider()
                
                Toggle("Voice Wake Enabled", isOn: $appState.voiceWakeEnabled)
                    .keyboardShortcut("w", modifiers: [.command, .shift])
            }
            
            CommandMenu("Gateway") {
                Button("Connect to Gateway...") {
                    appState.showGatewaySheet = true
                }
                .keyboardShortcut("g", modifiers: [.command, .shift])
                
                Button("Disconnect") {
                    appState.disconnectGateway()
                }
                .disabled(!appState.isGatewayConnected)
            }
            
            CommandMenu("Debug") {
                Button("Show Debug Panel") {
                    appState.showDebugPanel.toggle()
                }
                .keyboardShortcut("d", modifiers: [.command, .option])
                
                Divider()
                
                Button("View Logs") {
                    appState.showLogs = true
                }
                
                Button("Network Inspector") {
                    appState.showNetworkInspector = true
                }
            }
        }
        
        Settings {
            SettingsView()
                .environmentObject(appState)
        }
        
        MenuBarExtra("CursorBot", systemImage: appState.isGatewayConnected ? "circle.fill" : "circle") {
            MenuBarView()
                .environmentObject(appState)
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Setup global hotkeys
        HotkeyManager.shared.registerHotkeys()
        
        // Check for updates
        UpdateChecker.shared.checkForUpdates()
        
        // Note: Audio permissions are requested when Talk Mode is activated
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        // Cleanup
        AppState.shared.cleanup()
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return false  // Keep running in menu bar
    }
}
