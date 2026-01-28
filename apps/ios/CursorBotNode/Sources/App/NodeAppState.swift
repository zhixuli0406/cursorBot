// NodeAppState.swift
// Global application state for iOS Node

import SwiftUI
import Combine
import AVFoundation

@MainActor
class NodeAppState: ObservableObject {
    static let shared = NodeAppState()
    
    // MARK: - Connection State
    @Published var isConnected = false
    @Published var gatewayURL: String = ""
    @Published var connectionStatus: ConnectionStatus = .disconnected
    @Published var deviceId: String = ""
    @Published var pairingCode: String?
    
    // MARK: - Talk Mode State
    @Published var isTalkModeActive = false
    @Published var voiceWakeEnabled = false
    @Published var isListening = false
    @Published var isSpeaking = false
    @Published var currentTranscript = ""
    
    // MARK: - Canvas State
    @Published var canvasState: CanvasState?
    @Published var isCanvasActive = false
    
    // MARK: - Camera State
    @Published var isCameraActive = false
    @Published var capturedImage: UIImage?
    @Published var isProcessingImage = false
    
    // MARK: - Messages
    @Published var messages: [Message] = []
    
    // MARK: - Services
    private var gatewayService: GatewayService?
    private var audioService: AudioService?
    private var cameraService: CameraService?
    private var cancellables = Set<AnyCancellable>()
    
    private init() {
        deviceId = UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
        loadSettings()
        setupServices()
    }
    
    // MARK: - Public Methods
    
    func connectToGateway(url: String, token: String) async throws {
        gatewayURL = url
        connectionStatus = .connecting
        
        gatewayService = GatewayService(url: url, token: token, deviceId: deviceId)
        gatewayService?.delegate = self
        
        do {
            try await gatewayService?.connect()
            isConnected = true
            connectionStatus = .connected
            saveSettings()
        } catch {
            connectionStatus = .error(error.localizedDescription)
            throw error
        }
    }
    
    func disconnect() {
        gatewayService?.disconnect()
        isConnected = false
        connectionStatus = .disconnected
    }
    
    func requestPairingCode() async throws -> String {
        guard isConnected else { throw NodeError.notConnected }
        
        let code = try await gatewayService?.requestPairingCode()
        pairingCode = code
        return code ?? ""
    }
    
    // MARK: - Talk Mode
    
    func startTalkMode() {
        guard isConnected else { return }
        
        isTalkModeActive = true
        audioService?.startListening { [weak self] transcript in
            self?.handleTranscript(transcript)
        }
    }
    
    func stopTalkMode() {
        isTalkModeActive = false
        audioService?.stopListening()
    }
    
    func toggleTalkMode() {
        if isTalkModeActive {
            stopTalkMode()
        } else {
            startTalkMode()
        }
    }
    
    // MARK: - Canvas
    
    func createCanvas() async throws {
        guard isConnected else { throw NodeError.notConnected }
        
        let canvas = try await gatewayService?.createCanvas()
        canvasState = canvas
        isCanvasActive = true
    }
    
    func updateCanvasComponent(_ component: CanvasComponent) async throws {
        guard let canvasId = canvasState?.id else { throw NodeError.noCanvas }
        try await gatewayService?.updateCanvasComponent(canvasId: canvasId, component: component)
    }
    
    func closeCanvas() {
        canvasState = nil
        isCanvasActive = false
    }
    
    // MARK: - Camera
    
    func startCamera() {
        cameraService?.startSession()
        isCameraActive = true
    }
    
    func stopCamera() {
        cameraService?.stopSession()
        isCameraActive = false
    }
    
    func capturePhoto() async throws -> UIImage {
        guard let image = try await cameraService?.capturePhoto() else {
            throw NodeError.cameraError
        }
        capturedImage = image
        return image
    }
    
    func analyzeImage(_ image: UIImage) async throws -> String {
        guard isConnected else { throw NodeError.notConnected }
        
        isProcessingImage = true
        defer { isProcessingImage = false }
        
        guard let imageData = image.jpegData(compressionQuality: 0.8) else {
            throw NodeError.imageEncodingError
        }
        
        let base64 = imageData.base64EncodedString()
        let analysis = try await gatewayService?.analyzeImage(base64)
        return analysis ?? ""
    }
    
    // MARK: - Messaging
    
    func sendMessage(_ text: String) async {
        guard isConnected else { return }
        
        let message = Message(
            id: UUID().uuidString,
            role: .user,
            content: text,
            timestamp: Date()
        )
        messages.append(message)
        
        do {
            let response = try await gatewayService?.sendMessage(text)
            if let responseText = response {
                let aiMessage = Message(
                    id: UUID().uuidString,
                    role: .assistant,
                    content: responseText,
                    timestamp: Date()
                )
                messages.append(aiMessage)
                
                if isTalkModeActive {
                    await speakResponse(responseText)
                }
            }
        } catch {
            print("Failed to send message: \(error)")
        }
    }
    
    // MARK: - Voice Wake Control
    
    func toggleVoiceWake() {
        voiceWakeEnabled.toggle()
        
        if voiceWakeEnabled {
            print("NodeAppState: Enabling Voice Wake...")
            audioService?.startVoiceWake { [weak self] in
                guard let self = self else { return }
                print("NodeAppState: Voice Wake detected! Starting Talk Mode...")
                self.startTalkMode()
            }
        } else {
            print("NodeAppState: Disabling Voice Wake...")
            audioService?.stopVoiceWake()
        }
        
        saveSettings()
    }
    
    // MARK: - Private Methods
    
    private func setupServices() {
        audioService = AudioService()
        cameraService = CameraService()
        
        // Setup voice wake observer (skip first value to avoid auto-start on launch)
        $voiceWakeEnabled
            .dropFirst()
            .sink { [weak self] enabled in
                guard let self = self else { return }
                if enabled {
                    print("NodeAppState: Voice Wake enabled via observer")
                    self.audioService?.startVoiceWake { [weak self] in
                        guard let self = self else { return }
                        print("NodeAppState: Voice Wake detected!")
                        self.startTalkMode()
                    }
                } else {
                    print("NodeAppState: Voice Wake disabled via observer")
                    self.audioService?.stopVoiceWake()
                }
            }
            .store(in: &cancellables)
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
        await audioService?.speak(text)
        isSpeaking = false
    }
}

// MARK: - Gateway Service Delegate

extension NodeAppState: GatewayServiceDelegate {
    func gatewayDidConnect() {
        isConnected = true
        connectionStatus = .connected
    }
    
    func gatewayDidDisconnect(error: Error?) {
        isConnected = false
        connectionStatus = error != nil ? .error(error!.localizedDescription) : .disconnected
    }
    
    func gatewayDidReceiveMessage(_ message: String) {
        let aiMessage = Message(
            id: UUID().uuidString,
            role: .assistant,
            content: message,
            timestamp: Date()
        )
        messages.append(aiMessage)
    }
    
    func gatewayDidReceiveCanvasUpdate(_ canvas: CanvasState) {
        canvasState = canvas
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

enum NodeError: LocalizedError {
    case notConnected
    case noCanvas
    case cameraError
    case imageEncodingError
    
    var errorDescription: String? {
        switch self {
        case .notConnected: return "Not connected to gateway"
        case .noCanvas: return "No active canvas"
        case .cameraError: return "Camera error"
        case .imageEncodingError: return "Failed to encode image"
        }
    }
}
