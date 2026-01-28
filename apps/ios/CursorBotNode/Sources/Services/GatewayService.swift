// GatewayService.swift
// Gateway connection service for iOS Node using native URLSessionWebSocketTask

import Foundation

protocol GatewayServiceDelegate: AnyObject {
    func gatewayDidConnect()
    func gatewayDidDisconnect(error: Error?)
    func gatewayDidReceiveMessage(_ message: String)
    func gatewayDidReceiveCanvasUpdate(_ canvas: CanvasState)
}

class GatewayService: NSObject {
    private let url: String
    private let token: String
    private let deviceId: String
    private var webSocketTask: URLSessionWebSocketTask?
    private var urlSession: URLSession?
    private var isConnected = false
    private var reconnectAttempts = 0
    private let maxReconnectAttempts = 5
    
    weak var delegate: GatewayServiceDelegate?
    
    private var pendingRequests: [String: CheckedContinuation<String, Error>] = [:]
    private var connectionContinuation: CheckedContinuation<Void, Error>?
    
    init(url: String, token: String, deviceId: String) {
        self.url = url
        self.token = token
        self.deviceId = deviceId
        super.init()
    }
    
    // MARK: - Connection
    
    func connect() async throws {
        guard let wsURL = URL(string: url.replacingOccurrences(of: "http", with: "ws") + "/ws/node") else {
            throw GatewayError.invalidURL
        }
        
        var request = URLRequest(url: wsURL)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue(deviceId, forHTTPHeaderField: "X-Device-ID")
        request.setValue("ios", forHTTPHeaderField: "X-Device-Type")
        request.timeoutInterval = 30
        
        urlSession = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
        webSocketTask = urlSession?.webSocketTask(with: request)
        
        return try await withCheckedThrowingContinuation { continuation in
            self.connectionContinuation = continuation
            webSocketTask?.resume()
            
            // Start receiving messages
            receiveMessage()
            
            // Timeout after 30 seconds
            Task {
                try? await Task.sleep(nanoseconds: 30_000_000_000)
                if !self.isConnected {
                    self.connectionContinuation?.resume(throwing: GatewayError.connectionTimeout)
                    self.connectionContinuation = nil
                }
            }
        }
    }
    
    func disconnect() {
        webSocketTask?.cancel(with: .normalClosure, reason: nil)
        webSocketTask = nil
        urlSession?.invalidateAndCancel()
        urlSession = nil
        isConnected = false
    }
    
    // MARK: - Messaging
    
    func sendMessage(_ text: String) async throws -> String {
        guard isConnected else { throw GatewayError.notConnected }
        
        let requestId = UUID().uuidString
        let request = NodeRequest(
            id: requestId,
            type: .chat,
            payload: ["message": text]
        )
        
        return try await sendRequest(request)
    }
    
    // MARK: - Pairing
    
    func requestPairingCode() async throws -> String {
        guard isConnected else { throw GatewayError.notConnected }
        
        let requestId = UUID().uuidString
        let request = NodeRequest(
            id: requestId,
            type: .pairing,
            payload: ["action": "request_code"]
        )
        
        return try await sendRequest(request)
    }
    
    // MARK: - Canvas
    
    func createCanvas() async throws -> CanvasState {
        guard isConnected else { throw GatewayError.notConnected }
        
        let requestId = UUID().uuidString
        let request = NodeRequest(
            id: requestId,
            type: .canvas,
            payload: ["action": "create"]
        )
        
        let response = try await sendRequest(request)
        guard let data = response.data(using: .utf8),
              let canvas = try? JSONDecoder().decode(CanvasState.self, from: data) else {
            throw GatewayError.invalidResponse
        }
        
        return canvas
    }
    
    func updateCanvasComponent(canvasId: String, component: CanvasComponent) async throws {
        guard isConnected else { throw GatewayError.notConnected }
        
        let encoder = JSONEncoder()
        let componentData = try encoder.encode(component)
        let componentJSON = String(data: componentData, encoding: .utf8) ?? "{}"
        
        let requestId = UUID().uuidString
        let request = NodeRequest(
            id: requestId,
            type: .canvas,
            payload: [
                "action": "update",
                "canvasId": canvasId,
                "component": componentJSON
            ]
        )
        
        _ = try await sendRequest(request)
    }
    
    // MARK: - Image Analysis
    
    func analyzeImage(_ base64Image: String) async throws -> String {
        guard isConnected else { throw GatewayError.notConnected }
        
        let requestId = UUID().uuidString
        let request = NodeRequest(
            id: requestId,
            type: .image,
            payload: [
                "action": "analyze",
                "image": base64Image
            ]
        )
        
        return try await sendRequest(request)
    }
    
    // MARK: - Private Methods
    
