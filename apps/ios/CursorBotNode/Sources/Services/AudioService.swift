// AudioService.swift
// Audio recording, speech recognition, and TTS for iOS

import Foundation
import AVFoundation
import Speech

class AudioService: NSObject, ObservableObject {
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
    private var isVoiceWakeMode = false
    
    private var silenceTimer: Timer?
    private let silenceThreshold: TimeInterval = 2.0
    private var speakContinuation: CheckedContinuation<Void, Never>?
    
    override init() {
        super.init()
        synthesizer.delegate = self
    }
    
    // MARK: - Permissions
    
    func checkPermissions() -> Bool {
        let speechStatus = SFSpeechRecognizer.authorizationStatus()
        let audioStatus = AVAudioSession.sharedInstance().recordPermission
        let granted = speechStatus == .authorized && audioStatus == .granted
        DispatchQueue.main.async {
            self.permissionsGranted = granted
        }
        return granted
    }
    
    func requestPermissions(completion: @escaping (Bool) -> Void) {
        print("AudioService: Requesting permissions...")
        
        var speechGranted = false
        var audioGranted = false
        let group = DispatchGroup()
        
        // Request speech recognition permission
        group.enter()
        SFSpeechRecognizer.requestAuthorization { status in
            speechGranted = status == .authorized
            print("AudioService: Speech recognition \(speechGranted ? "granted" : "denied")")
            group.leave()
        }
        
        // Request microphone permission
        group.enter()
        AVAudioSession.sharedInstance().requestRecordPermission { granted in
            audioGranted = granted
            print("AudioService: Microphone \(audioGranted ? "granted" : "denied")")
            group.leave()
        }
        
        group.notify(queue: .main) {
            let allGranted = speechGranted && audioGranted
            self.permissionsGranted = allGranted
            print("AudioService: All permissions \(allGranted ? "granted" : "not granted")")
            completion(allGranted)
        }
    }
    
    // MARK: - Speech Recognition
    
    func startListening(onTranscript: @escaping (String) -> Void) {
        guard !isListening else { return }
        
        // Check permissions first
        if !checkPermissions() {
            print("AudioService: Permissions not granted, requesting...")
            requestPermissions { [weak self] granted in
                if granted {
                    self?.startListeningInternal(onTranscript: onTranscript)
                } else {
                    print("AudioService: Permissions denied, cannot start listening")
                }
            }
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
            // Configure audio session
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker, .allowBluetooth])
            try audioSession.setActive(true, options: .notifyOthersOnDeactivation)
            
            audioEngine = AVAudioEngine()
            guard let audioEngine = audioEngine else { return }
            
            let inputNode = audioEngine.inputNode
            let recordingFormat = inputNode.outputFormat(forBus: 0)
            
            recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
            guard let recognitionRequest = recognitionRequest else { return }
            
            recognitionRequest.shouldReportPartialResults = true
            recognitionRequest.taskHint = .dictation
            
            recognitionTask = recognizer.recognitionTask(with: recognitionRequest) { [weak self] result, error in
                guard let self = self else { return }
                
                if let result = result {
                    let transcript = result.bestTranscription.formattedString
                    
                    DispatchQueue.main.async {
                        self.currentTranscript = transcript
                    }
                    
                    // Reset silence timer
                    self.silenceTimer?.invalidate()
                    self.silenceTimer = Timer.scheduledTimer(withTimeInterval: self.silenceThreshold, repeats: false) { [weak self] _ in
                        if let finalTranscript = self?.currentTranscript, !finalTranscript.isEmpty {
                            self?.transcriptHandler?(finalTranscript)
                            DispatchQueue.main.async {
                                self?.currentTranscript = ""
                            }
                        }
                    }
                    
                    if result.isFinal {
                        self.silenceTimer?.invalidate()
                        if !transcript.isEmpty {
                            self.transcriptHandler?(transcript)
                        }
                        DispatchQueue.main.async {
                            self.currentTranscript = ""
                        }
                    }
                }
                
                if error != nil {
                    let wasVoiceWakeMode = self.isVoiceWakeMode
                    self.stopListening()
                    // Auto-restart if voice wake mode
                    if wasVoiceWakeMode {
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
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
                
                DispatchQueue.main.async {
                    self?.audioLevel = average
                }
            }
            
            audioEngine.prepare()
            try audioEngine.start()
            
            DispatchQueue.main.async {
                self.isListening = true
            }
            
            print("AudioService: Listening started successfully")
            
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
        
        DispatchQueue.main.async {
            self.isListening = false
            self.audioLevel = 0
            self.currentTranscript = ""
        }
    }
    
    // MARK: - Voice Wake
    
    func startVoiceWake(onWake: @escaping () -> Void) {
        voiceWakeHandler = onWake
        isVoiceWakeMode = true
        
        print("AudioService: Starting Voice Wake for '\(voiceWakePhrase)'...")
        
        // Check permissions first
        if !checkPermissions() {
            print("AudioService: Voice Wake - requesting permissions...")
            requestPermissions { [weak self] granted in
                guard let self = self, self.isVoiceWakeMode else { return }
                if granted {
                    self.startVoiceWakeListening()
                } else {
                    print("AudioService: Voice Wake - permissions denied")
                }
            }
            return
        }
        
        startVoiceWakeListening()
    }
    
    private func startVoiceWakeListening() {
        guard isVoiceWakeMode else { return }
        
        print("AudioService: Voice Wake listening for '\(voiceWakePhrase)'...")
        
        startListeningInternal { [weak self] transcript in
            guard let self = self, self.isVoiceWakeMode else { return }
            
            let lowercased = transcript.lowercased()
            print("AudioService: Voice Wake heard: '\(lowercased)'")
            
            if lowercased.contains(self.voiceWakePhrase) {
                print("AudioService: Voice Wake phrase detected!")
                self.voiceWakeHandler?()
            }
        }
    }
    
    func stopVoiceWake() {
        print("AudioService: Stopping Voice Wake")
        isVoiceWakeMode = false
        voiceWakeHandler = nil
        stopListening()
    }
    
    func setVoiceWakePhrase(_ phrase: String) {
        voiceWakePhrase = phrase.lowercased()
        print("AudioService: Voice Wake phrase set to '\(voiceWakePhrase)'")
    }
    
    // MARK: - Text-to-Speech
    
    func speak(_ text: String) async {
        return await withCheckedContinuation { continuation in
            let utterance = AVSpeechUtterance(string: text)
            utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
            utterance.rate = AVSpeechUtteranceDefaultSpeechRate
            utterance.volume = 1.0
            
            speakContinuation = continuation
            
            DispatchQueue.main.async {
                self.isSpeaking = true
            }
            
            synthesizer.speak(utterance)
        }
    }
    
    func stopSpeaking() {
        synthesizer.stopSpeaking(at: .immediate)
        DispatchQueue.main.async {
            self.isSpeaking = false
        }
    }
}

// MARK: - Speech Synthesizer Delegate

extension AudioService: AVSpeechSynthesizerDelegate {
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        DispatchQueue.main.async {
            self.isSpeaking = false
        }
        speakContinuation?.resume()
        speakContinuation = nil
    }
    
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didCancel utterance: AVSpeechUtterance) {
        DispatchQueue.main.async {
            self.isSpeaking = false
        }
        speakContinuation?.resume()
        speakContinuation = nil
    }
}
