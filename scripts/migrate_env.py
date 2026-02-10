#!/usr/bin/env python3
"""
Migrate .env from CursorBot to ClaudeBot

This script automatically migrates environment variables from the old CursorBot
naming convention to the new ClaudeBot naming convention.

Usage:
    python scripts/migrate_env.py [--env-file PATH]

Examples:
    python scripts/migrate_env.py
    python scripts/migrate_env.py --env-file .env.production
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime


def migrate_env_file(env_path: Path, dry_run: bool = False) -> bool:
    """
    Migrate environment variables from CURSOR_* to CLAUDE_*.

    Args:
        env_path: Path to the .env file
        dry_run: If True, show changes without modifying the file

    Returns:
        bool: True if migration was successful, False otherwise
    """
    if not env_path.exists():
        print(f"❌ Error: {env_path} not found")
        return False

    print(f"📂 Reading {env_path}")
    content = env_path.read_text()

    # Define environment variable replacements
    replacements = {
        'CURSOR_API_KEY': 'CLAUDE_API_KEY',
        'CURSOR_WORKSPACE_PATH': 'CLAUDE_WORKSPACE_PATH',
        'CURSOR_WORKING_DIR': 'CLAUDE_WORKING_DIR',
        'CURSOR_CLI_MODEL': 'CLAUDE_CLI_MODEL',
        'CURSOR_CLI_TIMEOUT': 'CLAUDE_CLI_TIMEOUT',
        'CURSOR_GITHUB_REPO': 'CLAUDE_GITHUB_REPO',
    }

    # Track changes
    changes_made = []
    new_content = content

    for old_var, new_var in replacements.items():
        if old_var in new_content:
            new_content = new_content.replace(old_var, new_var)
            changes_made.append(f"  • {old_var} → {new_var}")

    if not changes_made:
        print("✨ No environment variables to migrate (already up to date)")
        return True

    print("\n📝 Changes to be made:")
    for change in changes_made:
        print(change)

    if dry_run:
        print("\n🔍 Dry run mode - no changes written")
        print("\nNew content preview:")
        print("-" * 60)
        print(new_content)
        print("-" * 60)
        return True

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = env_path.with_suffix(f'.env.backup.{timestamp}')
    backup_path.write_text(content)
    print(f"\n📦 Backup saved to {backup_path}")

    # Write migrated content
    env_path.write_text(new_content)
    print(f"✅ Successfully migrated {env_path}")

    return True


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate environment variables from CursorBot to ClaudeBot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/migrate_env.py
  python scripts/migrate_env.py --env-file .env.production
  python scripts/migrate_env.py --dry-run
        """
    )
    parser.add_argument(
        '--env-file',
        type=Path,
        default=Path('.env'),
        help='Path to the .env file to migrate (default: .env)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show changes without modifying the file'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("CursorBot → ClaudeBot Environment Migration")
    print("=" * 60)
    print()

    success = migrate_env_file(args.env_file, dry_run=args.dry_run)

    if success:
        if not args.dry_run:
            print("\n🎉 Migration completed successfully!")
            print("\n⚠️  Next steps:")
            print("  1. Review the changes in", args.env_file)
            print("  2. Update CLAUDE_API_KEY with your Anthropic API key")
            print("  3. Verify all other values are correct")
            print("  4. Restart your application")
        sys.exit(0)
    else:
        print("\n❌ Migration failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
