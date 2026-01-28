// DebugPanelView.swift
// Debug tools panel for development and troubleshooting

import SwiftUI

struct DebugPanelView: View {
    @EnvironmentObject var appState: AppState
    @State private var selectedTab = 0
    
    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Debug Panel")
                    .font(.headline)
                Spacer()
                Button(action: { appState.showDebugPanel = false }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding()
            .background(.ultraThinMaterial)
            
            // Tabs
            Picker("", selection: $selectedTab) {
                Text("Status").tag(0)
                Text("Logs").tag(1)
                Text("Network").tag(2)
                Text("Tools").tag(3)
            }
            .pickerStyle(.segmented)
            .padding(.horizontal)
            .padding(.vertical, 8)
            
            Divider()
            
            // Content
            ScrollView {
                switch selectedTab {
                case 0:
                    StatusTabView()
                case 1:
                    LogsTabView()
                case 2:
                    NetworkTabView()
                case 3:
                    ToolsTabView()
                default:
                    EmptyView()
                }
            }
        }
        .background(.background)
    }
}

// MARK: - Status Tab

struct StatusTabView: View {
    @EnvironmentObject var appState: AppState
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Connection Status
            GroupBox("Connection") {
                VStack(alignment: .leading, spacing: 8) {
                    StatusRow(label: "Gateway", value: appState.connectionStatus.description, color: appState.connectionStatus.color)
                    StatusRow(label: "URL", value: appState.gatewayURL.isEmpty ? "Not set" : appState.gatewayURL)
                    StatusRow(label: "Talk Mode", value: appState.isTalkModeActive ? "Active" : "Inactive", color: appState.isTalkModeActive ? .green : .secondary)
                    StatusRow(label: "Voice Wake", value: appState.voiceWakeEnabled ? "Enabled" : "Disabled", color: appState.voiceWakeEnabled ? .green : .secondary)
                }
            }
            
            // System Info
            GroupBox("System") {
                VStack(alignment: .leading, spacing: 8) {
                    StatusRow(label: "App Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "Unknown")
                    StatusRow(label: "Build", value: Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "Unknown")
                    StatusRow(label: "macOS", value: ProcessInfo.processInfo.operatingSystemVersionString)
                    StatusRow(label: "Memory", value: formatBytes(getMemoryUsage()))
                }
            }
            
            // Messages
            GroupBox("Session") {
                VStack(alignment: .leading, spacing: 8) {
                    StatusRow(label: "Messages", value: "\(appState.currentMessages.count)")
                    StatusRow(label: "Conversations", value: "\(appState.conversations.count)")
                    StatusRow(label: "Log Entries", value: "\(appState.logs.count)")
                }
            }
        }
        .padding()
    }
    
    private func getMemoryUsage() -> UInt64 {
        var info = mach_task_basic_info()
        var count = mach_msg_type_number_t(MemoryLayout<mach_task_basic_info>.size) / 4
        let result = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: 1) {
                task_info(mach_task_self_, task_flavor_t(MACH_TASK_BASIC_INFO), $0, &count)
            }
        }
        return result == KERN_SUCCESS ? info.resident_size : 0
    }
    
    private func formatBytes(_ bytes: UInt64) -> String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .memory
        return formatter.string(fromByteCount: Int64(bytes))
    }
}

struct StatusRow: View {
    let label: String
    let value: String
    var color: Color = .primary
    
    var body: some View {
        HStack {
            Text(label)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .foregroundColor(color)
                .fontWeight(.medium)
        }
        .font(.caption)
    }
}

// MARK: - Logs Tab

struct LogsTabView: View {
    @EnvironmentObject var appState: AppState
    @State private var filterLevel: LogLevel?
    @State private var searchText = ""
    
    var filteredLogs: [LogEntry] {
        appState.logs.filter { entry in
            let matchesLevel = filterLevel == nil || entry.level == filterLevel
            let matchesSearch = searchText.isEmpty || entry.message.localizedCaseInsensitiveContains(searchText)
            return matchesLevel && matchesSearch
        }
    }
    