    private func sendRequest(_ request: NodeRequest) async throws -> String {
        let encoder = JSONEncoder()
        let data = try encoder.encode(request)
        let jsonString = String(data: data, encoding: .utf8)!
        
        let message = URLSessionWebSocketTask.Message.string(jsonString)
        try await webSocketTask?.send(message)
        
        return try await withCheckedThrowingContinuation { continuation in
            pendingRequests[request.id] = continuation
            
            // Timeout after 120 seconds
            Task {
                try? await Task.sleep(nanoseconds: 120_000_000_000)
                if let cont = self.pendingRequests.removeValue(forKey: request.id) {
                    cont.resume(throwing: GatewayError.requestTimeout)
                }
            }
        }
    }
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            guard let self = self else { return }
            
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self.handleMessage(text)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        self.handleMessage(text)
                    }
                @unknown default:
                    break
                }
                // Continue receiving
                self.receiveMessage()
                
            case .failure(let error):
                self.handleDisconnect(error: error)
            }
        }
    }
    
    private func handleMessage(_ text: String) {
        // Mark as connected on first message
        if !isConnected {
            isConnected = true
            reconnectAttempts = 0
            connectionContinuation?.resume()
            connectionContinuation = nil
            DispatchQueue.main.async {
                self.delegate?.gatewayDidConnect()
            }
        }
        
        guard let data = text.data(using: .utf8),
              let response = try? JSONDecoder().decode(NodeResponse.self, from: data) else {
            DispatchQueue.main.async {
                self.delegate?.gatewayDidReceiveMessage(text)
            }
            return
        }
        
        // Check pending requests
        if let requestId = response.requestId,
           let continuation = pendingRequests.removeValue(forKey: requestId) {
            if let error = response.error {
                continuation.resume(throwing: GatewayError.serverError(error))
            } else {
                continuation.resume(returning: response.payload ?? "")
            }
            return
        }
        
        // Handle push messages
        DispatchQueue.main.async {
            switch response.type {
            case "message":
                if let payload = response.payload {
                    self.delegate?.gatewayDidReceiveMessage(payload)
                }
            case "canvas":
                if let payload = response.payload,
                   let data = payload.data(using: .utf8),
                   let canvas = try? JSONDecoder().decode(CanvasState.self, from: data) {
                    self.delegate?.gatewayDidReceiveCanvasUpdate(canvas)
                }
            default:
                break
            }
        }
    }
    
    private func handleDisconnect(error: Error?) {
        isConnected = false
        DispatchQueue.main.async {
            self.delegate?.gatewayDidDisconnect(error: error)
        }
        attemptReconnect()
    }
    
    private func attemptReconnect() {
        guard reconnectAttempts < maxReconnectAttempts else {
            DispatchQueue.main.async {
                self.delegate?.gatewayDidDisconnect(error: GatewayError.maxReconnectAttemptsReached)
            }
            return
        }
        
        reconnectAttempts += 1
        let delay = Double(reconnectAttempts) * 2
        
        Task {
            try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            try? await self.connect()
        }
    }
}

// MARK: - URLSession Delegate

extension GatewayService: URLSessionWebSocketDelegate {
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        isConnected = true
        reconnectAttempts = 0
        connectionContinuation?.resume()
        connectionContinuation = nil
        DispatchQueue.main.async {
            self.delegate?.gatewayDidConnect()
        }
    }
    
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        isConnected = false
        let reasonString = reason.flatMap { String(data: $0, encoding: .utf8) }
        DispatchQueue.main.async {
            self.delegate?.gatewayDidDisconnect(error: GatewayError.disconnected(reason: reasonString ?? "Unknown", code: closeCode.rawValue))
        }
        attemptReconnect()
    }
}

// MARK: - Types

struct NodeRequest: Codable {
    let id: String
    let type: RequestType
    let payload: [String: String]
    
    enum RequestType: String, Codable {
        case chat
        case pairing
        case canvas
        case image
        case command
    }
}

struct NodeResponse: Codable {
    let requestId: String?
    let type: String
    let payload: String?
    let error: String?
}

enum GatewayError: LocalizedError {
    case invalidURL
    case notConnected
    case connectionTimeout
    case requestTimeout
    case maxReconnectAttemptsReached
    case disconnected(reason: String, code: Int)
    case serverError(String)
    case invalidResponse
    case unknown
    
    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Invalid gateway URL"
        case .notConnected: return "Not connected to gateway"
        case .connectionTimeout: return "Connection timeout"
        case .requestTimeout: return "Request timeout"
        case .maxReconnectAttemptsReached: return "Max reconnection attempts reached"
        case .disconnected(let reason, let code): return "Disconnected: \(reason) (code: \(code))"
        case .serverError(let message): return "Server error: \(message)"
        case .invalidResponse: return "Invalid response from server"
        case .unknown: return "Unknown error"
        }
    }
}
