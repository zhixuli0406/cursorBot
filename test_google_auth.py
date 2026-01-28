#!/usr/bin/env python3
"""
Google OAuth Authentication Test Script

This script triggers the Google OAuth flow for Calendar and Gmail.
Run this on a computer with a browser to complete authentication.
After successful auth, token files will be created and the bot can use them.
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import logger


async def authenticate_calendar():
    """Authenticate Google Calendar."""
    print("\n" + "=" * 50)
    print("Google Calendar Authentication")
    print("=" * 50)
    
    try:
        from src.core.google_calendar import get_calendar_manager
        
        manager = get_calendar_manager()
        
        if not manager.is_available:
            print("Error: Google API not installed")
            print("Run: pip install google-api-python-client google-auth-oauthlib")
            return False
        
        print(f"Credentials file: {manager.credentials_file}")
        print(f"Token file: {manager.token_file}")
        
        if not os.path.exists(manager.credentials_file):
            print(f"\nError: Credentials file not found!")
            print(f"Please download OAuth2 credentials from Google Cloud Console")
            print(f"and save to: {manager.credentials_file}")
            return False
        
        print("\nStarting OAuth flow...")
        print("A browser window will open for authentication.")
        print("Please sign in with your Google account.\n")
        
        success = await manager.authenticate()
        
        if success:
            print("\n✅ Calendar authentication successful!")
            print(f"Token saved to: {manager.token_file}")
            
            # Test by listing calendars
            calendars = await manager.list_calendars()
            print(f"\nFound {len(calendars)} calendars:")
            for cal in calendars[:5]:
                print(f"  - {cal.name}")
            return True
        else:
            print("\n❌ Calendar authentication failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def authenticate_gmail():
    """Authenticate Gmail."""
    print("\n" + "=" * 50)
    print("Gmail Authentication")
    print("=" * 50)
    
    try:
        from src.core.gmail import get_gmail_manager
        
        manager = get_gmail_manager()
        
        if not manager.is_available:
            print("Error: Google API not installed")
            return False
        
        print(f"Credentials file: {manager.credentials_file}")
        print(f"Token file: {manager.token_file}")
        
        if not os.path.exists(manager.credentials_file):
            print(f"\nCredentials file not found, skipping Gmail auth")
            return False
        
        print("\nStarting OAuth flow...")
        print("A browser window will open for authentication.\n")
        
        success = await manager.authenticate()
        
        if success:
            print("\n✅ Gmail authentication successful!")
            print(f"Token saved to: {manager.token_file}")
            return True
        else:
            print("\n❌ Gmail authentication failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def main():
    print("=" * 50)
    print("CursorBot Google OAuth Authentication")
    print("=" * 50)
    print("\nThis script will authenticate your Google account")
    print("for Calendar and Gmail integration.\n")
    
    # Check credentials file
    creds_path = "data/google/credentials.json"
    if not os.path.exists(creds_path):
        print(f"❌ Error: {creds_path} not found!")
        print("\nPlease follow these steps:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create or select a project")
        print("3. Enable Google Calendar API and Gmail API")
        print("4. Go to APIs & Services > Credentials")
        print("5. Create OAuth 2.0 Client ID (Desktop app)")
        print("6. Download JSON and save as data/google/credentials.json")
        return
    
    # Authenticate Calendar
    cal_success = await authenticate_calendar()
    
    # Authenticate Gmail
    gmail_success = await authenticate_gmail()
    
    # Summary
    print("\n" + "=" * 50)
    print("Authentication Summary")
    print("=" * 50)
    print(f"Calendar: {'✅ Success' if cal_success else '❌ Failed'}")
    print(f"Gmail: {'✅ Success' if gmail_success else '❌ Failed'}")
    
    if cal_success or gmail_success:
        print("\n✅ Token files created! You can now use:")
        print("   /calendar - View and manage calendar")
        print("   /gmail - Read and send emails")
        print("\nThese will work on any device including mobile Telegram.")


if __name__ == "__main__":
    asyncio.run(main())
