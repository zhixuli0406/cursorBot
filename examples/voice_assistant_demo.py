#!/usr/bin/env python3
"""
CursorBot v1.1 Voice Assistant Demo

This script demonstrates the voice assistant capabilities:
- Voice wake detection
- Speech recognition
- Intent recognition
- Context-aware responses
- Command execution

Prerequisites:
1. Install dependencies:
   pip install vosk edge-tts numpy

2. Download Vosk model:
   Download from: https://alphacephei.com/vosk/models
   Extract to: models/vosk-model-small-cn (for Chinese)
   Or: models/vosk-model-small-en (for English)

3. Run this script:
   python examples/voice_assistant_demo.py

Usage:
- Say "hey cursor" or "小助手" to wake the assistant
- Then speak your command or question
- The assistant will respond with voice

Example commands:
- "調高音量" - Increase volume
- "打開 Cursor" - Open Cursor app
- "現在幾點" - What time is it
- "搜尋天氣" - Search weather
- "提醒我10分鐘後喝水" - Remind me to drink water in 10 minutes
- "Git 提交" - Git commit
"""

import os
import sys
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.voice_assistant import (
    VoiceAssistant, VoiceAssistantConfig, AssistantState,
    WakeEngine, STTEngine, TTSEngine,
)
from src.core.voice_llm import (
    VoiceLLM, VoiceLLMConfig, IntegratedVoiceAssistant,
)
from src.core.voice_context import get_context_engine
from src.core.voice_commands import get_command_executor
from src.core.voice_learning import get_learning_engine
from src.utils.logger import logger


async def main():
    """Main demo function."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           CursorBot v1.1 Voice Assistant Demo                 ║
╠═══════════════════════════════════════════════════════════════╣
║  Say "hey cursor" or "小助手" to wake the assistant          ║
║  Then speak your command or question                          ║
║  Press Ctrl+C to exit                                         ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    # Check for required models
    vosk_model_path = "models/vosk-model-small-cn"
    if not os.path.exists(vosk_model_path):
        print(f"""
⚠️  Vosk model not found at {vosk_model_path}

Please download a Vosk model:
1. Visit: https://alphacephei.com/vosk/models
2. Download: vosk-model-small-cn (Chinese) or vosk-model-small-en (English)
3. Extract to: models/vosk-model-small-cn

Or set VOICE_VOSK_MODEL_PATH in your .env file.
""")
        # Continue anyway - will fall back to other methods
    
    # Configure the assistant
    config = VoiceAssistantConfig(
        wake_enabled=True,
        wake_engine=WakeEngine.VOSK,
        wake_words=["hey cursor", "ok cursor", "小助手", "嘿 cursor"],
        wake_timeout=10.0,
        stt_engine=STTEngine.WHISPER_LOCAL,
        stt_language="zh",
        tts_engine=TTSEngine.EDGE,
        tts_voice="zh-TW-HsiaoChenNeural",
        vad_enabled=True,
        noise_reduction=True,
        sound_enabled=True,
        vosk_model_path=vosk_model_path,
    )
    
    llm_config = VoiceLLMConfig(
        assistant_name="小助手",
        language="zh-TW",
        max_response_length=200,
    )
    
    # Create integrated assistant
    assistant = IntegratedVoiceAssistant(config, llm_config)
    
    # Register event handlers
    def on_wake(event):
        print(f"\n🎤 Wake word detected: {event.wake_word}")
        print("   Listening for your command...")
    
    def on_response(response):
        print(f"\n📝 You said: {response.utterance.text}")
        if response.intent:
            print(f"🎯 Intent: {response.intent.category.value}")
        print(f"🤖 Response: {response.text}")
        if response.audio:
            print("🔊 (Playing audio response...)")
    
    assistant.on_wake(on_wake)
    assistant.on_response(on_response)
    
    # Start the assistant
    print("Starting voice assistant...")
    if await assistant.start():
        print("✅ Voice assistant started successfully!")
        print(f"   State: {assistant.state.value}")
        print(f"   Stats: {assistant.get_stats()}")
        print("\n🎧 Listening for wake word...\n")
    else:
        print("❌ Failed to start voice assistant")
        print("   Check that required dependencies are installed:")
        print("   pip install vosk edge-tts numpy")
        return
    
    # Simulate audio input loop (in real usage, this would be from microphone)
    try:
        # Demo mode - show context and suggestions
        context_engine = get_context_engine()
        context = await context_engine.get_current_context()
        
        print(f"\n📍 Context:")
        print(f"   Time: {context.time.time_of_day.value}")
        print(f"   Device: {context.device.type.value}")
        if context.activity.current_app:
            print(f"   Current app: {context.activity.current_app}")
        
        greeting = context_engine.get_greeting(context)
        print(f"\n👋 {greeting}")
        
        suggestions = context_engine.get_suggestions(context)
        if suggestions:
            print("\n💡 Suggestions:")
            for s in suggestions[:3]:
                print(f"   - {s}")
        
        # Show available commands
        executor = get_command_executor()
        print("\n📋 Available command categories:")
        for cmd in executor.get_available_commands():
            print(f"   - {cmd}")
        
        # Demo: Process sample commands (simulate)
        print("\n" + "="*60)
        print("Demo mode: Processing sample commands...")
        print("="*60)
        
        sample_commands = [
            "現在幾點",
            "打開 Cursor",
            "Git status",
            "提醒我下午開會",
        ]
        
        from src.core.voice_assistant import Utterance, IntentRecognizer
        recognizer = IntentRecognizer(config)
        
        for cmd in sample_commands:
            print(f"\n📢 Command: {cmd}")
            
            # Recognize intent
            intent = await recognizer.recognize(cmd)
            print(f"   Intent: {intent.category.value}")
            
            # Execute command
            result = await executor.execute(intent)
            print(f"   Result: {result.status.value}")
            if result.response_text:
                print(f"   Response: {result.response_text}")
        
        print("\n" + "="*60)
        print("Demo complete!")
        print("="*60)
        
        # Keep running until interrupted
        print("\n🎧 Voice assistant is ready. Press Ctrl+C to exit.\n")
        
        # In production, this would be an audio capture loop
        # For demo, we just wait
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down voice assistant...")
    finally:
        await assistant.stop()
        print("✅ Voice assistant stopped.")


# Text-based demo (no microphone required)
async def text_demo():
    """Text-based demo for testing without microphone."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║       CursorBot v1.1 Voice Assistant - Text Demo              ║
