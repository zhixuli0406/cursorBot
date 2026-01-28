package com.cursorbot.node.service

import android.content.Context
import android.content.SharedPreferences
import dagger.hilt.android.qualifiers.ApplicationContext
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PreferencesManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    companion object {
        private const val PREFS_NAME = "cursorbot_prefs"
        private const val KEY_GATEWAY_URL = "gateway_url"
        private const val KEY_TOKEN = "token"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_VOICE_WAKE_ENABLED = "voice_wake_enabled"
        private const val KEY_VOICE_WAKE_PHRASE = "voice_wake_phrase"
        private const val KEY_VOICE_SENSITIVITY = "voice_sensitivity"
        private const val KEY_SPEAKING_RATE = "speaking_rate"
        private const val KEY_LANGUAGE = "language"
    }
    
    private val prefs: SharedPreferences by lazy {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }
    
    // Device ID
    fun getDeviceId(): String {
        var deviceId = prefs.getString(KEY_DEVICE_ID, null)
        if (deviceId == null) {
            deviceId = UUID.randomUUID().toString()
            prefs.edit().putString(KEY_DEVICE_ID, deviceId).apply()
        }
        return deviceId
    }
    
    // Gateway Settings
    fun getGatewayUrl(): String {
        return prefs.getString(KEY_GATEWAY_URL, "") ?: ""
    }
    
    fun saveGatewayUrl(url: String) {
        prefs.edit().putString(KEY_GATEWAY_URL, url).apply()
    }
    
    fun getToken(): String {
        return prefs.getString(KEY_TOKEN, "") ?: ""
    }
    
    fun saveToken(token: String) {
        prefs.edit().putString(KEY_TOKEN, token).apply()
    }
    
    // Voice Settings
    fun isVoiceWakeEnabled(): Boolean {
        return prefs.getBoolean(KEY_VOICE_WAKE_ENABLED, false)
    }
    
    fun getVoiceWakeEnabled(): Boolean = isVoiceWakeEnabled()
    
    fun setVoiceWakeEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_VOICE_WAKE_ENABLED, enabled).apply()
    }
    
    fun saveVoiceWakeEnabled(enabled: Boolean) = setVoiceWakeEnabled(enabled)
    
    fun getVoiceWakePhrase(): String {
        return prefs.getString(KEY_VOICE_WAKE_PHRASE, "Hey Cursor") ?: "Hey Cursor"
    }
    
    fun setVoiceWakePhrase(phrase: String) {
        prefs.edit().putString(KEY_VOICE_WAKE_PHRASE, phrase).apply()
    }
    
    fun getVoiceSensitivity(): Float {
        return prefs.getFloat(KEY_VOICE_SENSITIVITY, 0.5f)
    }
    
    fun setVoiceSensitivity(sensitivity: Float) {
        prefs.edit().putFloat(KEY_VOICE_SENSITIVITY, sensitivity).apply()
    }
    
    fun getSpeakingRate(): Float {
        return prefs.getFloat(KEY_SPEAKING_RATE, 1.0f)
    }
    
    fun setSpeakingRate(rate: Float) {
        prefs.edit().putFloat(KEY_SPEAKING_RATE, rate).apply()
    }
    
    fun getLanguage(): String {
        return prefs.getString(KEY_LANGUAGE, "en-US") ?: "en-US"
    }
    
    fun setLanguage(language: String) {
        prefs.edit().putString(KEY_LANGUAGE, language).apply()
    }
    
    // Clear all
    fun clearAll() {
        val deviceId = getDeviceId()  // Preserve device ID
        prefs.edit().clear().apply()
        prefs.edit().putString(KEY_DEVICE_ID, deviceId).apply()
    }
}
