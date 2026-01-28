// CanvasView.swift
// Live Canvas view for iOS Node

import SwiftUI

struct CanvasView: View {
    @EnvironmentObject var appState: NodeAppState
    @State private var scale: CGFloat = 1.0
    @State private var offset: CGSize = .zero
    @State private var selectedComponent: String?
    
    var body: some View {
        NavigationStack {
            ZStack {
                if appState.isCanvasActive, let canvas = appState.canvasState {
                    CanvasContentView(
                        canvas: canvas,
                        scale: $scale,
                        offset: $offset,
                        selectedComponent: $selectedComponent
                    )
                } else {
                    EmptyCanvasView()
                }
            }
            .navigationTitle("Canvas")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        if appState.isCanvasActive {
                            Button("Add Text") {
                                addComponent(.text)
                            }
                            Button("Add Code") {
                                addComponent(.code)
                            }
                            Button("Add Image") {
                                addComponent(.image)
                            }
                            Divider()
                            Button("Close Canvas", role: .destructive) {
                                appState.closeCanvas()
                            }
                        } else {
                            Button("Create Canvas") {
                                createCanvas()
                            }
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                }
            }
        }
    }
    
    private func createCanvas() {
        Task {
            try? await appState.createCanvas()
        }
    }
    
    private func addComponent(_ type: CanvasComponent.ComponentType) {
        guard let canvas = appState.canvasState else { return }
        
        let component = CanvasComponent(
            type: type,
            x: canvas.width / 2 - 100,
            y: canvas.height / 2 - 50,
            content: type == .text ? "New Text" : type == .code ? "// Code here" : ""
        )
        
        Task {
            try? await appState.updateCanvasComponent(component)
        }
    }
}

// MARK: - Empty Canvas View

struct EmptyCanvasView: View {
    @EnvironmentObject var appState: NodeAppState
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "rectangle.on.rectangle")
                .font(.system(size: 60))
                .foregroundColor(.secondary)
            
            Text("No Active Canvas")
                .font(.headline)
            
            Text("Create a canvas to visualize your work")
                .font(.caption)
                .foregroundColor(.secondary)
            
            Button("Create Canvas") {
                Task {
                    try? await appState.createCanvas()
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(!appState.isConnected)
        }
    }
}

// MARK: - Canvas Content View

struct CanvasContentView: View {
    let canvas: CanvasState
    @Binding var scale: CGFloat
    @Binding var offset: CGSize
    @Binding var selectedComponent: String?
    
    @GestureState private var gestureScale: CGFloat = 1.0
    @GestureState private var gestureOffset: CGSize = .zero
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // Background
                Color(.systemGray6)
                    .ignoresSafeArea()
                
                // Canvas content
                ForEach(canvas.components) { component in
                    CanvasComponentView(
                        component: component,
                        isSelected: selectedComponent == component.id
                    )
                    .position(
                        x: (component.x + offset.width + gestureOffset.width) * scale * gestureScale,
                        y: (component.y + offset.height + gestureOffset.height) * scale * gestureScale
                    )
                    .scaleEffect(scale * gestureScale)
                    .onTapGesture {
                        selectedComponent = component.id
                    }
                }
            }
            .gesture(
                MagnificationGesture()
                    .updating($gestureScale) { value, state, _ in
                        state = value
                    }
                    .onEnded { value in
                        scale *= value
                        scale = max(0.5, min(scale, 3.0))
                    }
            )
            .simultaneousGesture(
                DragGesture()
                    .updating($gestureOffset) { value, state, _ in
                        state = value.translation
                    }
                    .onEnded { value in
                        offset.width += value.translation.width / scale
                        offset.height += value.translation.height / scale
                    }
            )
        }
    }
}

// MARK: - Canvas Component View

struct CanvasComponentView: View {
    let component: CanvasComponent
    let isSelected: Bool
    