╠═══════════════════════════════════════════════════════════════╣
║  Type commands as if speaking to test the assistant           ║
║  Type 'quit' to exit                                          ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    from src.core.voice_assistant import Utterance, IntentRecognizer, VoiceAssistantConfig
    from src.core.voice_commands import get_command_executor
    from src.core.voice_context import get_context_engine
    from src.core.voice_learning import get_learning_engine
    
    config = VoiceAssistantConfig()
    recognizer = IntentRecognizer(config)
    executor = get_command_executor()
    context_engine = get_context_engine()
    learning_engine = get_learning_engine()
    
    # Get initial context
    context = await context_engine.get_current_context()
    print(f"\n👋 {context_engine.get_greeting(context)}")
    
    suggestions = context_engine.get_personalized_suggestions()
    if suggestions:
        print("\n💡 Based on your habits, you might want to:")
        for s in suggestions[:3]:
            print(f"   - {s}")
    
    print("\n📋 Available commands:")
    for cmd in executor.get_available_commands():
        print(f"   - {cmd}")
    
    print("\n" + "-"*60)
    
    while True:
        try:
            text = input("\n🎤 You: ").strip()
            if not text:
                continue
            if text.lower() in ['quit', 'exit', '退出']:
                break
            
            # Create utterance
            utterance = Utterance(text=text)
            
            # Recognize intent
            intent = await recognizer.recognize(text)
            print(f"   🎯 Intent: {intent.category.value}")
            
            # Execute command
            result = await executor.execute(intent)
            
            # Record interaction for learning
            await learning_engine.record_interaction(
                utterance=utterance,
                intent=intent,
                response=result.response_text,
                command_executed=result.status.value == "success",
                success=result.status.value != "failed"
            )
            
            if result.response_text:
                print(f"   🤖 {result.response_text}")
            else:
                # If no specific response, generate one
                print(f"   🤖 好的，我理解你說的是「{text}」")
            
        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n📊 Session statistics:")
    stats = learning_engine.get_statistics()
    print(f"   Total interactions: {stats['total_interactions']}")
    print(f"   Shortcuts: {stats['shortcuts_count']}")
    print(f"   Patterns learned: {stats['patterns_learned']}")
    
    print("\n👋 Goodbye!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CursorBot Voice Assistant Demo")
    parser.add_argument(
        "--text", "-t",
        action="store_true",
        help="Run text-based demo (no microphone required)"
    )
    args = parser.parse_args()
    
    if args.text:
        asyncio.run(text_demo())
    else:
        asyncio.run(main())
