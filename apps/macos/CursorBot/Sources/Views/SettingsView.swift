// SettingsView.swift
// Application settings view

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    
    var body: some View {
        TabView {
            GeneralSettingsView()
                .tabItem {
                    Label("General", systemImage: "gear")
                }
            
            VoiceSettingsView()
                .tabItem {
                    Label("Voice", systemImage: "waveform")
                }
            
            GatewaySettingsView()
                .tabItem {
                    Label("Gateway", systemImage: "antenna.radiowaves.left.and.right")
                }
            
            AdvancedSettingsView()
                .tabItem {
                    Label("Advanced", systemImage: "wrench")
                }
        }
        .frame(width: 500, height: 400)
    }
}

// MARK: - General Settings

struct GeneralSettingsView: View {
    @AppStorage("launchAtLogin") private var launchAtLogin = false
    @AppStorage("showInDock") private var showInDock = true
    @AppStorage("showInMenuBar") private var showInMenuBar = true
    @AppStorage("notifications") private var notifications = true
    
    var body: some View {
        Form {
            Section("Startup") {
                Toggle("Launch at login", isOn: $launchAtLogin)
                Toggle("Show in Dock", isOn: $showInDock)
                Toggle("Show in menu bar", isOn: $showInMenuBar)
            }
            
            Section("Notifications") {
                Toggle("Enable notifications", isOn: $notifications)
            }
            
            Section("Appearance") {
                Picker("Theme", selection: .constant(0)) {
                    Text("System").tag(0)
                    Text("Light").tag(1)
                    Text("Dark").tag(2)
                }
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

// MARK: - Voice Settings

struct VoiceSettingsView: View {
    @EnvironmentObject var appState: AppState
    @AppStorage("voiceWakePhrase") private var voiceWakePhrase = "Hey Cursor"
    @AppStorage("voiceSensitivity") private var voiceSensitivity = 0.5
    @AppStorage("speakingRate") private var speakingRate = 1.0
    @AppStorage("voiceLanguage") private var voiceLanguage = "en-US"
    
    var body: some View {
        Form {
            Section("Voice Wake") {
                Toggle("Enable Voice Wake", isOn: $appState.voiceWakeEnabled)
                
                TextField("Wake Phrase", text: $voiceWakePhrase)
                    .textFieldStyle(.roundedBorder)
                
                HStack {
                    Text("Sensitivity")
                    Slider(value: $voiceSensitivity, in: 0...1)
                    Text(String(format: "%.0f%%", voiceSensitivity * 100))
                        .monospacedDigit()
                        .frame(width: 40)
                }
            }
            
            Section("Speech") {
                Picker("Language", selection: $voiceLanguage) {
                    Text("English (US)").tag("en-US")
                    Text("English (UK)").tag("en-GB")
                    Text("中文 (繁體)").tag("zh-TW")
                    Text("中文 (简体)").tag("zh-CN")
                    Text("日本語").tag("ja-JP")
                }
                
                HStack {
                    Text("Speaking Rate")
                    Slider(value: $speakingRate, in: 0.5...2.0)
                    Text(String(format: "%.1fx", speakingRate))
                        .monospacedDigit()
                        .frame(width: 40)
                }
            }
            
            Section("Audio Devices") {
                Picker("Input Device", selection: .constant("Default")) {
                    Text("Default").tag("Default")
                    // TODO: List available devices
                }
                
                Picker("Output Device", selection: .constant("Default")) {
                    Text("Default").tag("Default")
                    // TODO: List available devices
                }
                
                Button("Test Audio") {
                    Task {
                        await AudioService.shared.speak("This is a test of the audio system.")
                    }
                }
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

// MARK: - Gateway Settings

struct GatewaySettingsView: View {
    @EnvironmentObject var appState: AppState
    @AppStorage("autoReconnect") private var autoReconnect = true
    @AppStorage("reconnectAttempts") private var reconnectAttempts = 5
    @AppStorage("connectionTimeout") private var connectionTimeout = 30
    
    var body: some View {
        Form {
            Section("Connection") {
                Toggle("Auto reconnect", isOn: $autoReconnect)
                
                Stepper("Max reconnect attempts: \(reconnectAttempts)", value: $reconnectAttempts, in: 1...10)
                
                Stepper("Connection timeout: \(connectionTimeout)s", value: $connectionTimeout, in: 10...120, step: 10)
            }
            
            Section("Current Connection") {
                HStack {
                    Text("Status")
                    Spacer()
                    Text(appState.connectionStatus.description)
                        .foregroundColor(appState.connectionStatus.color)
                }
                
                HStack {
                    Text("URL")
                    Spacer()
                    Text(appState.gatewayURL.isEmpty ? "Not connected" : appState.gatewayURL)
                        .foregroundColor(.secondary)
                }
            }
            
            Section {
                Button("Manage Gateways...") {
                    appState.showGatewaySheet = true
                }
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

// MARK: - Advanced Settings

struct AdvancedSettingsView: View {
    @AppStorage("debugMode") private var debugMode = false
    @AppStorage("verboseLogging") private var verboseLogging = false
    @AppStorage("maxLogEntries") private var maxLogEntries = 1000
    
    var body: some View {
        Form {
            Section("Debug") {
                Toggle("Debug mode", isOn: $debugMode)
                Toggle("Verbose logging", isOn: $verboseLogging)
                
                Stepper("Max log entries: \(maxLogEntries)", value: $maxLogEntries, in: 100...10000, step: 100)
            }
            
            Section("Cache") {
                HStack {
                    Text("Cache Size")
                    Spacer()
                    Text("12.5 MB")
                        .foregroundColor(.secondary)
                }
                
                Button("Clear Cache") {
                    // TODO: Clear cache
                }
            }
            
            Section("Data") {
                Button("Export All Data...") {
                    // TODO: Export
                }
                
                Button("Reset All Settings", role: .destructive) {
                    // TODO: Reset
                }
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

// MARK: - Preview

#Preview {
    SettingsView()
        .environmentObject(AppState.shared)
}
