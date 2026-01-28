package com.cursorbot.node.service

import android.util.Log
import com.cursorbot.node.model.CanvasComponent
import com.cursorbot.node.model.CanvasState
import com.cursorbot.node.model.NodeRequest
import com.cursorbot.node.model.NodeResponse
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import org.java_websocket.client.WebSocketClient
import org.java_websocket.handshake.ServerHandshake
import java.net.URI
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

@Singleton
class GatewayService @Inject constructor() {
    
    companion object {
        private const val TAG = "GatewayService"
        private const val CONNECTION_TIMEOUT = 30000L
        private const val REQUEST_TIMEOUT = 120000L
    }
    
    private var webSocket: WebSocketClient? = null
    private val gson = Gson()
    private val pendingRequests = ConcurrentHashMap<String, (Result<String>) -> Unit>()
    
    private var onConnected: (() -> Unit)? = null
    private var onDisconnected: ((String?) -> Unit)? = null
    private var onMessage: ((String) -> Unit)? = null
    private var onCanvasUpdate: ((CanvasState) -> Unit)? = null
    
    var isConnected: Boolean = false
        private set
    
    fun setCallbacks(
        onConnected: () -> Unit,
        onDisconnected: (String?) -> Unit,
        onMessage: (String) -> Unit,
        onCanvasUpdate: (CanvasState) -> Unit
    ) {
        this.onConnected = onConnected
        this.onDisconnected = onDisconnected
        this.onMessage = onMessage
        this.onCanvasUpdate = onCanvasUpdate
    }
    
    suspend fun connect(url: String, token: String, deviceId: String) = withContext(Dispatchers.IO) {
        val wsUrl = url.replace("http", "ws") + "/ws/node"
        val uri = URI(wsUrl)
        
        val headers = mapOf(
            "Authorization" to "Bearer $token",
            "X-Device-ID" to deviceId,
            "X-Device-Type" to "android"
        )
        
        webSocket = object : WebSocketClient(uri, headers) {
            override fun onOpen(handshakedata: ServerHandshake?) {
                Log.d(TAG, "WebSocket connected")
                isConnected = true
                onConnected?.invoke()
            }
            
            override fun onMessage(message: String?) {
                message?.let { handleMessage(it) }
            }
            
            override fun onClose(code: Int, reason: String?, remote: Boolean) {
                Log.d(TAG, "WebSocket closed: $reason (code: $code)")
                isConnected = false
                onDisconnected?.invoke(reason)
            }
            
            override fun onError(ex: Exception?) {
                Log.e(TAG, "WebSocket error", ex)
                isConnected = false
                onDisconnected?.invoke(ex?.message)
            }
        }
        
        withTimeout(CONNECTION_TIMEOUT) {
            suspendCancellableCoroutine { continuation ->
                val originalOnConnected = onConnected
                val originalOnDisconnected = onDisconnected
                
                onConnected = {
                    originalOnConnected?.invoke()
                    if (continuation.isActive) {
                        continuation.resume(Unit)
                    }
                    onConnected = originalOnConnected
                    onDisconnected = originalOnDisconnected
                }
                
                onDisconnected = { error ->
                    originalOnDisconnected?.invoke(error)
                    if (continuation.isActive) {
                        continuation.resumeWithException(Exception(error ?: "Connection failed"))
                    }
                    onConnected = originalOnConnected
                    onDisconnected = originalOnDisconnected
                }
                
                webSocket?.connect()
                
                continuation.invokeOnCancellation {
                    webSocket?.close()
                    onConnected = originalOnConnected
                    onDisconnected = originalOnDisconnected
                }
            }
        }
    }
    
    fun disconnect() {
        webSocket?.close()
        webSocket = null
        isConnected = false
    }
    
    private fun handleMessage(text: String) {
        try {
            val response = gson.fromJson(text, NodeResponse::class.java)
            
            // Check pending requests
            response.requestId?.let { requestId ->
                pendingRequests.remove(requestId)?.let { callback ->
                    if (response.error != null) {
                        callback(Result.failure(Exception(response.error)))
                    } else {
                        callback(Result.success(response.payload ?: ""))
                    }
                    return
                }
            }
            
            // Handle push messages
            when (response.type) {
                "message" -> {
                    response.payload?.let { onMessage?.invoke(it) }
                }
                "canvas" -> {
                    response.payload?.let { payload ->
                        try {
                            val canvas = gson.fromJson(payload, CanvasState::class.java)
                            onCanvasUpdate?.invoke(canvas)
                        } catch (e: Exception) {
                            Log.e(TAG, "Failed to parse canvas update", e)
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to handle message", e)
            onMessage?.invoke(text)
        }
    }
    
    private suspend fun sendRequest(request: NodeRequest): String = withContext(Dispatchers.IO) {
        if (!isConnected) {
            throw Exception("Not connected to gateway")
        }
        
        withTimeout(REQUEST_TIMEOUT) {
            suspendCancellableCoroutine { continuation ->
                pendingRequests[request.id] = { result ->
                    if (continuation.isActive) {
                        result.fold(
                            onSuccess = { continuation.resume(it) },
                            onFailure = { continuation.resumeWithException(it) }
                        )
                    }
                }
                
                val json = gson.toJson(request)
                webSocket?.send(json)
                
                continuation.invokeOnCancellation {
                    pendingRequests.remove(request.id)
                }
            }
        }
    }
    
    suspend fun sendMessage(text: String): String? {
        val request = NodeRequest(
            id = UUID.randomUUID().toString(),
            type = "chat",
            payload = mapOf("message" to text)
        )
        return sendRequest(request)
    }
    
    suspend fun requestPairingCode(): String {
        val request = NodeRequest(
            id = UUID.randomUUID().toString(),
            type = "pairing",
            payload = mapOf("action" to "request_code")
        )
        return sendRequest(request)
    }
    
    suspend fun createCanvas(): CanvasState {
        val request = NodeRequest(
            id = UUID.randomUUID().toString(),
            type = "canvas",
            payload = mapOf("action" to "create")
        )
        val response = sendRequest(request)
        return gson.fromJson(response, CanvasState::class.java)
    }
    
    suspend fun updateCanvasComponent(canvasId: String, component: CanvasComponent) {
        val componentJson = gson.toJson(component)
        val request = NodeRequest(
            id = UUID.randomUUID().toString(),
            type = "canvas",
            payload = mapOf(
                "action" to "update",
                "canvasId" to canvasId,
                "component" to componentJson
            )
        )
        sendRequest(request)
    }
    
    suspend fun analyzeImage(base64Image: String): String {
        val request = NodeRequest(
            id = UUID.randomUUID().toString(),
            type = "image",
            payload = mapOf(
                "action" to "analyze",
                "image" to base64Image
            )
        )
        return sendRequest(request)
    }
}