    var body: some View {
        VStack(spacing: 0) {
            // Filters
            HStack {
                TextField("Search logs...", text: $searchText)
                    .textFieldStyle(.roundedBorder)
                
                Picker("Level", selection: $filterLevel) {
                    Text("All").tag(nil as LogLevel?)
                    ForEach([LogLevel.debug, .info, .warning, .error], id: \.self) { level in
                        Text(level.rawValue).tag(level as LogLevel?)
                    }
                }
                .frame(width: 100)
                
                Button("Clear") {
                    appState.logs.removeAll()
                }
            }
            .padding()
            
            Divider()
            
            // Log list
            List(filteredLogs) { entry in
                HStack(alignment: .top, spacing: 8) {
                    Text(entry.level.rawValue)
                        .font(.caption2)
                        .fontWeight(.bold)
                        .foregroundColor(entry.level.color)
                        .frame(width: 50, alignment: .leading)
                    
                    VStack(alignment: .leading, spacing: 2) {
                        Text(entry.message)
                            .font(.caption)
                        Text(entry.timestamp, style: .time)
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
            }
            .listStyle(.plain)
        }
    }
}

// MARK: - Network Tab

struct NetworkTabView: View {
    @EnvironmentObject var appState: AppState
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
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
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(methodColor(request.method))
                                .foregroundColor(.white)
                                .cornerRadius(4)
                            
                            Text(request.url)
                                .font(.caption)
                                .lineLimit(1)
                            
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
                .listStyle(.plain)
            }
        }
        .padding()
    }
    
    private func methodColor(_ method: String) -> Color {
        switch method {
        case "GET": return .blue
        case "POST": return .green
        case "PUT": return .orange
        case "DELETE": return .red
        default: return .secondary
        }
    }
}

// MARK: - Tools Tab

struct ToolsTabView: View {
    @EnvironmentObject var appState: AppState
    @State private var testMessage = ""
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            GroupBox("Test Message") {
                VStack(alignment: .leading, spacing: 8) {
                    TextField("Enter test message", text: $testMessage)
                        .textFieldStyle(.roundedBorder)
                    
                    Button("Send Test Message") {
                        Task {
                            await appState.sendMessage(testMessage)
                        }
                    }
                    .disabled(testMessage.isEmpty || !appState.isGatewayConnected)
                }
            }
            
            GroupBox("Quick Actions") {
                VStack(alignment: .leading, spacing: 8) {
                    Button("Clear Conversation") {
                        appState.currentMessages.removeAll()
                    }
                    
                    Button("Clear All Logs") {
                        appState.logs.removeAll()
                    }
                    
                    Button("Reconnect Gateway") {
                        Task {
                            appState.disconnectGateway()
                            try? await Task.sleep(nanoseconds: 1_000_000_000)
                            try? await appState.connectToGateway(url: appState.gatewayURL, token: "")
                        }
                    }
                    .disabled(!appState.isGatewayConnected)
                    
                    Divider()
                    
                    Button("Export Logs") {
                        exportLogs()
                    }
                    
                    Button("Copy Debug Info") {
                        copyDebugInfo()
                    }
                }
            }
            
            GroupBox("Audio Test") {
                VStack(alignment: .leading, spacing: 8) {
                    Button("Test TTS") {
                        Task {
                            await AudioService.shared.speak("Hello, this is a test of the text to speech system.")
                        }
                    }
                    
                    Button("Test Speech Recognition") {
                        AudioService.shared.startListening { transcript in
                            appState.addLog(.info, "Recognized: \(transcript)")
                        }
                    }
                    
                    Button("Stop Audio") {
                        AudioService.shared.stopListening()
                        AudioService.shared.stopSpeaking()
                    }
                }
            }
        }
        .padding()
    }
    
    private func exportLogs() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.json]
        panel.nameFieldStringValue = "cursorbot-logs.json"
        
        if panel.runModal() == .OK, let url = panel.url {
            let encoder = JSONEncoder()
            encoder.outputFormatting = .prettyPrinted
            encoder.dateEncodingStrategy = .iso8601
            
            if let data = try? encoder.encode(appState.logs.map { ["timestamp": $0.timestamp.description, "level": $0.level.rawValue, "message": $0.message] }) {
                try? data.write(to: url)
            }
        }
    }
    
    private func copyDebugInfo() {
        let info = """
        CursorBot Debug Info
        ====================
        App Version: \(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "Unknown")
        Build: \(Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "Unknown")
        macOS: \(ProcessInfo.processInfo.operatingSystemVersionString)
        Gateway: \(appState.connectionStatus.description)
        URL: \(appState.gatewayURL)
        Messages: \(appState.currentMessages.count)
        Logs: \(appState.logs.count)
        """
        
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(info, forType: .string)
    }
}

// MARK: - Preview

#Preview {
    DebugPanelView()
        .environmentObject(AppState.shared)
        .frame(width: 350, height: 600)
}
