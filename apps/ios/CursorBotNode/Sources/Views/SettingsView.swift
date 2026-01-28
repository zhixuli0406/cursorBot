// SettingsView.swift
// Settings view for iOS Node

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: NodeAppState
    
    var body: some View {
        NavigationStack {
            List {
                // Connection Section
                Section("Connection") {
                    NavigationLink {
                        ConnectionView()
                    } label: {
                        HStack {
                            Image(systemName: "antenna.radiowaves.left.and.right")
                                .foregroundColor(.blue)
                            VStack(alignment: .leading) {
                                Text("Gateway")
                                Text(appState.isConnected ? appState.gatewayURL : "Not connected")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                    
                    if appState.isConnected {
                        NavigationLink {
                            PairingView()
                        } label: {
                            HStack {
                                Image(systemName: "qrcode")
                                    .foregroundColor(.purple)
                                Text("Device Pairing")
                            }
                        }
                    }
                }
                
                // Voice Section
                Section("Voice") {
                    Toggle(isOn: $appState.voiceWakeEnabled) {
                        HStack {
                            Image(systemName: "waveform")
                                .foregroundColor(.green)
                            Text("Voice Wake")
                        }
                    }
                    
                    NavigationLink {
                        VoiceSettingsView()
                    } label: {
                        HStack {
                            Image(systemName: "speaker.wave.3")
                                .foregroundColor(.orange)
                            Text("Voice Settings")
                        }
                    }
                }
                
                // Device Info Section
                Section("Device") {
                    HStack {
                        Text("Device ID")
                        Spacer()
                        Text(String(appState.deviceId.prefix(8)) + "...")
                            .foregroundColor(.secondary)
                            .font(.caption)
                    }
                    
                    HStack {
                        Text("Device Name")
                        Spacer()
                        Text(UIDevice.current.name)
                            .foregroundColor(.secondary)
                    }
                    
                    HStack {
                        Text("iOS Version")
                        Spacer()
                        Text(UIDevice.current.systemVersion)
                            .foregroundColor(.secondary)
                    }
                }
                
                // About Section
                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("0.4.0")
                            .foregroundColor(.secondary)
                    }
                    
                    Link(destination: URL(string: "https://github.com/cursorbot/cursorbot")!) {
                        HStack {
                            Text("GitHub")
                            Spacer()
                            Image(systemName: "arrow.up.right")
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Link(destination: URL(string: "https://cursorbot.ai/docs")!) {
                        HStack {
                            Text("Documentation")
                            Spacer()
                            Image(systemName: "arrow.up.right")
                                .foregroundColor(.secondary)
                        }
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}

// MARK: - Connection View

struct ConnectionView: View {
    @EnvironmentObject var appState: NodeAppState
    @State private var gatewayURL = ""
    @State private var token = ""
    @State private var isConnecting = false
    @State private var errorMessage: String?
    
    var body: some View {
        List {
            Section {
                TextField("Gateway URL", text: $gatewayURL)
                    .textContentType(.URL)
                    .autocapitalization(.none)
                    .autocorrectionDisabled()
                
                SecureField("Token (optional)", text: $token)
            } header: {
                Text("Connection Details")
            } footer: {
                Text("Enter your CursorBot server URL (e.g., https://your-server.com)")
            }
            
            if let error = errorMessage {
                Section {
                    Text(error)
                        .foregroundColor(.red)
                        .font(.caption)
                }
            }
            
            Section {
                Button(appState.isConnected ? "Disconnect" : "Connect") {
                    if appState.isConnected {
                        appState.disconnect()
                    } else {
                        connect()
                    }
                }
                .disabled(gatewayURL.isEmpty && !appState.isConnected)
                .frame(maxWidth: .infinity)
            }
            
            if appState.isConnected {
                Section {
                    HStack {
                        Text("Status")
                        Spacer()
                        HStack {
                            Circle()
                                .fill(Color.green)
                                .frame(width: 8, height: 8)
                            Text("Connected")
                        }
                        .foregroundColor(.green)
                    }
                    
                    HStack {
                        Text("URL")
                        Spacer()
                        Text(appState.gatewayURL)
                            .foregroundColor(.secondary)
                            .font(.caption)
                    }
                }
            }
        }
        .navigationTitle("Gateway Connection")
        .onAppear {
            gatewayURL = appState.gatewayURL
        }
    }
    
    private func connect() {
        isConnecting = true
        errorMessage = nil
        
        Task {
            do {
                try await appState.connectToGateway(url: gatewayURL, token: token)
            } catch {
                errorMessage = error.localizedDescription
            }
            isConnecting = false
        }
    }
}

// MARK: - Pairing View

struct PairingView: View {
    @EnvironmentObject var appState: NodeAppState
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    var body: some View {
        VStack(spacing: 30) {
            if let code = appState.pairingCode {
                // QR Code display
                QRCodeView(code: code)
                    .frame(width: 200, height: 200)
                
                Text("Scan this code to pair")
                    .font(.headline)
                
                Text(code)
                    .font(.system(.title2, design: .monospaced))
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(8)
                
                Text("Code expires in 5 minutes")
                    .font(.caption)
                    .foregroundColor(.secondary)
            } else {
                Image(systemName: "qrcode")
                    .font(.system(size: 80))
                    .foregroundColor(.secondary)
                
                Text("Generate a pairing code")
                    .font(.headline)
                
                Text("Use this code to connect from another device")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            
            if let error = errorMessage {
                Text(error)
                    .foregroundColor(.red)
                    .font(.caption)
            }
            
            Button(appState.pairingCode == nil ? "Generate Code" : "Regenerate") {
                generateCode()
            }
            .buttonStyle(.borderedProminent)
            .disabled(isLoading)
        }
        .padding()
        .navigationTitle("Device Pairing")
    }
    
    private func generateCode() {
        isLoading = true
        errorMessage = nil
        
        Task {
            do {
                _ = try await appState.requestPairingCode()
            } catch {
                errorMessage = error.localizedDescription
            }
            isLoading = false
        }
    }
}

struct QRCodeView: View {
    let code: String
    
    var body: some View {
        if let qrImage = generateQRCode(from: code) {
            Image(uiImage: qrImage)
                .interpolation(.none)
                .resizable()
                .scaledToFit()
        } else {
            Color.gray
        }
    }
    
    private func generateQRCode(from string: String) -> UIImage? {
        guard let data = string.data(using: .utf8),
              let filter = CIFilter(name: "CIQRCodeGenerator") else {
            return nil
        }
        
        filter.setValue(data, forKey: "inputMessage")
        filter.setValue("H", forKey: "inputCorrectionLevel")
        
        guard let ciImage = filter.outputImage else { return nil }
        
        let transform = CGAffineTransform(scaleX: 10, y: 10)
        let scaledImage = ciImage.transformed(by: transform)
        
        let context = CIContext()
        guard let cgImage = context.createCGImage(scaledImage, from: scaledImage.extent) else {
            return nil
        }
        
        return UIImage(cgImage: cgImage)
    }
}

// MARK: - Voice Settings View

struct VoiceSettingsView: View {
    @AppStorage("voiceWakePhrase") private var wakePhrase = "Hey Cursor"
    @AppStorage("voiceSensitivity") private var sensitivity = 0.5
    @AppStorage("speakingRate") private var speakingRate = 1.0
    @AppStorage("voiceLanguage") private var language = "en-US"
    
    var body: some View {
        List {
            Section("Voice Wake") {
                TextField("Wake Phrase", text: $wakePhrase)
                
                VStack(alignment: .leading) {
                    Text("Sensitivity: \(Int(sensitivity * 100))%")
                    Slider(value: $sensitivity, in: 0...1)
                }
            }
            
            Section("Speech") {
                Picker("Language", selection: $language) {
                    Text("English (US)").tag("en-US")
                    Text("English (UK)").tag("en-GB")
                    Text("中文 (繁體)").tag("zh-TW")
                    Text("中文 (简体)").tag("zh-CN")
                    Text("日本語").tag("ja-JP")
                }
                
                VStack(alignment: .leading) {
                    Text("Speaking Rate: \(String(format: "%.1f", speakingRate))x")
                    Slider(value: $speakingRate, in: 0.5...2.0)
                }
            }
            
            Section {
                Button("Test Voice") {
                    // Test TTS
                }
            }
        }
        .navigationTitle("Voice Settings")
    }
}

// MARK: - Preview

#Preview {
    SettingsView()
        .environmentObject(NodeAppState.shared)
}
