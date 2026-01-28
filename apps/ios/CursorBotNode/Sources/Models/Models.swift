// Models.swift
// Data models for CursorBot iOS Node

import Foundation
import SwiftUI

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
    var imageAttachment: String?
}

// MARK: - Canvas

struct CanvasState: Codable, Identifiable {
    let id: String
    var components: [CanvasComponent]
    var width: Double
    var height: Double
    var zoom: Double
    var panOffset: CGPoint
    
    init(id: String = UUID().uuidString) {
        self.id = id
        self.components = []
        self.width = UIScreen.main.bounds.width
        self.height = UIScreen.main.bounds.height
        self.zoom = 1.0
        self.panOffset = .zero
    }
}

struct CanvasComponent: Identifiable, Codable, Equatable {
    let id: String
    var type: ComponentType
    var x: Double
    var y: Double
    var width: Double
    var height: Double
    var content: String
    var style: ComponentStyle?
    var isInteractive: Bool
    
    init(
        id: String = UUID().uuidString,
        type: ComponentType,
        x: Double,
        y: Double,
        width: Double = 200,
        height: Double = 100,
        content: String,
        style: ComponentStyle? = nil,
        isInteractive: Bool = false
    ) {
        self.id = id
        self.type = type
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.content = content
        self.style = style
        self.isInteractive = isInteractive
    }
    
    enum ComponentType: String, Codable {
        case text
        case code
        case image
        case chart
        case markdown
        case button
        case input
        case container
        case camera
    }
}

struct ComponentStyle: Codable, Equatable {
    var backgroundColor: String?
    var textColor: String?
    var borderColor: String?
    var borderWidth: Double?
    var cornerRadius: Double?
    var fontSize: Double?
    var fontWeight: String?
    var shadow: Bool?
    
    func toColor(_ hex: String?) -> Color {
        guard let hex = hex else { return .clear }
        let scanner = Scanner(string: hex.replacingOccurrences(of: "#", with: ""))
        var rgbValue: UInt64 = 0
        scanner.scanHexInt64(&rgbValue)
        
        return Color(
            red: Double((rgbValue & 0xFF0000) >> 16) / 255.0,
            green: Double((rgbValue & 0x00FF00) >> 8) / 255.0,
            blue: Double(rgbValue & 0x0000FF) / 255.0
        )
    }
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

// MARK: - Pairing

struct PairingInfo: Codable {
    let code: String
    let deviceId: String
    let deviceName: String
    let expiresAt: Date
}

// MARK: - API Types

struct ChatRequest: Codable {
    let message: String
    let conversationId: String?
    let attachments: [Attachment]?
}

struct Attachment: Codable {
    let type: String  // "image", "file"
    let data: String  // base64 encoded
    let mimeType: String
}

struct ChatResponse: Codable {
    let response: String
    let conversationId: String
    let canvasUpdate: CanvasState?
}

struct ImageAnalysisRequest: Codable {
    let image: String  // base64
    let prompt: String?
}

struct ImageAnalysisResponse: Codable {
    let analysis: String
    let objects: [DetectedObject]?
}

struct DetectedObject: Codable {
    let label: String
    let confidence: Double
    let boundingBox: CGRect?
}
