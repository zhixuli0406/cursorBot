// CameraService.swift
// Camera capture service for iOS Node

import Foundation
import AVFoundation
import UIKit
import Combine

class CameraService: NSObject, ObservableObject {
    @Published var isRunning = false
    @Published var previewLayer: AVCaptureVideoPreviewLayer?
    @Published var capturedImage: UIImage?
    
    private var captureSession: AVCaptureSession?
    private var photoOutput: AVCapturePhotoOutput?
    private var videoOutput: AVCaptureVideoDataOutput?
    private var currentDevice: AVCaptureDevice?
    
    private var photoContinuation: CheckedContinuation<UIImage, Error>?
    
    enum CameraPosition {
        case front
        case back
    }
    
    override init() {
        super.init()
        setupSession()
    }
    
    // MARK: - Setup
    
    private func setupSession() {
        captureSession = AVCaptureSession()
        captureSession?.sessionPreset = .photo
        
        // Setup input
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
            print("No camera available")
            return
        }
        
        currentDevice = device
        
        do {
            let input = try AVCaptureDeviceInput(device: device)
            if captureSession?.canAddInput(input) == true {
                captureSession?.addInput(input)
            }
        } catch {
            print("Failed to create camera input: \(error)")
            return
        }
        
        // Setup photo output
        photoOutput = AVCapturePhotoOutput()
        if let photoOutput = photoOutput, captureSession?.canAddOutput(photoOutput) == true {
            captureSession?.addOutput(photoOutput)
        }
        
        // Setup video output for real-time processing
        videoOutput = AVCaptureVideoDataOutput()
        videoOutput?.setSampleBufferDelegate(self, queue: DispatchQueue(label: "camera.video"))
        if let videoOutput = videoOutput, captureSession?.canAddOutput(videoOutput) == true {
            captureSession?.addOutput(videoOutput)
        }
        
        // Setup preview layer
        previewLayer = AVCaptureVideoPreviewLayer(session: captureSession!)
        previewLayer?.videoGravity = .resizeAspectFill
    }
    
    // MARK: - Session Control
    
    func startSession() {
        guard let session = captureSession, !session.isRunning else { return }
        
        DispatchQueue.global(qos: .userInitiated).async {
            session.startRunning()
            DispatchQueue.main.async {
                self.isRunning = true
            }
        }
    }
    
    func stopSession() {
        guard let session = captureSession, session.isRunning else { return }
        
        DispatchQueue.global(qos: .userInitiated).async {
            session.stopRunning()
            DispatchQueue.main.async {
                self.isRunning = false
            }
        }
    }
    
    // MARK: - Camera Switch
    
    func switchCamera(to position: CameraPosition) {
        guard let session = captureSession else { return }
        
        session.beginConfiguration()
        
        // Remove current input
        if let currentInput = session.inputs.first as? AVCaptureDeviceInput {
            session.removeInput(currentInput)
        }
        
        // Get new device
        let devicePosition: AVCaptureDevice.Position = position == .front ? .front : .back
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: devicePosition) else {
            session.commitConfiguration()
            return
        }
        
        currentDevice = device
        
        do {
            let input = try AVCaptureDeviceInput(device: device)
            if session.canAddInput(input) {
                session.addInput(input)
            }
        } catch {
            print("Failed to switch camera: \(error)")
        }
        
        session.commitConfiguration()
    }
    
    // MARK: - Photo Capture
    
    func capturePhoto() async throws -> UIImage {
        guard let photoOutput = photoOutput else {
            throw CameraError.notConfigured
        }
        
        return try await withCheckedThrowingContinuation { continuation in
            self.photoContinuation = continuation
            
            let settings = AVCapturePhotoSettings()
            photoOutput.capturePhoto(with: settings, delegate: self)
        }
    }
    
    // MARK: - Focus & Exposure
    
    func focus(at point: CGPoint) {
        guard let device = currentDevice else { return }
        
        do {
            try device.lockForConfiguration()
            
            if device.isFocusPointOfInterestSupported {
                device.focusPointOfInterest = point
                device.focusMode = .autoFocus
            }
            
            if device.isExposurePointOfInterestSupported {
                device.exposurePointOfInterest = point
                device.exposureMode = .autoExpose
            }
            
            device.unlockForConfiguration()
        } catch {
            print("Failed to focus: \(error)")
        }
    }
    
    // MARK: - Zoom
    
    func setZoom(_ factor: CGFloat) {
        guard let device = currentDevice else { return }
        
        let zoomFactor = max(1.0, min(factor, device.activeFormat.videoMaxZoomFactor))
        
        do {
            try device.lockForConfiguration()
            device.videoZoomFactor = zoomFactor
            device.unlockForConfiguration()
        } catch {
            print("Failed to set zoom: \(error)")
        }
    }
    
    // MARK: - Flash
    
    func setFlashMode(_ mode: AVCaptureDevice.FlashMode) {
        guard let device = currentDevice, device.hasFlash else { return }
        
        do {
            try device.lockForConfiguration()
            if device.isFlashModeSupported(mode) {
                // Flash mode is set in photo settings, not on device
            }
            device.unlockForConfiguration()
        } catch {
            print("Failed to set flash: \(error)")
        }
    }
}

// MARK: - Photo Capture Delegate

extension CameraService: AVCapturePhotoCaptureDelegate {
    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        if let error = error {
            photoContinuation?.resume(throwing: error)
            photoContinuation = nil
            return
        }
        
        guard let imageData = photo.fileDataRepresentation(),
              let image = UIImage(data: imageData) else {
            photoContinuation?.resume(throwing: CameraError.processingFailed)
            photoContinuation = nil
            return
        }
        
        DispatchQueue.main.async {
            self.capturedImage = image
        }
        
        photoContinuation?.resume(returning: image)
        photoContinuation = nil
    }
}

// MARK: - Video Data Delegate

extension CameraService: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        // Can be used for real-time image processing
        // e.g., object detection, face detection, etc.
    }
}

// MARK: - Errors

enum CameraError: LocalizedError {
    case notConfigured
    case processingFailed
    case notAvailable
    
    var errorDescription: String? {
        switch self {
        case .notConfigured: return "Camera not configured"
        case .processingFailed: return "Failed to process photo"
        case .notAvailable: return "Camera not available"
        }
    }
}
