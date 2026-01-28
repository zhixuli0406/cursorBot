// MenuBarView.swift
// Menu bar dropdown view

import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject var appState: AppState
    @State private var quickMessage = ""
    
    var body: some View {
        VStack(spacing: 0) {
            // Status Header
            HStack {
                Circle()
                    .fill(appState.connectionStatus.color)
                    .frame(width: 8, height: 8)
                Text(appState.connectionStatus.description)
                    .font(.caption)
                Spacer()
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
            .background(Color.secondary.opacity(0.1))
            
            Divider()
            
            // Quick Chat
            HStack {
                TextField("Quick message...", text: $quickMessage)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        sendQuickMessage()
                    }
                
                Button(action: sendQuickMessage) {
                    Image(systemName: "arrow.up.circle.fill")
                }
                .buttonStyle(.plain)
                .disabled(quickMessage.isEmpty || !appState.isGatewayConnected)
            }
            .padding()
            
            Divider()
            
            // Actions
            VStack(spacing: 0) {
                MenuButton(title: "New Conversation", icon: "square.and.pencil") {
                    appState.startNewConversation()
                    NSApp.activate(ignoringOtherApps: true)
                }
                
                MenuButton(
                    title: appState.isTalkModeActive ? "Stop Talk Mode" : "Start Talk Mode",
                    icon: appState.isTalkModeActive ? "mic.fill" : "mic"
                ) {
                    appState.toggleTalkMode()
                }
                
                Divider()
                    .padding(.horizontal)
                
                MenuButton(title: "Open Dashboard", icon: "rectangle.on.rectangle") {
                    NSApp.activate(ignoringOtherApps: true)
                }
                
                MenuButton(title: "Settings...", icon: "gear") {
                    NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
                }
            }
            
            Divider()
            
            // Footer
            HStack {
                Text("CursorBot v0.4")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Button("Quit") {
                    NSApp.terminate(nil)
                }
                .buttonStyle(.plain)
                .font(.caption)
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
        }
        .frame(width: 280)
    }
    
    private func sendQuickMessage() {
        guard !quickMessage.isEmpty, appState.isGatewayConnected else { return }
        let message = quickMessage
        quickMessage = ""
        
        Task {
            await appState.sendMessage(message)
        }
    }
}

struct MenuButton: View {
    let title: String
    let icon: String
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                    .frame(width: 20)
                Text(title)
                Spacer()
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Additional Views

struct LogsView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Logs")
                    .font(.headline)
                Spacer()
                Button("Close") { dismiss() }
            }
            .padding()
            
            Divider()
            
            List(appState.logs) { entry in
                HStack(alignment: .top) {
                    Text(entry.level.rawValue)
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(entry.level.color)
                        .frame(width: 60, alignment: .leading)
                    
                    Text(entry.message)
                        .font(.caption)
                    
                    Spacer()
                    
                    Text(entry.timestamp, style: .time)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
        }
        .frame(width: 600, height: 400)
    }
}

struct NetworkInspectorView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Network Inspector")
                    .font(.headline)
                Spacer()
                Button("Close") { dismiss() }
            }
            .padding()
            
            Divider()
            
            if appState.networkRequests.isEmpty {
                ContentUnavailableView(
                    "No Requests",
                    systemImage: "network",
                    description: Text("Network requests will appear here")
                )
            } else {
                List(appState.networkRequests) { request in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(request.method)
                                .font(.caption)
                                .fontWeight(.bold)
                            Text(request.url)
                                .font(.caption)
                            Spacer()
                            if let code = request.statusCode {
                                Text("\(code)")
                                    .font(.caption)
                                    .foregroundColor(code < 400 ? .green : .red)
                            }
                        }
                        Text("\(String(format: "%.2f", request.duration * 1000))ms")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
            }
        }
        .frame(width: 600, height: 400)
    }
}

// MARK: - Preview

#Preview {
    MenuBarView()
        .environmentObject(AppState.shared)
}
