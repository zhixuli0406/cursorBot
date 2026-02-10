// GatewayService.swift
// Remote Gateway connection and communication service

import Foundation
import Starscream
import Combine

protocol GatewayServiceDelegate: AnyObject {
    func gatewayDidConnect()
    func gatewayDidDisconnect(error: Error?)
    func gatewayDidReceiveMessage(_ message: String)
}

@MainActor
class GatewayService: NSObject {
    private let url: String
    private let token: String
    private var socket: WebSocket?
    private var isConnected = false
    private var reconnectAttempts = 0
    private let maxReconnectAttempts = 5
    private var pingTimer: Timer?
    
    weak var delegate: GatewayServiceDelegate?
    
    private var pendingRequests: [String: CheckedContinuation<String, Error>] = [:]
    
    init(url: String, token: String) {
        self.url = url
        self.token = token
        super.init()
    }
    
    // MARK: - Connection
    
    func connect() async throws {
        guard let wsURL = URL(string: url.replacingOccurrences(of: "http", with: "ws") + "/ws") else {
            throw GatewayError.invalidURL
        }
        
        var request = URLRequest(url: wsURL)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.timeoutInterval = 30
        
        socket = WebSocket(request: request)
        socket?.delegate = self
        
        return try await withCheckedThrowingContinuation { continuation in
            self.connectionContinuation = continuation
            socket?.connect()
            
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
    
    private var connectionContinuation: CheckedContinuation<Void, Error>?
    
    func disconnect() {
        pingTimer?.invalidate()
        pingTimer = nil
        socket?.disconnect()
        socket = nil
        isConnected = false
    }
    
    // MARK: - Messaging
    
    func sendMessage(_ text: String) async throws -> String {
        guard isConnected else {
            throw GatewayError.notConnected
        }
        
        let requestId = UUID().uuidString
        let request = GatewayRequest(
            id: requestId,
            type: .chat,
            payload: ["message": text]
        )
        
        let encoder = JSONEncoder()
        let data = try encoder.encode(request)
        let jsonString = String(data: data, encoding: .utf8)!
        
        socket?.write(string: jsonString)
        
        return try await withCheckedThrowingContinuation { continuation in
            pendingRequests[requestId] = continuation
            
            // Timeout after 120 seconds
            Task {
                try? await Task.sleep(nanoseconds: 120_000_000_000)
                if let cont = self.pendingRequests.removeValue(forKey: requestId) {
                    cont.resume(throwing: GatewayError.requestTimeout)
                }
            }
        }
    }
    
    func sendCommand(_ command: String, args: [String: Any] = [:]) async throws -> [String: Any] {
        guard isConnected else {
            throw GatewayError.notConnected
        }
        
        let requestId = UUID().uuidString
        var payload = args
        payload["command"] = command
        
        let request = GatewayRequest(
            id: requestId,
            type: .command,
            payload: payload.mapValues { "\($0)" }
        )
        
        let encoder = JSONEncoder()
        let data = try encoder.encode(request)
        let jsonString = String(data: data, encoding: .utf8)!
        
        socket?.write(string: jsonString)
        
        let response = try await withCheckedThrowingContinuation { continuation in
            pendingRequests[requestId] = continuation
        }
        
        // Parse response as JSON
        if let responseData = response.data(using: .utf8),
           let json = try? JSONSerialization.jsonObject(with: responseData) as? [String: Any] {
            return json
        }
        
        return ["response": response]
    }
    
    // MARK: - Health Check
    
    private func startPingTimer() {
        pingTimer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.sendPing()
            }
        }
    }
    
    private func sendPing() {
        socket?.write(ping: Data())
    }
    
    // MARK: - Reconnection
    
    private func attemptReconnect() {
        guard reconnectAttempts < maxReconnectAttempts else {
            delegate?.gatewayDidDisconnect(error: GatewayError.maxReconnectAttemptsReached)
            return
        }
        
        reconnectAttempts += 1
        let delay = Double(reconnectAttempts) * 2  // Exponential backoff
        
        Task {
            try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            try? await self.connect()
        }
    }
}

// MARK: - WebSocket Delegate

extension GatewayService: WebSocketDelegate {
    nonisolated func didReceive(event: WebSocketEvent, client: WebSocketClient) {
        Task { @MainActor in
            switch event {
            case .connected:
                isConnected = true
                reconnectAttempts = 0
                startPingTimer()
                connectionContinuation?.resume()
                connectionContinuation = nil
                delegate?.gatewayDidConnect()
                
            case .disconnected(let reason, let code):
                isConnected = false
                pingTimer?.invalidate()
                delegate?.gatewayDidDisconnect(error: GatewayError.disconnected(reason: reason, code: code))
                attemptReconnect()
                
            case .text(let text):
                handleMessage(text)
                
            case .binary(let data):
                if let text = String(data: data, encoding: .utf8) {
                    handleMessage(text)
                }
                
            case .ping:
                socket?.write(pong: Data())
                
            case .pong:
                break
                
            case .viabilityChanged(let viable):
                if !viable {
                    attemptReconnect()
                }
                
            case .reconnectSuggested:
                attemptReconnect()
                
            case .cancelled:
                isConnected = false
                delegate?.gatewayDidDisconnect(error: nil)
                
            case .error(let error):
                connectionContinuation?.resume(throwing: error ?? GatewayError.unknown)
                connectionContinuation = nil
                delegate?.gatewayDidDisconnect(error: error)
                
            case .peerClosed:
                isConnected = false
                delegate?.gatewayDidDisconnect(error: nil)
            }
        }
    }
    
    private func handleMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let response = try? JSONDecoder().decode(GatewayResponse.self, from: data) else {
            delegate?.gatewayDidReceiveMessage(text)
            return
        }
        
        // Check if this is a response to a pending request
        if let requestId = response.requestId,
           let continuation = pendingRequests.removeValue(forKey: requestId) {
            if let error = response.error {
                continuation.resume(throwing: GatewayError.serverError(error))
            } else {
                continuation.resume(returning: response.payload ?? "")
            }
            return
        }
        
        // Otherwise, it's a push message
        if let payload = response.payload {
            delegate?.gatewayDidReceiveMessage(payload)
        }
    }
}

// MARK: - Gateway Types

struct GatewayRequest: Codable {
    let id: String
    let type: RequestType
    let payload: [String: String]
    
    enum RequestType: String, Codable {
        case chat
        case command
        case subscribe
        case unsubscribe
    }
}

struct GatewayResponse: Codable {
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
    case disconnected(reason: String, code: UInt16)
    case serverError(String)
    case unknown
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid gateway URL"
        case .notConnected:
            return "Not connected to gateway"
        case .connectionTimeout:
            return "Connection timeout"
        case .requestTimeout:
            return "Request timeout"
        case .maxReconnectAttemptsReached:
            return "Max reconnection attempts reached"
        case .disconnected(let reason, let code):
            return "Disconnected: \(reason) (code: \(code))"
        case .serverError(let message):
            return "Server error: \(message)"
        case .unknown:
            return "Unknown error"
        }
    }
}
