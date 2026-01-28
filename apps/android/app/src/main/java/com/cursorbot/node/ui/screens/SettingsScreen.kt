package com.cursorbot.node.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.cursorbot.node.model.ConnectionStatus
import com.cursorbot.node.viewmodel.MainViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(viewModel: MainViewModel) {
    val connectionStatus by viewModel.connectionStatus.collectAsState()
    val isConnected by viewModel.isConnected.collectAsState()
    val gatewayUrl by viewModel.gatewayUrl.collectAsState()
    val pairingCode by viewModel.pairingCode.collectAsState()
    val recordingState by viewModel.recordingState.collectAsState()
    
    var showConnectionDialog by remember { mutableStateOf(false) }
    var showPairingDialog by remember { mutableStateOf(false) }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
        ) {
            // Connection Section
            SettingsSection(title = "Connection") {
                SettingsItem(
                    icon = Icons.Default.Wifi,
                    title = "Gateway",
                    subtitle = if (isConnected) gatewayUrl else "Not connected",
                    onClick = { showConnectionDialog = true }
                )
                
                if (isConnected) {
                    SettingsItem(
                        icon = Icons.Default.QrCode,
                        title = "Device Pairing",
                        subtitle = "Generate pairing code",
                        onClick = { 
                            viewModel.requestPairingCode()
                            showPairingDialog = true 
                        }
                    )
                }
            }
            
            // Voice Section
            SettingsSection(title = "Voice") {
                val voiceWakeEnabled by viewModel.voiceWakeEnabled.collectAsState()
                val voiceWakePhrase by viewModel.voiceWakePhrase.collectAsState()
                
                SettingsSwitchItem(
                    icon = Icons.Default.Mic,
                    title = "Voice Wake",
                    subtitle = if (voiceWakeEnabled) "Listening for '$voiceWakePhrase'" else "Tap to enable",
                    checked = voiceWakeEnabled,
                    onCheckedChange = { viewModel.toggleVoiceWake() }
                )
                
                SettingsItem(
                    icon = Icons.Default.VolumeUp,
                    title = "Voice Settings",
                    subtitle = "Language, rate, sensitivity",
                    onClick = { /* Navigate to voice settings */ }
                )
            }
            
            // Screen Recording Section
            SettingsSection(title = "Screen Recording") {
                SettingsItem(
                    icon = Icons.Default.Videocam,
                    title = if (recordingState.isRecording) "Stop Recording" else "Start Recording",
                    subtitle = if (recordingState.isRecording) {
                        "Recording in progress..."
                    } else {
                        "Record screen for analysis"
                    },
                    onClick = {
                        if (recordingState.isRecording) {
                            viewModel.stopRecording()
                        } else {
                            viewModel.startRecording()
                        }
                    }
                )
            }
            
            // Device Info Section
            SettingsSection(title = "Device") {
                SettingsItem(
                    icon = Icons.Default.Smartphone,
                    title = "Device ID",
                    subtitle = viewModel.deviceId.take(8) + "...",
                    onClick = { }
                )
                
                SettingsItem(
                    icon = Icons.Default.Info,
                    title = "Version",
                    subtitle = "0.4.0",
                    onClick = { }
                )
            }
            
            // About Section
            SettingsSection(title = "About") {
                SettingsItem(
                    icon = Icons.Default.Code,
                    title = "GitHub",
                    subtitle = "View source code",
                    onClick = { /* Open GitHub */ }
                )
                
                SettingsItem(
                    icon = Icons.Default.Description,
                    title = "Documentation",
                    subtitle = "View docs",
                    onClick = { /* Open docs */ }
                )
            }
        }
    }
    
    // Connection Dialog
    if (showConnectionDialog) {
        ConnectionDialog(
            currentUrl = gatewayUrl,
            isConnected = isConnected,
            onConnect = { url, token ->
                viewModel.connectToGateway(url, token)
            },
            onDisconnect = { viewModel.disconnect() },
            onDismiss = { showConnectionDialog = false }
        )
    }
    
    // Pairing Dialog
    if (showPairingDialog) {
        PairingDialog(
            code = pairingCode,
            onDismiss = { showPairingDialog = false },
            onRegenerate = { viewModel.requestPairingCode() }
        )
    }
}

@Composable
private fun SettingsSection(
    title: String,
    content: @Composable ColumnScope.() -> Unit
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = title,
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
        )
        content()
        Spacer(modifier = Modifier.height(8.dp))
    }
}

@Composable
private fun SettingsItem(
    icon: ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit
) {
    Surface(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
            
            Spacer(modifier = Modifier.width(16.dp))
            
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.bodyLarge
                )
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            
            Icon(
                imageVector = Icons.Default.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun SettingsSwitchItem(
    icon: ImageVector,
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Surface(
        onClick = { onCheckedChange(!checked) },
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
            
            Spacer(modifier = Modifier.width(16.dp))
            
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.bodyLarge
                )
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            
            Switch(
                checked = checked,
                onCheckedChange = onCheckedChange
            )
        }
    }
}

@Composable
private fun ConnectionDialog(
    currentUrl: String,
    isConnected: Boolean,
    onConnect: (String, String) -> Unit,
    onDisconnect: () -> Unit,
    onDismiss: () -> Unit
) {
    var url by remember { mutableStateOf(currentUrl) }
    var token by remember { mutableStateOf("") }
    
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Gateway Connection") },
        text = {
            Column {
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    label = { Text("Gateway URL") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                
                Spacer(modifier = Modifier.height(8.dp))
                
                OutlinedTextField(
                    value = token,
                    onValueChange = { token = it },
                    label = { Text("Token (optional)") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
            }
        },
        confirmButton = {
            if (isConnected) {
                TextButton(onClick = {
                    onDisconnect()
                    onDismiss()
                }) {
                    Text("Disconnect", color = MaterialTheme.colorScheme.error)
                }
            } else {
                TextButton(
                    onClick = {
                        onConnect(url, token)
                        onDismiss()
                    },
                    enabled = url.isNotBlank()
                ) {
                    Text("Connect")
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}

@Composable
private fun PairingDialog(
    code: String?,
    onDismiss: () -> Unit,
    onRegenerate: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Device Pairing") },
        text = {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth()
            ) {
                if (code != null) {
                    Text(
                        text = code,
                        style = MaterialTheme.typography.headlineMedium
                    )
                    
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    Text(
                        text = "Enter this code on another device to pair",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    CircularProgressIndicator()
                    
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    Text("Generating code...")
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onRegenerate) {
                Text("Regenerate")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Close")
            }
        }
    )
}
