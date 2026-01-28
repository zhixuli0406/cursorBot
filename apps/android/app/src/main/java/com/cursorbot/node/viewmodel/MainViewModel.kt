package com.cursorbot.node.viewmodel

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cursorbot.node.model.*
import com.cursorbot.node.service.GatewayService
import com.cursorbot.node.service.PreferencesManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.Date
import java.util.UUID
import javax.inject.Inject

@HiltViewModel
class MainViewModel @Inject constructor(
    private val gatewayService: GatewayService,
    private val preferencesManager: PreferencesManager
) : ViewModel() {
    
    companion object {
        private const val TAG = "MainViewModel"
    }
    
    // Connection State
    private val _connectionStatus = MutableStateFlow<ConnectionStatus>(ConnectionStatus.Disconnected)
    val connectionStatus: StateFlow<ConnectionStatus> = _connectionStatus.asStateFlow()
    
    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected.asStateFlow()
    
    private val _gatewayUrl = MutableStateFlow("")
    val gatewayUrl: StateFlow<String> = _gatewayUrl.asStateFlow()
    
    // Talk Mode State
    private val _isTalkModeActive = MutableStateFlow(false)
    val isTalkModeActive: StateFlow<Boolean> = _isTalkModeActive.asStateFlow()
    
    private val _isListening = MutableStateFlow(false)
    val isListening: StateFlow<Boolean> = _isListening.asStateFlow()
    
    private val _isSpeaking = MutableStateFlow(false)
    val isSpeaking: StateFlow<Boolean> = _isSpeaking.asStateFlow()
    
    private val _currentTranscript = MutableStateFlow("")
    val currentTranscript: StateFlow<String> = _currentTranscript.asStateFlow()
    
    // Voice Wake State
    private val _voiceWakeEnabled = MutableStateFlow(false)
    val voiceWakeEnabled: StateFlow<Boolean> = _voiceWakeEnabled.asStateFlow()
    
    private val _voiceWakePhrase = MutableStateFlow("hey cursor")
    val voiceWakePhrase: StateFlow<String> = _voiceWakePhrase.asStateFlow()
    
    // Canvas State
    private val _canvasState = MutableStateFlow<CanvasState?>(null)
    val canvasState: StateFlow<CanvasState?> = _canvasState.asStateFlow()
    
    private val _isCanvasActive = MutableStateFlow(false)
    val isCanvasActive: StateFlow<Boolean> = _isCanvasActive.asStateFlow()
    
    // Messages
    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages.asStateFlow()
    
    // Screen Recording
    private val _recordingState = MutableStateFlow(RecordingState())
    val recordingState: StateFlow<RecordingState> = _recordingState.asStateFlow()
    
    // Pairing
    private val _pairingCode = MutableStateFlow<String?>(null)
    val pairingCode: StateFlow<String?> = _pairingCode.asStateFlow()
    
    // Device ID
    val deviceId: String = preferencesManager.getDeviceId()
    
    init {
        loadSavedSettings()
        setupGatewayCallbacks()
    }
    
    private fun loadSavedSettings() {
        viewModelScope.launch {
            _gatewayUrl.value = preferencesManager.getGatewayUrl()
            // Don't auto-enable voice wake on startup
            // _voiceWakeEnabled.value = preferencesManager.getVoiceWakeEnabled()
            _voiceWakeEnabled.value = false
            
            // Auto-connect if URL is saved
            if (_gatewayUrl.value.isNotEmpty()) {
                connectToGateway(_gatewayUrl.value, preferencesManager.getToken())
            }
        }
    }
    
    private fun setupGatewayCallbacks() {
        gatewayService.setCallbacks(
            onConnected = {
                viewModelScope.launch {
                    _isConnected.value = true
                    _connectionStatus.value = ConnectionStatus.Connected
                    Log.d(TAG, "Gateway connected")
                }
            },
            onDisconnected = { error ->
                viewModelScope.launch {
                    _isConnected.value = false
                    _connectionStatus.value = if (error != null) {
                        ConnectionStatus.Error(error)
                    } else {
                        ConnectionStatus.Disconnected
                    }
                    Log.d(TAG, "Gateway disconnected: $error")
                }
            },
            onMessage = { message ->
                viewModelScope.launch {
                    val aiMessage = Message(
                        role = MessageRole.ASSISTANT,
                        content = message,
                        timestamp = Date()
                    )
                    _messages.value = _messages.value + aiMessage
                }
            },
            onCanvasUpdate = { canvas ->
                viewModelScope.launch {
                    _canvasState.value = canvas
                }
            }
        )
    }
    
    // Connection Methods
    fun connectToGateway(url: String, token: String) {
        viewModelScope.launch {
            _connectionStatus.value = ConnectionStatus.Connecting
            _gatewayUrl.value = url
            
            try {
                gatewayService.connect(url, token, deviceId)
                preferencesManager.saveGatewayUrl(url)
                preferencesManager.saveToken(token)
            } catch (e: Exception) {
                _connectionStatus.value = ConnectionStatus.Error(e.message ?: "Connection failed")
                Log.e(TAG, "Connection failed", e)
            }
        }
    }
    
    fun disconnect() {
        viewModelScope.launch {
            gatewayService.disconnect()
            _isConnected.value = false
            _connectionStatus.value = ConnectionStatus.Disconnected
        }
    }
    
    // Messaging Methods
    fun sendMessage(text: String) {
        viewModelScope.launch {
            if (!_isConnected.value) return@launch
            
            val userMessage = Message(
                role = MessageRole.USER,
                content = text,
                timestamp = Date()
            )
            _messages.value = _messages.value + userMessage
            
            try {
                val response = gatewayService.sendMessage(text)
                if (response != null) {
                    val aiMessage = Message(
                        role = MessageRole.ASSISTANT,
                        content = response,
                        timestamp = Date()
                    )
                    _messages.value = _messages.value + aiMessage
                    
                    if (_isTalkModeActive.value) {
                        // Trigger TTS
                        speakResponse(response)
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to send message", e)
            }
        }
    }
    
    // Talk Mode Methods
    fun toggleTalkMode() {
        if (_isTalkModeActive.value) {
            stopTalkMode()
        } else {
            startTalkMode()
        }
    }
    
    fun startTalkMode() {
        if (!_isConnected.value) {
            Log.w(TAG, "Cannot start Talk Mode: not connected")
            return
        }
        Log.d(TAG, "Starting Talk Mode")
        _isTalkModeActive.value = true
        _isListening.value = true
    }
    
    fun stopTalkMode() {
        Log.d(TAG, "Stopping Talk Mode")
        _isTalkModeActive.value = false
        _isListening.value = false
    }
    
    fun onTranscript(transcript: String) {
        _currentTranscript.value = transcript
        
        // Check for voice wake phrase when voice wake is enabled but talk mode is not active
        if (_voiceWakeEnabled.value && !_isTalkModeActive.value) {
            val lowercased = transcript.lowercase()
            if (lowercased.contains(_voiceWakePhrase.value.lowercase())) {
                Log.d(TAG, "Voice wake phrase detected!")
                startTalkMode()
            }
        }
    }
    
    fun onTranscriptComplete(transcript: String) {
        _currentTranscript.value = ""
        if (transcript.isNotEmpty() && _isTalkModeActive.value) {
            sendMessage(transcript)
        }
    }
    
    private fun speakResponse(text: String) {
        _isSpeaking.value = true
        // TTS will be handled by the UI layer
    }
    
    fun onSpeakComplete() {
        _isSpeaking.value = false
    }
    
    // Voice Wake Methods
    fun toggleVoiceWake() {
        val newValue = !_voiceWakeEnabled.value
        _voiceWakeEnabled.value = newValue
        preferencesManager.saveVoiceWakeEnabled(newValue)
        
        if (newValue) {
            Log.d(TAG, "Voice Wake enabled - listening for '${_voiceWakePhrase.value}'")
            _isListening.value = true
        } else {
            Log.d(TAG, "Voice Wake disabled")
            if (!_isTalkModeActive.value) {
                _isListening.value = false
            }
        }
    }
    
    fun setVoiceWakePhrase(phrase: String) {
        _voiceWakePhrase.value = phrase.lowercase()
        Log.d(TAG, "Voice Wake phrase set to '${_voiceWakePhrase.value}'")
    }
    
    // Canvas Methods
    fun createCanvas() {
        viewModelScope.launch {
            if (!_isConnected.value) return@launch
            
            try {
                val canvas = gatewayService.createCanvas()
                _canvasState.value = canvas
                _isCanvasActive.value = true
            } catch (e: Exception) {
                Log.e(TAG, "Failed to create canvas", e)
            }
        }
    }
    
    fun updateCanvasComponent(component: CanvasComponent) {
        viewModelScope.launch {
            val canvasId = _canvasState.value?.id ?: return@launch
            
            try {
                gatewayService.updateCanvasComponent(canvasId, component)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to update canvas component", e)
            }
        }
    }
    
    fun closeCanvas() {
        _canvasState.value = null
        _isCanvasActive.value = false
    }
    
    // Screen Recording Methods
    fun startRecording() {
        _recordingState.value = _recordingState.value.copy(isRecording = true)
    }
    
    fun stopRecording() {
        _recordingState.value = _recordingState.value.copy(isRecording = false)
    }
    
    fun updateRecordingDuration(duration: Long) {
        _recordingState.value = _recordingState.value.copy(duration = duration)
    }
    
    fun setRecordingPath(path: String) {
        _recordingState.value = _recordingState.value.copy(outputPath = path)
    }
    
    // Pairing Methods
    fun requestPairingCode() {
        viewModelScope.launch {
            if (!_isConnected.value) return@launch
            
            try {
                val code = gatewayService.requestPairingCode()
                _pairingCode.value = code
            } catch (e: Exception) {
                Log.e(TAG, "Failed to request pairing code", e)
            }
        }
    }
    
    // Cleanup
    override fun onCleared() {
        super.onCleared()
        gatewayService.disconnect()
    }
}