    var body: some View {
        Group {
            switch component.type {
            case .text:
                TextComponentView(component: component)
            case .code:
                CodeComponentView(component: component)
            case .image:
                ImageComponentView(component: component)
            case .button:
                ButtonComponentView(component: component)
            case .input:
                InputComponentView(component: component)
            case .container:
                ContainerComponentView(component: component)
            case .markdown:
                MarkdownComponentView(component: component)
            case .chart:
                ChartComponentView(component: component)
            case .camera:
                CameraComponentView(component: component)
            }
        }
        .frame(width: component.width, height: component.height)
        .overlay(
            RoundedRectangle(cornerRadius: component.style?.cornerRadius ?? 8)
                .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 2)
        )
    }
}

struct TextComponentView: View {
    let component: CanvasComponent
    
    var body: some View {
        Text(component.content)
            .font(.system(size: component.style?.fontSize ?? 16))
            .foregroundColor(component.style?.toColor(component.style?.textColor) ?? .primary)
            .padding()
            .background(component.style?.toColor(component.style?.backgroundColor) ?? Color(.systemBackground))
            .cornerRadius(component.style?.cornerRadius ?? 8)
    }
}

struct CodeComponentView: View {
    let component: CanvasComponent
    
    var body: some View {
        ScrollView {
            Text(component.content)
                .font(.system(.body, design: .monospaced))
                .foregroundColor(.green)
                .padding()
        }
        .background(Color.black)
        .cornerRadius(component.style?.cornerRadius ?? 8)
    }
}

struct ImageComponentView: View {
    let component: CanvasComponent
    
    var body: some View {
        if let data = Data(base64Encoded: component.content),
           let uiImage = UIImage(data: data) {
            Image(uiImage: uiImage)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .cornerRadius(component.style?.cornerRadius ?? 8)
        } else {
            Image(systemName: "photo")
                .font(.largeTitle)
                .foregroundColor(.secondary)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color(.systemGray5))
                .cornerRadius(component.style?.cornerRadius ?? 8)
        }
    }
}

struct ButtonComponentView: View {
    let component: CanvasComponent
    
    var body: some View {
        Button(component.content) {
            // Handle tap
        }
        .buttonStyle(.borderedProminent)
    }
}

struct InputComponentView: View {
    let component: CanvasComponent
    @State private var text = ""
    
    var body: some View {
        TextField(component.content, text: $text)
            .textFieldStyle(.roundedBorder)
            .padding()
    }
}

struct ContainerComponentView: View {
    let component: CanvasComponent
    
    var body: some View {
        RoundedRectangle(cornerRadius: component.style?.cornerRadius ?? 8)
            .fill(component.style?.toColor(component.style?.backgroundColor) ?? Color(.systemGray6))
            .overlay(
                RoundedRectangle(cornerRadius: component.style?.cornerRadius ?? 8)
                    .stroke(component.style?.toColor(component.style?.borderColor) ?? Color.gray, lineWidth: component.style?.borderWidth ?? 1)
            )
    }
}

struct MarkdownComponentView: View {
    let component: CanvasComponent
    
    var body: some View {
        ScrollView {
            Text(component.content)
                .padding()
        }
        .background(Color(.systemBackground))
        .cornerRadius(component.style?.cornerRadius ?? 8)
    }
}

struct ChartComponentView: View {
    let component: CanvasComponent
    
    var body: some View {
        // Placeholder for chart
        VStack {
            Image(systemName: "chart.bar")
                .font(.largeTitle)
            Text("Chart")
                .font(.caption)
        }
        .foregroundColor(.secondary)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGray6))
        .cornerRadius(component.style?.cornerRadius ?? 8)
    }
}

struct CameraComponentView: View {
    let component: CanvasComponent
    
    var body: some View {
        // Live camera preview placeholder
        VStack {
            Image(systemName: "camera.viewfinder")
                .font(.largeTitle)
            Text("Camera")
                .font(.caption)
        }
        .foregroundColor(.secondary)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.black)
        .cornerRadius(component.style?.cornerRadius ?? 8)
    }
}

// MARK: - Preview

#Preview {
    CanvasView()
        .environmentObject(NodeAppState.shared)
}
