// AudioService.swift
// Audio recording, speech recognition, and text-to-speech service

import Foundation
import AVFoundation
import Speech
import AppKit

@MainActor
class AudioService: NSObject, ObservableObject {
    static let shared = AudioService()
    
    // MARK: - Properties
    
    @Published var isListening = false
    @Published var isSpeaking = false
    @Published var audioLevel: Float = 0
    @Published var currentTranscript = ""
    @Published var permissionsGranted = false
    
    private var audioEngine: AVAudioEngine?
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let synthesizer = AVSpeechSynthesizer()
    
    private var transcriptHandler: ((String) -> Void)?
    private var voiceWakeHandler: (() -> Void)?
    private var voiceWakePhrase = "hey cursor"
    
    private var silenceTimer: Timer?
    private let silenceThreshold: TimeInterval = 2.0
    
    private override init() {
        super.init()
        synthesizer.delegate = self
    }
    
    // MARK: - Check Permissions (without requesting)
    
    func checkPermissions() -> Bool {
        let speechStatus = SFSpeechRecognizer.authorizationStatus()
        let audioStatus = AVCaptureDevice.authorizationStatus(for: .audio)
        return speechStatus == .authorized && audioStatus == .authorized
    }
    
    // MARK: - Permissions
    
    func requestPermissions() {
        // Only request permissions if running as a proper app bundle
        // Command-line execution may crash when requesting permissions
        
        // Check current status first
        let speechStatus = SFSpeechRecognizer.authorizationStatus()
        let audioStatus = AVCaptureDevice.authorizationStatus(for: .audio)
        
        print("Speech recognition status: \(speechStatus.rawValue)")
        print("Microphone status: \(audioStatus.rawValue)")
        
        // Only request if not determined yet
        if speechStatus == .notDetermined {
            SFSpeechRecognizer.requestAuthorization { status in
                Task { @MainActor in
                    switch status {
                    case .authorized:
                        print("Speech recognition authorized")
                        self.permissionsGranted = true
                    case .denied:
                        print("Speech recognition denied")
                    case .restricted:
                        print("Speech recognition restricted")
                    case .notDetermined:
                        print("Speech recognition not determined")
                    @unknown default:
                        break
                    }
                }
            }
        }
        
        if audioStatus == .notDetermined {
            AVCaptureDevice.requestAccess(for: .audio) { granted in
                Task { @MainActor in
                    if granted {
                        print("Microphone access granted")
                    } else {
                        print("Microphone access denied")
                    }
                }
            }
        }
        
        // Update permissions status
        permissionsGranted = speechStatus == .authorized && audioStatus == .authorized
    }
    
    // MARK: - Speech Recognition
    
    func startListening(onTranscript: @escaping (String) -> Void) {
        guard !isListening else { return }
        
        // Request permissions first if not granted
        if !checkPermissions() {
            print("Listening: Requesting permissions...")
            requestPermissions()
            return
        }
        
        startListeningInternal(onTranscript: onTranscript)
    }
    
    private func startListeningInternal(onTranscript: @escaping (String) -> Void) {
        guard !isListening else { return }
        guard let recognizer = speechRecognizer, recognizer.isAvailable else {
            print("Speech recognizer not available")
            return
        }
        
        transcriptHandler = onTranscript
        
        do {
            audioEngine = AVAudioEngine()
            guard let audioEngine = audioEngine else { return }
            
            let inputNode = audioEngine.inputNode
            let recordingFormat = inputNode.outputFormat(forBus: 0)
            
            recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
            guard let recognitionRequest = recognitionRequest else { return }
            
            recognitionRequest.shouldReportPartialResults = true
            recognitionRequest.taskHint = .dictation
            
            recognitionTask = recognizer.recognitionTask(with: recognitionRequest) { [weak self] result, error in
                Task { @MainActor [weak self] in
                    guard let self = self else { return }
                    
                    if let result = result {
                        let transcript = result.bestTranscription.formattedString
                        self.currentTranscript = transcript
                        
                        // Reset silence timer
                        self.silenceTimer?.invalidate()
                        self.silenceTimer = Timer.scheduledTimer(withTimeInterval: self.silenceThreshold, repeats: false) { [weak self] _ in
                            Task { @MainActor [weak self] in
                                guard let self = self else { return }
                                if !self.currentTranscript.isEmpty {
                                    self.transcriptHandler?(self.currentTranscript)
                                    self.currentTranscript = ""
                                }
                            }
                        }
                        
                        if result.isFinal {
                            self.silenceTimer?.invalidate()
                            if !transcript.isEmpty {
                                self.transcriptHandler?(transcript)
                            }
                            self.currentTranscript = ""
                        }
                    }
                    
                    if error != nil {
                        let wasVoiceWakeMode = self.isVoiceWakeMode
                        self.stopListening()
                        // Auto-restart if error and voice wake is enabled
                        if wasVoiceWakeMode {
                            try? await Task.sleep(nanoseconds: 1_000_000_000)
                            self.startVoiceWakeListening()
                        }
                    }
                }
            }
            
            inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { [weak self] buffer, _ in
                self?.recognitionRequest?.append(buffer)
                
                // Calculate audio level
                let channelData = buffer.floatChannelData?[0]
                let frames = buffer.frameLength
                var sum: Float = 0
                for i in 0..<Int(frames) {
                    sum += abs(channelData?[i] ?? 0)
                }
                let average = sum / Float(frames)
                
                Task { @MainActor [weak self] in
                    self?.audioLevel = average
                }
            }
            
            audioEngine.prepare()
            try audioEngine.start()
            
            isListening = true
            print("Listening: Started successfully")
            
        } catch {
            print("Failed to start audio engine: \(error)")
        }
    }
    
