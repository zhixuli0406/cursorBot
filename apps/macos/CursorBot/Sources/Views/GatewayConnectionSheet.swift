// GatewayConnectionSheet.swift
// Gateway connection configuration sheet

import SwiftUI

struct GatewayConnectionSheet: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) private var dismiss
    
    @State private var gatewayURL = ""
    @State private var token = ""
    @State private var savedGateways: [GatewayConfig] = []
    @State private var isConnecting = false
    @State private var errorMessage: String?
    @State private var showAddNew = false
    
    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Gateway Connection")
                    .font(.headline)
                Spacer()
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding()
            
            Divider()
            
            // Content
            ScrollView {
                VStack(spacing: 20) {
                    // Current Status
                    if appState.isGatewayConnected {
                        GroupBox {
                            HStack {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundColor(.green)
                                    .font(.title2)
                                
                                VStack(alignment: .leading) {
                                    Text("Connected")
                                        .font(.headline)
                                    Text(appState.gatewayURL)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                
                                Spacer()
                                
                                Button("Disconnect") {
                                    appState.disconnectGateway()
                                }
                                .buttonStyle(.bordered)
                                .tint(.red)
                            }
                        }
                    }
                    
                    // Saved Gateways
                    GroupBox("Saved Gateways") {
                        VStack(spacing: 8) {
                            if savedGateways.isEmpty {
                                Text("No saved gateways")
                                    .foregroundColor(.secondary)
                                    .padding()
                            } else {
                                ForEach(savedGateways, id: \.url) { gateway in
                                    GatewayRow(
                                        gateway: gateway,
                                        isConnected: appState.isGatewayConnected && appState.gatewayURL == gateway.url,
                                        onConnect: { connect(to: gateway) },
                                        onDelete: { deleteGateway(gateway) }
                                    )
                                }
                            }
                            
                            Button(action: { showAddNew = true }) {
                                Label("Add Gateway", systemImage: "plus")
                            }
                            .buttonStyle(.borderless)
                        }
                    }
                    
                    // Quick Connect
                    GroupBox("Quick Connect") {
                        VStack(spacing: 12) {
                            TextField("Gateway URL", text: $gatewayURL)
                                .textFieldStyle(.roundedBorder)
                            
                            SecureField("Token (optional)", text: $token)
                                .textFieldStyle(.roundedBorder)
                            
                            if let error = errorMessage {
                                Text(error)
                                    .font(.caption)
                                    .foregroundColor(.red)
                            }
                            
                            HStack {
                                Button("Connect") {
                                    connectToGateway()
                                }
                                .buttonStyle(.borderedProminent)
                                .disabled(gatewayURL.isEmpty || isConnecting)
                                
                                if isConnecting {
                                    ProgressView()
                                        .scaleEffect(0.8)
                                }
                            }
                        }
                    }
                    
                    // Help
                    GroupBox("Help") {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Gateway URL format:")
                                .font(.caption)
                                .fontWeight(.medium)
                            
                            Text("• http://localhost:8000")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            
                            Text("• https://your-server.com")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            
                            Divider()
                            
                            Text("The gateway connects to your CursorBot server to send and receive messages.")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .padding()
            }
        }
        .frame(width: 450, height: 550)
        .onAppear {
            loadSavedGateways()
            gatewayURL = appState.gatewayURL
        }
        .sheet(isPresented: $showAddNew) {
            AddGatewaySheet(onSave: { config in
                savedGateways.append(config)
                saveSavedGateways()
            })
        }
    }
    
    private func connectToGateway() {
        isConnecting = true
        errorMessage = nil
        
        Task {
            do {
                try await appState.connectToGateway(url: gatewayURL, token: token)
                dismiss()
            } catch {
                errorMessage = error.localizedDescription
            }
            isConnecting = false
        }
    }
    
    private func connect(to gateway: GatewayConfig) {
        gatewayURL = gateway.url
        token = gateway.token
        connectToGateway()
    }
    
    private func deleteGateway(_ gateway: GatewayConfig) {
        savedGateways.removeAll { $0.url == gateway.url }
        saveSavedGateways()
    }
    
    private func loadSavedGateways() {
        if let data = UserDefaults.standard.data(forKey: "savedGateways"),
           let gateways = try? JSONDecoder().decode([GatewayConfig].self, from: data) {
            savedGateways = gateways
        }
    }
    
    private func saveSavedGateways() {
        if let data = try? JSONEncoder().encode(savedGateways) {
            UserDefaults.standard.set(data, forKey: "savedGateways")
        }
    }
}

// MARK: - Gateway Row

struct GatewayRow: View {
    let gateway: GatewayConfig
    let isConnected: Bool
    let onConnect: () -> Void
    let onDelete: () -> Void
    
    var body: some View {
        HStack {
            VStack(alignment: .leading) {
                Text(gateway.name)
                    .fontWeight(.medium)
                Text(gateway.url)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            if isConnected {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(.green)
            } else {
                Button("Connect") {
                    onConnect()
                }
                .buttonStyle(.bordered)
            }
            
            Button(action: onDelete) {
                Image(systemName: "trash")
                    .foregroundColor(.red)
            }
            .buttonStyle(.plain)
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Add Gateway Sheet

struct AddGatewaySheet: View {
    @Environment(\.dismiss) private var dismiss
    let onSave: (GatewayConfig) -> Void
    
    @State private var name = ""
    @State private var url = ""
    @State private var token = ""
    @State private var isDefault = false
    
    var body: some View {
        VStack(spacing: 20) {
            Text("Add Gateway")
                .font(.headline)
            
            VStack(alignment: .leading, spacing: 12) {
                TextField("Name", text: $name)
                    .textFieldStyle(.roundedBorder)
                
                TextField("URL", text: $url)
                    .textFieldStyle(.roundedBorder)
                
                SecureField("Token (optional)", text: $token)
                    .textFieldStyle(.roundedBorder)
                
                Toggle("Set as default", isOn: $isDefault)
            }
            
            HStack {
                Button("Cancel") {
                    dismiss()
                }
                .buttonStyle(.bordered)
                
                Button("Save") {
                    let config = GatewayConfig(
                        url: url,
                        token: token,
                        name: name.isEmpty ? url : name,
                        isDefault: isDefault
                    )
                    onSave(config)
                    dismiss()
                }
                .buttonStyle(.borderedProminent)
                .disabled(url.isEmpty)
            }
        }
        .padding()
        .frame(width: 350)
    }
}

// MARK: - Preview

#Preview {
    GatewayConnectionSheet()
        .environmentObject(AppState.shared)
}
