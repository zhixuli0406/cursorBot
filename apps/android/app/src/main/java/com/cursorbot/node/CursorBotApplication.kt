package com.cursorbot.node

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class CursorBotApplication : Application() {
    
    companion object {
        const val CHANNEL_ID_RECORDING = "screen_recording"
        const val CHANNEL_ID_VOICE = "voice_wake"
        const val CHANNEL_ID_GENERAL = "general"
    }
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }
    
    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = getSystemService(NotificationManager::class.java)
            
            // Screen Recording Channel
            val recordingChannel = NotificationChannel(
                CHANNEL_ID_RECORDING,
                "Screen Recording",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Notifications for screen recording service"
            }
            
            // Voice Wake Channel
            val voiceChannel = NotificationChannel(
                CHANNEL_ID_VOICE,
                "Voice Wake",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Notifications for voice wake service"
            }
            
            // General Channel
            val generalChannel = NotificationChannel(
                CHANNEL_ID_GENERAL,
                "General",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "General notifications"
            }
            
            notificationManager.createNotificationChannels(
                listOf(recordingChannel, voiceChannel, generalChannel)
            )
        }
    }
}