    func stopListening() {
        silenceTimer?.invalidate()
        silenceTimer = nil
        
        audioEngine?.stop()
        audioEngine?.inputNode.removeTap(onBus: 0)
        
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()
        
        recognitionRequest = nil
        recognitionTask = nil
        audioEngine = nil
        
        isListening = false
        audioLevel = 0
        currentTranscript = ""
    }
    
    // MARK: - Voice Wake
    
    private var isVoiceWakeMode = false
    
    func startVoiceWake(onWake: @escaping () -> Void) {
        voiceWakeHandler = onWake
        isVoiceWakeMode = true
        
        // Check permissions first
        if !checkPermissions() {
            print("Voice Wake: Requesting permissions...")
            requestPermissions()
            
            // Wait for permissions and retry
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
                self?.retryVoiceWakeAfterPermissions()
            }
            return
        }
        
        startVoiceWakeListening()
    }
    
    private func retryVoiceWakeAfterPermissions() {
        guard isVoiceWakeMode else { return }
        
        if checkPermissions() {
            print("Voice Wake: Permissions granted, starting...")
            startVoiceWakeListening()
        } else {
            print("Voice Wake: Permissions not yet granted, retrying in 2s...")
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) { [weak self] in
                self?.retryVoiceWakeAfterPermissions()
            }
        }
    }
    
    private func startVoiceWakeListening() {
        guard isVoiceWakeMode else { return }
        
        print("Voice Wake: Starting to listen for '\(voiceWakePhrase)'...")
        
        startListeningInternal { [weak self] transcript in
            guard let self = self, self.isVoiceWakeMode else { return }
            
            let lowercased = transcript.lowercased()
            print("Voice Wake: Heard: \(lowercased)")
            
            if lowercased.contains(self.voiceWakePhrase) {
                print("Voice Wake: Wake phrase detected!")
                self.voiceWakeHandler?()
            }
        }
    }
    
    func stopVoiceWake() {
        isVoiceWakeMode = false
        voiceWakeHandler = nil
        stopListening()
        print("Voice Wake: Stopped")
    }
    
    func setVoiceWakePhrase(_ phrase: String) {
        voiceWakePhrase = phrase.lowercased()
        print("Voice Wake: Phrase set to '\(voiceWakePhrase)'")
    }
    
    // MARK: - Text-to-Speech
    
    func speak(_ text: String) async {
        return await withCheckedContinuation { continuation in
            let utterance = AVSpeechUtterance(string: text)
            utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
            utterance.rate = AVSpeechUtteranceDefaultSpeechRate
            utterance.volume = 1.0
            
            speakContinuation = continuation
            isSpeaking = true
            synthesizer.speak(utterance)
        }
    }
    
    private var speakContinuation: CheckedContinuation<Void, Never>?
    
    func stopSpeaking() {
        synthesizer.stopSpeaking(at: .immediate)
        isSpeaking = false
    }
    
    // MARK: - Audio Devices
    
    func getInputDevices() -> [AVCaptureDevice] {
        let discoverySession = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.microphone],
            mediaType: .audio,
            position: .unspecified
        )
        return discoverySession.devices
    }
    
    func getOutputDevices() -> [AudioDeviceID] {
        var propertySize: UInt32 = 0
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        
        AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &propertySize)
        
        let deviceCount = Int(propertySize) / MemoryLayout<AudioDeviceID>.size
        var devices = [AudioDeviceID](repeating: 0, count: deviceCount)
        
        AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &propertySize, &devices)
        
        return devices
    }
}

// MARK: - Speech Synthesizer Delegate

extension AudioService: AVSpeechSynthesizerDelegate {
    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor in
            isSpeaking = false
            speakContinuation?.resume()
            speakContinuation = nil
        }
    }
    
    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didCancel utterance: AVSpeechUtterance) {
        Task { @MainActor in
            isSpeaking = false
            speakContinuation?.resume()
            speakContinuation = nil
        }
    }
}
