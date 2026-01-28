// HotkeyManager.swift
// Global hotkey registration and handling

import Foundation
import Carbon
import AppKit

class HotkeyManager {
    static let shared = HotkeyManager()
    
    private var eventHandler: EventHandlerRef?
    private var hotkeys: [UInt32: () -> Void] = [:]
    private var nextHotkeyId: UInt32 = 1
    
    private init() {}
    
    func registerHotkeys() {
        // Register default hotkeys
        registerHotkey(keyCode: kVK_Space, modifiers: [.command, .shift]) {
            Task { @MainActor in
                AppState.shared.toggleTalkMode()
            }
        }
        
        registerHotkey(keyCode: kVK_ANSI_N, modifiers: [.command, .shift]) {
            Task { @MainActor in
                AppState.shared.startNewConversation()
                NSApp.activate(ignoringOtherApps: true)
            }
        }
        
        registerHotkey(keyCode: kVK_ANSI_G, modifiers: [.command, .shift]) {
            Task { @MainActor in
                AppState.shared.showGatewaySheet = true
                NSApp.activate(ignoringOtherApps: true)
            }
        }
    }
    
    @discardableResult
    func registerHotkey(keyCode: Int, modifiers: NSEvent.ModifierFlags, action: @escaping () -> Void) -> UInt32 {
        let hotkeyId = nextHotkeyId
        nextHotkeyId += 1
        
        hotkeys[hotkeyId] = action
        
        var eventType = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        
        if eventHandler == nil {
            let handler: EventHandlerUPP = { (nextHandler, event, userData) -> OSStatus in
                var hotkeyId = EventHotKeyID()
                GetEventParameter(event, EventParamName(kEventParamDirectObject), EventParamType(typeEventHotKeyID), nil, MemoryLayout<EventHotKeyID>.size, nil, &hotkeyId)
                
                if let manager = userData?.assumingMemoryBound(to: HotkeyManager.self).pointee {
                    manager.handleHotkey(id: hotkeyId.id)
                }
                
                return noErr
            }
            
            var handlerRef: EventHandlerRef?
            InstallEventHandler(GetApplicationEventTarget(), handler, 1, &eventType, Unmanaged.passUnretained(self).toOpaque(), &handlerRef)
            eventHandler = handlerRef
        }
        
        let hotkeyIdStruct = EventHotKeyID(signature: OSType(0x4342_4F54), id: hotkeyId)  // "CBOT"
        var hotkeyRef: EventHotKeyRef?
        
        let carbonModifiers = convertToCarbonModifiers(modifiers)
        
        RegisterEventHotKey(UInt32(keyCode), carbonModifiers, hotkeyIdStruct, GetApplicationEventTarget(), 0, &hotkeyRef)
        
        return hotkeyId
    }
    
    func unregisterHotkey(id: UInt32) {
        hotkeys.removeValue(forKey: id)
    }
    
    private func handleHotkey(id: UInt32) {
        if let action = hotkeys[id] {
            action()
        }
    }
    
    private func convertToCarbonModifiers(_ modifiers: NSEvent.ModifierFlags) -> UInt32 {
        var carbonModifiers: UInt32 = 0
        
        if modifiers.contains(.command) {
            carbonModifiers |= UInt32(cmdKey)
        }
        if modifiers.contains(.option) {
            carbonModifiers |= UInt32(optionKey)
        }
        if modifiers.contains(.control) {
            carbonModifiers |= UInt32(controlKey)
        }
        if modifiers.contains(.shift) {
            carbonModifiers |= UInt32(shiftKey)
        }
        
        return carbonModifiers
    }
}

// MARK: - Update Checker

class UpdateChecker {
    static let shared = UpdateChecker()
    
    private let updateURL = "https://api.github.com/repos/cursorbot/cursorbot-macos/releases/latest"
    
    func checkForUpdates() {
        Task {
            do {
                guard let url = URL(string: updateURL) else { return }
                let (data, _) = try await URLSession.shared.data(from: url)
                
                if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let tagName = json["tag_name"] as? String {
                    let latestVersion = tagName.replacingOccurrences(of: "v", with: "")
                    let currentVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.0.0"
                    
                    if latestVersion > currentVersion {
                        await notifyUpdate(version: latestVersion)
                    }
                }
            } catch {
                print("Failed to check for updates: \(error)")
            }
        }
    }
    
    @MainActor
    private func notifyUpdate(version: String) {
        let alert = NSAlert()
        alert.messageText = "Update Available"
        alert.informativeText = "CursorBot \(version) is available. Would you like to download it?"
        alert.alertStyle = .informational
        alert.addButton(withTitle: "Download")
        alert.addButton(withTitle: "Later")
        
        if alert.runModal() == .alertFirstButtonReturn {
            if let url = URL(string: "https://github.com/cursorbot/cursorbot-macos/releases/latest") {
                NSWorkspace.shared.open(url)
            }
        }
    }
}
