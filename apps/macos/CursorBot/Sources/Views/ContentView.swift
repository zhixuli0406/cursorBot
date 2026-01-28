// ContentView.swift
// Main content view for CursorBot macOS App

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @State private var messageText = ""
    @State private var showSidebar = true
    
    var body: some View {
        NavigationSplitView(columnVisibility: .constant(showSidebar ? .all : .detailOnly)) {
            SidebarView()
        } detail: {
            ZStack {
                ChatView(messageText: $messageText)
                
                // Talk Mode Overlay
                if appState.isTalkModeActive {
                    TalkModeOverlay()
                }
                
                // Debug Panel
                if appState.showDebugPanel {
                    DebugPanelView()
                        .frame(width: 350)
                        .transition(.move(edge: .trailing))
                }
            }
        }
        .toolbar {
            ToolbarItemGroup(placement: .navigation) {
                Button(action: { showSidebar.toggle() }) {
                    Image(systemName: "sidebar.left")
                }
            }
            
            ToolbarItemGroup(placement: .principal) {
                ConnectionStatusView()
            }
            
            ToolbarItemGroup(placement: .primaryAction) {
                Button(action: { appState.toggleTalkMode() }) {
                    Image(systemName: appState.isTalkModeActive ? "mic.fill" : "mic")
                        .foregroundColor(appState.isTalkModeActive ? .red : .primary)
                }
                .help(appState.isTalkModeActive ? "Stop Talk Mode" : "Start Talk Mode")
                
                Button(action: { appState.showDebugPanel.toggle() }) {
                    Image(systemName: "ladybug")
                        .foregroundColor(appState.showDebugPanel ? .accentColor : .primary)
                }
                .help("Debug Panel")
                
                Button(action: { appState.showGatewaySheet = true }) {
                    Image(systemName: "antenna.radiowaves.left.and.right")
                        .foregroundColor(appState.isGatewayConnected ? .green : .secondary)
                }
                .help("Gateway Connection")
            }
        }
        .sheet(isPresented: $appState.showGatewaySheet) {
            GatewayConnectionSheet()
        }
        .sheet(isPresented: $appState.showLogs) {
            LogsView()
        }
        .sheet(isPresented: $appState.showNetworkInspector) {
            NetworkInspectorView()
        }
    }
}

// MARK: - Sidebar View

struct SidebarView: View {
    @EnvironmentObject var appState: AppState
    
    var body: some View {
        List(selection: $appState.selectedConversationId) {
            Section("Conversations") {
                ForEach(appState.conversations) { conversation in
                    NavigationLink(value: conversation.id) {
                        VStack(alignment: .leading) {
                            Text(conversation.title)
                                .font(.headline)
                            Text("\(conversation.messages.count) messages")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }
            }
        }
        .listStyle(.sidebar)
        .navigationSplitViewColumnWidth(min: 200, ideal: 250)
        .toolbar {
            ToolbarItem {
                Button(action: { appState.startNewConversation() }) {
                    Image(systemName: "square.and.pencil")
                }
            }
        }
    }
}

// MARK: - Chat View

struct ChatView: View {
    @EnvironmentObject var appState: AppState
    @Binding var messageText: String
    @FocusState private var isInputFocused: Bool
    
    var body: some View {
        VStack(spacing: 0) {
            // Messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 16) {
                        ForEach(appState.currentMessages) { message in
                            MessageBubble(message: message)
                                .id(message.id)
                        }
                    }
                    .padding()
                }
                .onChange(of: appState.currentMessages.count) { _, _ in
                    if let lastMessage = appState.currentMessages.last {
                        withAnimation {
                            proxy.scrollTo(lastMessage.id, anchor: .bottom)
                        }
                    }
                }
            }
            
            Divider()
            
            // Input area
            HStack(spacing: 12) {
                TextField("Type a message...", text: $messageText, axis: .vertical)
                    .textFieldStyle(.plain)
                    .lineLimit(1...5)
                    .focused($isInputFocused)
                    .onSubmit {
                        sendMessage()
                    }
                
                Button(action: sendMessage) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.title2)
                }
                .buttonStyle(.plain)
                .disabled(messageText.isEmpty || !appState.isGatewayConnected)
            }
            .padding()
            .background(.ultraThinMaterial)
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

// MARK: - Message Bubble

struct MessageBubble: View {
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
                    .background(message.role == .user ? Color.accentColor : Color.secondary.opacity(0.2))
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

// MARK: - Connection Status View

struct ConnectionStatusView: View {
    @EnvironmentObject var appState: AppState
    
    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(appState.connectionStatus.color)
                .frame(width: 8, height: 8)
            
            Text(appState.connectionStatus.description)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(.ultraThinMaterial)
        .cornerRadius(12)
    }
}

// MARK: - Talk Mode Overlay

struct TalkModeOverlay: View {
    @EnvironmentObject var appState: AppState
    @ObservedObject private var audioService = AudioService.shared
    
    var body: some View {
        VStack(spacing: 20) {
            Spacer()
            
            // Waveform visualization
            HStack(spacing: 4) {
                ForEach(0..<20, id: \.self) { i in
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color.accentColor)
                        .frame(width: 4, height: CGFloat.random(in: 10...(30 + Double(audioService.audioLevel) * 100)))
                        .animation(.easeInOut(duration: 0.1), value: audioService.audioLevel)
                }
            }
            .frame(height: 60)
            
            // Current transcript
            if !audioService.currentTranscript.isEmpty {
                Text(audioService.currentTranscript)
                    .font(.title3)
                    .multilineTextAlignment(.center)
                    .padding()
                    .background(.ultraThinMaterial)
                    .cornerRadius(12)
            }
            
            // Status
            Text(appState.isSpeaking ? "Speaking..." : "Listening...")
                .font(.headline)
                .foregroundColor(.secondary)
            
            // Stop button
            Button("Stop Talk Mode") {
                appState.stopTalkMode()
            }
            .buttonStyle(.borderedProminent)
            .tint(.red)
            
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(.ultraThinMaterial)
    }
}

// MARK: - Preview

#Preview {
    ContentView()
        .environmentObject(AppState.shared)
}
