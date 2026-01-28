// CameraView.swift
// Camera view for iOS Node

import SwiftUI
import AVFoundation

struct CameraView: View {
    @EnvironmentObject var appState: NodeAppState
    @StateObject private var cameraService = CameraService()
    @State private var showCapturedImage = false
    @State private var analysisResult: String?
    @State private var isAnalyzing = false
    @State private var flashMode: AVCaptureDevice.FlashMode = .auto
    @State private var currentZoom: CGFloat = 1.0
    
    var body: some View {
        NavigationStack {
            ZStack {
                // Camera Preview
                CameraPreviewView(previewLayer: cameraService.previewLayer)
                    .ignoresSafeArea()
                    .onTapGesture { location in
                        // Focus on tap
                        let point = CGPoint(
                            x: location.x / UIScreen.main.bounds.width,
                            y: location.y / UIScreen.main.bounds.height
                        )
                        cameraService.focus(at: point)
                    }
                    .gesture(
                        MagnificationGesture()
                            .onChanged { value in
                                let newZoom = currentZoom * value
                                cameraService.setZoom(newZoom)
                            }
                            .onEnded { value in
                                currentZoom *= value
                            }
                    )
                
                // Controls Overlay
                VStack {
                    // Top controls
                    HStack {
                        Button(action: { toggleFlash() }) {
                            Image(systemName: flashIcon)
                                .font(.title2)
                                .foregroundColor(.white)
                                .padding()
                                .background(Color.black.opacity(0.5))
                                .clipShape(Circle())
                        }
                        
                        Spacer()
                        
                        Button(action: { switchCamera() }) {
                            Image(systemName: "arrow.triangle.2.circlepath.camera")
                                .font(.title2)
                                .foregroundColor(.white)
                                .padding()
                                .background(Color.black.opacity(0.5))
                                .clipShape(Circle())
                        }
                    }
                    .padding()
                    
                    Spacer()
                    
                    // Analysis result
                    if let result = analysisResult {
                        Text(result)
                            .padding()
                            .background(Color.black.opacity(0.7))
                            .foregroundColor(.white)
                            .cornerRadius(12)
                            .padding()
                    }
                    
                    // Bottom controls
                    HStack(spacing: 60) {
                        // Gallery button
                        Button(action: { showCapturedImage = true }) {
                            if let image = cameraService.capturedImage {
                                Image(uiImage: image)
                                    .resizable()
                                    .scaledToFill()
                                    .frame(width: 50, height: 50)
                                    .clipShape(RoundedRectangle(cornerRadius: 8))
                            } else {
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(Color.gray.opacity(0.5))
                                    .frame(width: 50, height: 50)
                            }
                        }
                        
                        // Capture button
                        Button(action: { capturePhoto() }) {
                            ZStack {
                                Circle()
                                    .stroke(Color.white, lineWidth: 3)
                                    .frame(width: 70, height: 70)
                                
                                Circle()
                                    .fill(Color.white)
                                    .frame(width: 60, height: 60)
                            }
                        }
                        .disabled(isAnalyzing)
                        
                        // Analyze button
                        Button(action: { analyzeCurrentFrame() }) {
                            VStack {
                                Image(systemName: "sparkles")
                                    .font(.title2)
                                Text("Analyze")
                                    .font(.caption)
                            }
                            .foregroundColor(.white)
                            .padding()
                            .background(Color.blue.opacity(0.8))
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                        .disabled(!appState.isConnected || isAnalyzing)
                    }
                    .padding(.bottom, 30)
                }
                
                // Loading overlay
                if isAnalyzing {
                    Color.black.opacity(0.5)
                        .ignoresSafeArea()
                    
                    VStack {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            .scaleEffect(1.5)
                        Text("Analyzing...")
                            .foregroundColor(.white)
                            .padding(.top)
                    }
                }
            }
            .onAppear {
                cameraService.startSession()
            }
            .onDisappear {
                cameraService.stopSession()
            }
            .sheet(isPresented: $showCapturedImage) {
                CapturedImageView(image: cameraService.capturedImage)
            }
            .navigationTitle("Camera")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
        }
    }
    
    private var flashIcon: String {
        switch flashMode {
        case .auto: return "bolt.badge.a"
        case .on: return "bolt.fill"
        case .off: return "bolt.slash"
        @unknown default: return "bolt.badge.a"
        }
    }
    
    private func toggleFlash() {
        switch flashMode {
        case .auto: flashMode = .on
        case .on: flashMode = .off
        case .off: flashMode = .auto
        @unknown default: flashMode = .auto
        }
        cameraService.setFlashMode(flashMode)
    }
    
    private func switchCamera() {
        // Toggle between front and back
        cameraService.switchCamera(to: .back)  // Simplified
    }
    
    private func capturePhoto() {
        Task {
            do {
                _ = try await cameraService.capturePhoto()
            } catch {
                print("Failed to capture photo: \(error)")
            }
        }
    }
    
    private func analyzeCurrentFrame() {
        guard let image = cameraService.capturedImage ?? UIImage() as UIImage? else { return }
        
        isAnalyzing = true
        
        Task {
            do {
                // Capture if no image
                let imageToAnalyze: UIImage
                if cameraService.capturedImage == nil {
                    imageToAnalyze = try await cameraService.capturePhoto()
                } else {
                    imageToAnalyze = cameraService.capturedImage!
                }
                
                let result = try await appState.analyzeImage(imageToAnalyze)
                analysisResult = result
            } catch {
                analysisResult = "Analysis failed: \(error.localizedDescription)"
            }
            
            isAnalyzing = false
        }
    }
}

// MARK: - Camera Preview View

struct CameraPreviewView: UIViewRepresentable {
    let previewLayer: AVCaptureVideoPreviewLayer?
    
    func makeUIView(context: Context) -> UIView {
        let view = UIView()
        view.backgroundColor = .black
        
        if let previewLayer = previewLayer {
            previewLayer.frame = UIScreen.main.bounds
            view.layer.addSublayer(previewLayer)
        }
        
        return view
    }
    
    func updateUIView(_ uiView: UIView, context: Context) {
        if let previewLayer = previewLayer {
            previewLayer.frame = uiView.bounds
        }
    }
}

// MARK: - Captured Image View

struct CapturedImageView: View {
    @Environment(\.dismiss) private var dismiss
    let image: UIImage?
    
    var body: some View {
        NavigationStack {
            if let image = image {
                Image(uiImage: image)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
            } else {
                ContentUnavailableView(
                    "No Image",
                    systemImage: "photo",
                    description: Text("Capture a photo first")
                )
            }
        }
        .navigationTitle("Captured Photo")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button("Done") {
                    dismiss()
                }
            }
        }
    }
}

// MARK: - Preview

#Preview {
    CameraView()
        .environmentObject(NodeAppState.shared)
}
