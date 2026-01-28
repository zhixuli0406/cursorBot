package com.cursorbot.node.model

import java.util.Date
import java.util.UUID

// Message Models
data class Message(
    val id: String = UUID.randomUUID().toString(),
    val role: MessageRole,
    val content: String,
    val timestamp: Date = Date(),
    val metadata: MessageMetadata? = null
)

enum class MessageRole {
    USER, ASSISTANT, SYSTEM
}

data class MessageMetadata(
    val tokensUsed: Int? = null,
    val model: String? = null,
    val processingTime: Long? = null,
    val imageAttachment: String? = null
)

// Canvas Models
data class CanvasState(
    val id: String = UUID.randomUUID().toString(),
    val components: List<CanvasComponent> = emptyList(),
    val width: Float = 0f,
    val height: Float = 0f,
    val zoom: Float = 1f,
    val panOffsetX: Float = 0f,
    val panOffsetY: Float = 0f
)

data class CanvasComponent(
    val id: String = UUID.randomUUID().toString(),
    val type: ComponentType,
    val x: Float,
    val y: Float,
    val width: Float = 200f,
    val height: Float = 100f,
    val content: String,
    val style: ComponentStyle? = null,
    val isInteractive: Boolean = false
)

enum class ComponentType {
    TEXT, CODE, IMAGE, CHART, MARKDOWN, BUTTON, INPUT, CONTAINER, CAMERA
}

data class ComponentStyle(
    val backgroundColor: String? = null,
    val textColor: String? = null,
    val borderColor: String? = null,
    val borderWidth: Float? = null,
    val cornerRadius: Float? = null,
    val fontSize: Float? = null,
    val fontWeight: String? = null,
    val shadow: Boolean? = null
)

// Gateway Models
data class GatewayConfig(
    val url: String,
    val token: String,
    val name: String = "Default",
    val isDefault: Boolean = false
)

data class GatewayStatus(
    val connected: Boolean,
    val latency: Long? = null,
    val version: String? = null,
    val features: List<String>? = null
)

// Connection Status
sealed class ConnectionStatus {
    object Disconnected : ConnectionStatus()
    object Connecting : ConnectionStatus()
    object Connected : ConnectionStatus()
    data class Error(val message: String) : ConnectionStatus()
    
    val description: String
        get() = when (this) {
            is Disconnected -> "Disconnected"
            is Connecting -> "Connecting..."
            is Connected -> "Connected"
            is Error -> "Error: $message"
        }
}

// Pairing
data class PairingInfo(
    val code: String,
    val deviceId: String,
    val deviceName: String,
    val expiresAt: Date
)

// API Models
data class ChatRequest(
    val message: String,
    val conversationId: String? = null,
    val attachments: List<Attachment>? = null
)

data class Attachment(
    val type: String,
    val data: String,
    val mimeType: String
)

data class ChatResponse(
    val response: String,
    val conversationId: String,
    val canvasUpdate: CanvasState? = null
)

// WebSocket Models
data class NodeRequest(
    val id: String,
    val type: String,
    val payload: Map<String, String>
)

data class NodeResponse(
    val requestId: String?,
    val type: String,
    val payload: String?,
    val error: String?
)

// Screen Recording
data class RecordingState(
    val isRecording: Boolean = false,
    val duration: Long = 0,
    val outputPath: String? = null
)
