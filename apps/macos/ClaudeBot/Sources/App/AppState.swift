// AppState.swift
// Global application state management

import SwiftUI
import Combine

@MainActor
class AppState: ObservableObject {
    static let shared = AppState()
    
    // MARK: - Connection State
    @Published var isGatewayConnected = false
    @Published var gatewayURL: String = ""
    @Published var connectionStatus: ConnectionStatus = .disconnected
    
    // MARK: - Talk Mode State
    @Published var isTalkModeActive = false
    @Published var voiceWakeEnabled = false
    @Published var isListening = false
    @Published var isSpeaking = false
    @Published var currentTranscript = ""
    
    // MARK: - UI State
    @Published var showGatewaySheet = false
    @Published var showDebugPanel = false
    @Published var showLogs = false
    @Published var showNetworkInspector = false
    @Published var selectedConversationId: String?
    
    // MARK: - Data
    @Published var conversations: [Conversation] = []
    @Published var currentMessages: [Message] = []
    @Published var logs: [LogEntry] = []
    @Published var networkRequests: [NetworkRequest] = []
    
    // MARK: - Services
    private var gatewayService: GatewayService?
    private var audioService = AudioService.shared
    private var cancellables = Set<AnyCancellable>()
    
    private init() {
        setupBindings()
        loadSettings()
    }
    
    // MARK: - Public Methods
    
    func connectToGateway(url: String, token: String) async throws {
        gatewayURL = url
        connectionStatus = .connecting
        
        gatewayService = GatewayService(url: url, token: token)
        gatewayService?.delegate = self
        
        do {
            try await gatewayService?.connect()
            isGatewayConnected = true
            connectionStatus = .connected
            addLog(.info, "Connected to gateway: \(url)")
        } catch {
            connectionStatus = .error(error.localizedDescription)
            addLog(.error, "Failed to connect: \(error.localizedDescription)")
            throw error
        }
    }
    
    func disconnectGateway() {
        gatewayService?.disconnect()
        isGatewayConnected = false
        connectionStatus = .disconnected
        addLog(.info, "Disconnected from gateway")
    }
    
    func toggleTalkMode() {
        if isTalkModeActive {
            stopTalkMode()
        } else {
            startTalkMode()
        }
    }
    
    func startTalkMode() {
        guard isGatewayConnected else {
            addLog(.warning, "Cannot start Talk Mode: not connected to gateway")
            return
        }
        
        // Check permissions first
        if !audioService.checkPermissions() {
            addLog(.warning, "Talk Mode requires microphone and speech recognition permissions")
            audioService.requestPermissions()
            return
        }
        
        isTalkModeActive = true
        audioService.startListening { [weak self] transcript in
            self?.handleTranscript(transcript)
        }
        addLog(.info, "Talk Mode started")
    }
    
    func stopTalkMode() {
        isTalkModeActive = false
        audioService.stopListening()
        addLog(.info, "Talk Mode stopped")
    }
    
    func sendMessage(_ text: String) async {
        guard isGatewayConnected else { return }
        
        let message = Message(
            id: UUID().uuidString,
            role: .user,
            content: text,
            timestamp: Date()
        )
        currentMessages.append(message)
        
        do {
            let response = try await gatewayService?.sendMessage(text)
            if let responseText = response {
                let aiMessage = Message(
                    id: UUID().uuidString,
                    role: .assistant,
                    content: responseText,
                    timestamp: Date()
                )
                currentMessages.append(aiMessage)
                
                if isTalkModeActive {
                    await speakResponse(responseText)
                }
            }
        } catch {
            addLog(.error, "Failed to send message: \(error.localizedDescription)")
        }
    }
    
    func startNewConversation() {
        currentMessages = []
        selectedConversationId = UUID().uuidString
        addLog(.info, "Started new conversation")
    }
    
    func cleanup() {
        stopTalkMode()
        disconnectGateway()
        saveSettings()
    }
    
    // MARK: - Private Methods
    
