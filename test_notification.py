#!/usr/bin/env python3
"""
Test script for v0.4 notification system.
Run this to test if desktop notifications work on your system.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.notifications import (
    get_notification_manager,
    NotificationCategory,
    NotificationPriority,
)


async def test_notifications():
    """Test the notification system."""
    print("=" * 50)
    print("CursorBot v0.4 Notification Test")
    print("=" * 50)
    print()
    
    manager = get_notification_manager()
    user_id = "test_user"
    
    # Test 1: Basic notification
    print("[Test 1] Sending basic notification...")
    result = await manager.notify(
        user_id=user_id,
        title="CursorBot Test",
        message="This is a test notification from CursorBot v0.4!",
        category=NotificationCategory.SYSTEM_ALERT,
        priority=NotificationPriority.NORMAL,
        sound=True,
    )
    
    if result:
        print(f"  ✅ Notification sent! ID: {result.id}")
    else:
        print("  ⚠️ Notification was filtered (check settings)")
    
    await asyncio.sleep(2)
    
    # Test 2: Task complete notification
    print("\n[Test 2] Sending task complete notification...")
    result = await manager.notify_task_complete(
        user_id=user_id,
        task_name="Code Analysis",
        success=True,
        details="Analysis completed successfully with no issues found.",
    )
    
    if result:
        print(f"  ✅ Task notification sent! ID: {result.id}")
    else:
        print("  ⚠️ Notification was filtered")
    
    await asyncio.sleep(2)
    
    # Test 3: High priority notification
    print("\n[Test 3] Sending high priority notification...")
    result = await manager.notify(
        user_id=user_id,
        title="Approval Required",
        message="Action 'delete_files' requires your approval.",
        category=NotificationCategory.APPROVAL_REQUIRED,
        priority=NotificationPriority.HIGH,
        sound=True,
    )
    
    if result:
        print(f"  ✅ High priority notification sent! ID: {result.id}")
    else:
        print("  ⚠️ Notification was filtered")
    
    # Show status
    print("\n" + "=" * 50)
    print("Notification Status")
    print("=" * 50)
    print(manager.get_status_message(user_id))
    
    print("\n" + "=" * 50)
    print("Test Complete!")
    print("=" * 50)
    print("\nIf you saw desktop notifications, the system is working correctly.")
    print("If not, check your system notification settings.")


if __name__ == "__main__":
    asyncio.run(test_notifications())
