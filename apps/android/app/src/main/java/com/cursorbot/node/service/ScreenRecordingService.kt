package com.cursorbot.node.service

import android.app.*
import android.content.Context
import android.content.Intent
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.MediaRecorder
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.IBinder
import android.util.DisplayMetrics
import android.view.WindowManager
import androidx.core.app.NotificationCompat
import com.cursorbot.node.CursorBotApplication
import com.cursorbot.node.MainActivity
import com.cursorbot.node.R
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

class ScreenRecordingService : Service() {
    
    companion object {
        const val ACTION_START = "com.cursorbot.node.action.START_RECORDING"
        const val ACTION_STOP = "com.cursorbot.node.action.STOP_RECORDING"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_RESULT_DATA = "result_data"
        
        private const val NOTIFICATION_ID = 1001
        private const val VIDEO_MIME_TYPE = "video/mp4"
        private const val VIDEO_BIT_RATE = 6000000
        private const val VIDEO_FRAME_RATE = 30
    }
    
    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var mediaRecorder: MediaRecorder? = null
    private var outputPath: String? = null
    
    private var screenWidth: Int = 0
    private var screenHeight: Int = 0
    private var screenDensity: Int = 0
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onCreate() {
        super.onCreate()
        
        // Get screen metrics
        val windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val metrics = DisplayMetrics()
        windowManager.defaultDisplay.getMetrics(metrics)
        
        screenWidth = metrics.widthPixels
        screenHeight = metrics.heightPixels
        screenDensity = metrics.densityDpi
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED)
                val resultData = intent.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)
                
                if (resultCode == Activity.RESULT_OK && resultData != null) {
                    startForeground(NOTIFICATION_ID, createNotification())
                    startRecording(resultCode, resultData)
                }
            }
            ACTION_STOP -> {
                stopRecording()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
        
        return START_NOT_STICKY
    }
    
    private fun createNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        
        val stopIntent = PendingIntent.getService(
            this,
            0,
            Intent(this, ScreenRecordingService::class.java).apply {
                action = ACTION_STOP
            },
            PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, CursorBotApplication.CHANNEL_ID_RECORDING)
            .setContentTitle("Screen Recording")
            .setContentText("Recording in progress...")
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentIntent(pendingIntent)
            .addAction(android.R.drawable.ic_media_pause, "Stop", stopIntent)
            .setOngoing(true)
            .build()
    }
    
    private fun startRecording(resultCode: Int, resultData: Intent) {
        // Create output file
        val dateFormat = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault())
        val fileName = "recording_${dateFormat.format(Date())}.mp4"
        val outputDir = getExternalFilesDir(null)
        outputPath = File(outputDir, fileName).absolutePath
        
        // Setup MediaRecorder
        mediaRecorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            MediaRecorder(this)
        } else {
            @Suppress("DEPRECATION")
            MediaRecorder()
        }.apply {
            setVideoSource(MediaRecorder.VideoSource.SURFACE)
            setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            setVideoEncoder(MediaRecorder.VideoEncoder.H264)
            setVideoEncodingBitRate(VIDEO_BIT_RATE)
            setVideoFrameRate(VIDEO_FRAME_RATE)
            setVideoSize(screenWidth, screenHeight)
            setOutputFile(outputPath)
            
            prepare()
        }
        
        // Get MediaProjection
        val projectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        mediaProjection = projectionManager.getMediaProjection(resultCode, resultData)
        
        // Create VirtualDisplay
        virtualDisplay = mediaProjection?.createVirtualDisplay(
            "ScreenRecording",
            screenWidth,
            screenHeight,
            screenDensity,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            mediaRecorder?.surface,
            null,
            null
        )
        
        // Start recording
        mediaRecorder?.start()
    }
    
    private fun stopRecording() {
        try {
            mediaRecorder?.stop()
            mediaRecorder?.reset()
        } catch (e: Exception) {
            // Ignore
        }
        
        mediaRecorder?.release()
        mediaRecorder = null
        
        virtualDisplay?.release()
        virtualDisplay = null
        
        mediaProjection?.stop()
        mediaProjection = null
        
        // Broadcast recording complete
        val intent = Intent("com.cursorbot.node.RECORDING_COMPLETE").apply {
            putExtra("output_path", outputPath)
        }
        sendBroadcast(intent)
    }
    
    override fun onDestroy() {
        super.onDestroy()
        stopRecording()
    }
}
