// MainTabView.swift
// Main tab-based navigation for iOS Node

import SwiftUI

struct MainTabView: View {
    @EnvironmentObject var appState: NodeAppState
    @State private var selectedTab = 0
    
    var body: some View {
        TabView(selection: $selectedTab) {
            ChatView()
                .tabItem {
                    Label("Chat", systemImage: "message")
                }
                .tag(0)
            
            CanvasView()
                .tabItem {
                    Label("Canvas", systemImage: "rectangle.on.rectangle")
                }
                .tag(1)
            
            CameraView()
                .tabItem {
                    Label("Camera", systemImage: "camera")
                }
                .tag(2)
            
            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(3)
        }
        .onAppear {
            // Auto-connect if URL is saved
            if !appState.gatewayURL.isEmpty && !appState.isConnected {
                Task {
                    try? await appState.connectToGateway(url: appState.gatewayURL, token: "")
                }
            }
        }
    }
}

// MARK: - Chat View

struct ChatView: View {
    @EnvironmentObject var appState: NodeAppState
    @State private var messageText = ""
    @FocusState private var isInputFocused: Bool
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Connection Banner
                if !appState.isConnected {
                    ConnectionBanner()
                }
                
                // Messages
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            ForEach(appState.messages) { message in
                                MessageRow(message: message)
                                    .id(message.id)
                            }
                        }
                        .padding()
                    }
                    .onChange(of: appState.messages.count) { _, _ in
                        if let lastMessage = appState.messages.last {
                            withAnimation {
                                proxy.scrollTo(lastMessage.id, anchor: .bottom)
                            }
                        }
                    }
                }
                
                // Talk Mode Indicator
                if appState.isTalkModeActive {
                    TalkModeIndicator()
                }
                
                // Input
                InputBar(text: $messageText, isFocused: _isInputFocused) {
                    sendMessage()
                }
            }
            .navigationTitle("CursorBot")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    ConnectionStatusIndicator()
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { appState.toggleTalkMode() }) {
                        Image(systemName: appState.isTalkModeActive ? "mic.fill" : "mic")
                            .foregroundColor(appState.isTalkModeActive ? .red : .primary)
                    }
                }
            }
        }
    }
    
    private func sendMessage() {
        guard !messageText.isEmpty else { return }
        let text = messageText
        messageText = ""
        
        Task {
            await appState.sendMessage(text)
        }
    }
}

// MARK: - Supporting Views

struct ConnectionBanner: View {
    @EnvironmentObject var appState: NodeAppState
    
    var body: some View {
        HStack {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(.orange)
            Text("Not connected")
                .font(.caption)
            Spacer()
            NavigationLink("Connect") {
                ConnectionView()
            }
            .font(.caption)
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color.orange.opacity(0.1))
    }
}

struct ConnectionStatusIndicator: View {
    @EnvironmentObject var appState: NodeAppState
    
    var body: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(appState.connectionStatus.color)
                .frame(width: 8, height: 8)
            Text(appState.isConnected ? "Online" : "Offline")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
}

struct MessageRow: View {
    let message: Message
    
    var body: some View {
        HStack {
            if message.role == .user {
                Spacer(minLength: 60)
            }
            
            VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 4) {
                Text(message.content)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(message.role == .user ? Color.blue : Color(.systemGray5))
                    .foregroundColor(message.role == .user ? .white : .primary)
                    .cornerRadius(16)
                
                Text(message.timestamp, style: .time)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            
            if message.role == .assistant {
                Spacer(minLength: 60)
            }
        }
    }
}

struct TalkModeIndicator: View {
    @EnvironmentObject var appState: NodeAppState
    
    var body: some View {
        HStack {
            Image(systemName: "waveform")
                .symbolEffect(.variableColor.iterative)
            
            Text(appState.isSpeaking ? "Speaking..." : "Listening...")
                .font(.caption)
            
            if !appState.currentTranscript.isEmpty {
                Text(appState.currentTranscript)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            }
            
            Spacer()
            
            Button("Stop") {
                appState.stopTalkMode()
            }
            .font(.caption)
            .buttonStyle(.bordered)
            .tint(.red)
        }
        .padding()
        .background(Color(.systemGray6))
    }
}

struct InputBar: View {
    @Binding var text: String
    @FocusState var isFocused: Bool
    let onSend: () -> Void
    
    var body: some View {
        HStack(spacing: 12) {
            TextField("Type a message...", text: $text, axis: .vertical)
                .textFieldStyle(.plain)
                .lineLimit(1...5)
                .focused($isFocused)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color(.systemGray6))
                .cornerRadius(20)
            
            Button(action: onSend) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.title2)
            }
            .disabled(text.isEmpty)
        }
        .padding()
    }
}

// MARK: - Preview

#Preview {
    MainTabView()
        .environmentObject(NodeAppState.shared)
}