    private func setupBindings() {
        // Auto-start voice wake when enabled
        $voiceWakeEnabled
            .dropFirst() // Skip initial value from UserDefaults to prevent auto-start on launch
            .sink { [weak self] enabled in
                guard let self = self else { return }
                if enabled {
                    self.addLog(.info, "Voice Wake enabled, starting...")
                    self.audioService.startVoiceWake { [weak self] in
                        guard let self = self else { return }
                        self.addLog(.info, "Voice Wake detected! Starting Talk Mode...")
                        self.startTalkMode()
                    }
                } else {
                    self.addLog(.info, "Voice Wake disabled")
                    self.audioService.stopVoiceWake()
                }
            }
            .store(in: &cancellables)
    }
    
    // MARK: - Voice Wake Control
    
    func toggleVoiceWake() {
        voiceWakeEnabled.toggle()
        
        // If enabling voice wake, start it immediately
        if voiceWakeEnabled {
            addLog(.info, "Enabling Voice Wake...")
            audioService.startVoiceWake { [weak self] in
                guard let self = self else { return }
                self.addLog(.info, "Voice Wake detected! Starting Talk Mode...")
                self.startTalkMode()
            }
        } else {
            addLog(.info, "Disabling Voice Wake...")
            audioService.stopVoiceWake()
        }
    }
    
    private func loadSettings() {
        let defaults = UserDefaults.standard
        gatewayURL = defaults.string(forKey: "gatewayURL") ?? ""
        // Don't auto-enable voice wake on startup - user must manually enable
        // voiceWakeEnabled = defaults.bool(forKey: "voiceWakeEnabled")
        voiceWakeEnabled = false
    }
    
    private func saveSettings() {
        let defaults = UserDefaults.standard
        defaults.set(gatewayURL, forKey: "gatewayURL")
        defaults.set(voiceWakeEnabled, forKey: "voiceWakeEnabled")
    }
    
    private func handleTranscript(_ transcript: String) {
        currentTranscript = transcript
        Task {
            await sendMessage(transcript)
        }
    }
    
    private func speakResponse(_ text: String) async {
        isSpeaking = true
        await audioService.speak(text)
        isSpeaking = false
    }
    
    func addLog(_ level: LogLevel, _ message: String) {
        let entry = LogEntry(
            id: UUID().uuidString,
            timestamp: Date(),
            level: level,
            message: message
        )
        logs.append(entry)
        
        // Keep only last 1000 logs
        if logs.count > 1000 {
            logs.removeFirst(logs.count - 1000)
        }
    }
}

// MARK: - Gateway Service Delegate
extension AppState: GatewayServiceDelegate {
    nonisolated func gatewayDidConnect() {
        Task { @MainActor in
            isGatewayConnected = true
            connectionStatus = .connected
        }
    }
    
    nonisolated func gatewayDidDisconnect(error: Error?) {
        Task { @MainActor in
            isGatewayConnected = false
            connectionStatus = error != nil ? .error(error!.localizedDescription) : .disconnected
        }
    }
    
    nonisolated func gatewayDidReceiveMessage(_ message: String) {
        Task { @MainActor in
            let aiMessage = Message(
                id: UUID().uuidString,
                role: .assistant,
                content: message,
                timestamp: Date()
            )
            currentMessages.append(aiMessage)
        }
    }
}

// MARK: - Supporting Types

enum ConnectionStatus: Equatable {
    case disconnected
    case connecting
    case connected
    case error(String)
    
    var description: String {
        switch self {
        case .disconnected: return "Disconnected"
        case .connecting: return "Connecting..."
        case .connected: return "Connected"
        case .error(let msg): return "Error: \(msg)"
        }
    }
    
    var color: Color {
        switch self {
        case .disconnected: return .gray
        case .connecting: return .orange
        case .connected: return .green
        case .error: return .red
        }
    }
}

enum LogLevel: String {
    case debug = "DEBUG"
    case info = "INFO"
    case warning = "WARNING"
    case error = "ERROR"
    
    var color: Color {
        switch self {
        case .debug: return .secondary
        case .info: return .blue
        case .warning: return .orange
        case .error: return .red
        }
    }
}

struct LogEntry: Identifiable {
    let id: String
    let timestamp: Date
    let level: LogLevel
    let message: String
}

struct NetworkRequest: Identifiable {
    let id: String
    let timestamp: Date
    let method: String
    let url: String
    let statusCode: Int?
    let duration: TimeInterval
    let requestBody: String?
    let responseBody: String?
}
