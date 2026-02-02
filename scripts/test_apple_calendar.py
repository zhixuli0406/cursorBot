#!/usr/bin/env python3
"""
Test script for Apple Calendar integration.
Run this to diagnose AppleScript timeout issues.

Usage:
    python scripts/test_apple_calendar.py
"""

import subprocess
import time
import platform


def run_applescript(script: str, timeout: int = 5) -> tuple[bool, str, float]:
    """Run AppleScript and return (success, output, elapsed_time)."""
    start = time.time()
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.time() - start
        if result.returncode == 0:
            return True, result.stdout.strip(), elapsed
        else:
            return False, result.stderr.strip(), elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return False, f"TIMEOUT after {timeout}s", elapsed
    except Exception as e:
        elapsed = time.time() - start
        return False, str(e), elapsed


def main():
    print("=" * 60)
    print("Apple Calendar Diagnostic Tool")
    print("=" * 60)
    print()
    
    # Check platform
    if platform.system() != "Darwin":
        print("ERROR: This script only works on macOS")
        return
    
    print(f"Platform: {platform.system()} {platform.release()}")
    print()
    
    # Test 1: Simple osascript test
    print("Test 1: Basic osascript functionality")
    print("-" * 40)
    success, output, elapsed = run_applescript('return "Hello from AppleScript"', timeout=5)
    if success:
        print(f"  PASS ({elapsed:.2f}s): {output}")
    else:
        print(f"  FAIL ({elapsed:.2f}s): {output}")
        print("  AppleScript is not working. Check system permissions.")
        return
    print()
    
    # Test 2: Check if Calendar.app exists
    print("Test 2: Check Calendar.app existence")
    print("-" * 40)
    success, output, elapsed = run_applescript(
        'tell application "System Events" to return exists application process "Calendar"',
        timeout=5
    )
    calendar_running = output == "true"
    print(f"  Calendar.app running: {calendar_running} ({elapsed:.2f}s)")
    print()
    
    # Test 3: Simple Calendar access (this might trigger permission dialog)
    print("Test 3: Access Calendar.app (may trigger permission dialog)")
    print("-" * 40)
    print("  NOTE: If this hangs, check System Preferences > Security & Privacy > Automation")
    print("  Make sure Terminal (or Python) is allowed to control Calendar.app")
    print()
    
    success, output, elapsed = run_applescript(
        'tell application "Calendar" to return count of calendars',
        timeout=10
    )
    if success:
        print(f"  PASS ({elapsed:.2f}s): Found {output} calendars")
    else:
        print(f"  FAIL ({elapsed:.2f}s): {output}")
        if "timeout" in output.lower():
            print()
            print("  DIAGNOSIS: Calendar.app is not responding to AppleScript.")
            print("  Possible solutions:")
            print("    1. Open Calendar.app manually and ensure it's not frozen")
            print("    2. Check System Preferences > Security & Privacy > Privacy > Automation")
            print("    3. Try: tccutil reset AppleEvents")
            print("    4. Restart Calendar.app")
        return
    print()
    
    # Test 4: List calendar names
    print("Test 4: List calendar names")
    print("-" * 40)
    success, output, elapsed = run_applescript(
        'tell application "Calendar" to return name of calendars',
        timeout=10
    )
    if success:
        print(f"  PASS ({elapsed:.2f}s)")
        calendars = output.split(", ")
        for cal in calendars[:10]:
            print(f"    - {cal}")
        if len(calendars) > 10:
            print(f"    ... and {len(calendars) - 10} more")
    else:
        print(f"  FAIL ({elapsed:.2f}s): {output}")
    print()
    
    # Test 5: Query individual calendars
    print("Test 5: Query individual calendars (finding slow ones)")
    print("-" * 40)
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now().replace(hour=0, minute=0, second=0) + 
                __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Get calendar names first
    success, cal_list, _ = run_applescript(
        'tell application "Calendar" to return name of calendars',
        timeout=5
    )
    
    if not success:
        print("  FAIL: Could not get calendar list")
    else:
        calendars = cal_list.split(", ")
        print(f"  Testing {len(calendars)} calendars individually...")
        print()
        
        slow_calendars = []
        fast_calendars = []
        
        for cal_name in calendars[:15]:  # Test first 15 calendars
            script = f'''
            tell application "Calendar"
                set eventCount to 0
                set startDate to date "{today}"
                set endDate to date "{tomorrow}"
                
                try
                    set targetCal to calendar "{cal_name}"
                    set calEvents to (every event of targetCal whose start date >= startDate and start date < endDate)
                    set eventCount to count of calEvents
                end try
                
                return eventCount
            end tell
            '''
            
            success, output, elapsed = run_applescript(script, timeout=3)
            status = "OK" if success else "SLOW/FAIL"
            events = output if success else "?"
            
            if success and elapsed < 1.0:
                fast_calendars.append(cal_name)
                print(f"    [OK]   {cal_name}: {events} events ({elapsed:.2f}s)")
            elif success:
                slow_calendars.append(cal_name)
                print(f"    [SLOW] {cal_name}: {events} events ({elapsed:.2f}s)")
            else:
                slow_calendars.append(cal_name)
                print(f"    [FAIL] {cal_name}: timeout ({elapsed:.2f}s)")
        
        print()
        if slow_calendars:
            print(f"  Found {len(slow_calendars)} slow/problematic calendars:")
            for cal in slow_calendars[:5]:
                print(f"    - {cal}")
            print()
            print("  Recommendation: Add to .env to exclude slow calendars:")
            exclude_str = ",".join(slow_calendars[:5])
            print(f"    APPLE_CALENDAR_EXCLUDE={exclude_str}")
            print()
            print("  Or only include fast calendars:")
            include_str = ",".join(fast_calendars[:5])
            print(f"    APPLE_CALENDAR_INCLUDE={include_str}")
    print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    print("If tests passed but you still see timeouts in the bot,")
    print("consider these options:")
    print()
    print("1. Increase timeout: Add to .env:")
    print("   APPLE_CALENDAR_TIMEOUT=15")
    print()
    print("2. Disable Apple Calendar: Add to .env:")
    print("   APPLE_CALENDAR_ENABLED=false")
    print()
    print("3. Use Google Calendar instead (/calendar auth)")
    print()


if __name__ == "__main__":
    main()
