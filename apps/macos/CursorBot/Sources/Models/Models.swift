// Models.swift
// Data models for CursorBot macOS App

import Foundation

// MARK: - Conversation

struct Conversation: Identifiable, Codable {
    let id: String
    var title: String
    var messages: [Message]
    var createdAt: Date
    var updatedAt: Date
    
    init(id: String = UUID().uuidString, title: String = "New Conversation") {
        self.id = id
        self.title = title
        self.messages = []
        self.createdAt = Date()
        self.updatedAt = Date()
    }
}

// MARK: - Message

struct Message: Identifiable, Codable, Equatable {
    let id: String
    let role: MessageRole
    let content: String
    let timestamp: Date
    var metadata: MessageMetadata?
    
    init(id: String = UUID().uuidString, role: MessageRole, content: String, timestamp: Date = Date(), metadata: MessageMetadata? = nil) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.metadata = metadata
    }
}

enum MessageRole: String, Codable {
    case user
    case assistant
    case system
}

struct MessageMetadata: Codable, Equatable {
    var tokensUsed: Int?
    var model: String?
    var processingTime: TimeInterval?
    var thinkingContent: String?
}

// MARK: - Gateway

struct GatewayConfig: Codable {
    var url: String
    var token: String
    var name: String
    var isDefault: Bool
    
    init(url: String, token: String, name: String = "Default", isDefault: Bool = false) {
        self.url = url
        self.token = token
        self.name = name
        self.isDefault = isDefault
    }
}

struct GatewayStatus: Codable {
    let connected: Bool
    let latency: TimeInterval?
    let version: String?
    let features: [String]?
}

// MARK: - Talk Mode

struct VoiceSettings: Codable {
    var inputDevice: String?
    var outputDevice: String?
    var voiceWakePhrase: String
    var sensitivity: Double
    var language: String
    var speakingRate: Double
    var volume: Double
    
    static var `default`: VoiceSettings {
        VoiceSettings(
            voiceWakePhrase: "Hey Cursor",
            sensitivity: 0.5,
            language: "en-US",
            speakingRate: 1.0,
            volume: 1.0
        )
    }
}

// MARK: - Debug

struct DebugInfo: Codable {
    let appVersion: String
    let buildNumber: String
    let osVersion: String
    let memoryUsage: UInt64
    let cpuUsage: Double
    let gatewayLatency: TimeInterval?
    let activeConnections: Int
    let pendingTasks: Int
}

// MARK: - Canvas

struct CanvasState: Codable {
    var id: String
    var components: [CanvasComponent]
    var width: Double
    var height: Double
    var zoom: Double
    var panOffset: CGPoint
}

struct CanvasComponent: Identifiable, Codable {
    let id: String
    var type: ComponentType
    var x: Double
    var y: Double
    var width: Double
    var height: Double
    var content: String
    var style: ComponentStyle?
    
    enum ComponentType: String, Codable {
        case text
        case code
        case image
        case chart
        case markdown
        case button
        case input
        case container
    }
}

struct ComponentStyle: Codable {
    var backgroundColor: String?
    var textColor: String?
    var borderColor: String?
    var borderWidth: Double?
    var cornerRadius: Double?
    var fontSize: Double?
    var fontWeight: String?
}

// MARK: - API Response

struct APIResponse<T: Codable>: Codable {
    let success: Bool
    let data: T?
    let error: APIError?
}

struct APIError: Codable, Error {
    let code: String
    let message: String
}

// MARK: - Chat Request/Response

struct ChatRequest: Codable {
    let message: String
    let conversationId: String?
    let model: String?
    let temperature: Double?
    let maxTokens: Int?
}

struct ChatResponse: Codable {
    let response: String
    let conversationId: String
    let usage: TokenUsage?
}

struct TokenUsage: Codable {
    let promptTokens: Int
    let completionTokens: Int
    let totalTokens: Int
}
