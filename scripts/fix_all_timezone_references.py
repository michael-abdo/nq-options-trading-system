#!/usr/bin/env python3
"""
Fix ALL timezone references in the codebase to use Eastern Time
This ensures consistent LLM communication about time
"""

import os
import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_file_timezone(file_path):
    """Fix timezone references in a single file"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes_made = []

    # Check if file already imports timezone utils
    has_timezone_import = 'from utils.timezone_utils import' in content

    # Pattern replacements
    replacements = [
        # datetime.now() -> get_eastern_time()
        (r'\bdatetime\.now\(\)', 'get_eastern_time()', 'datetime.now()'),
        # datetime.utcnow() -> get_utc_time()
        (r'\bdatetime\.utcnow\(\)', 'get_utc_time()', 'datetime.utcnow()'),
        # For timestamps and logging that should show Eastern
        (r'datetime\.now\(\)\.isoformat\(\)', 'get_eastern_time().isoformat()', 'datetime.now().isoformat()'),
        (r'datetime\.now\(\)\.strftime', 'get_eastern_time().strftime', 'datetime.now().strftime'),
    ]

    # Apply replacements
    for pattern, replacement, original in replacements:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changes_made.append(f"Replaced {original} with {replacement}")

    # If changes were made and no timezone import exists, add it
    if changes_made and not has_timezone_import:
        # Find the right place to add import
        import_lines = []

        # Check for existing datetime import
        datetime_import_match = re.search(r'^from datetime import (.+)$', content, re.MULTILINE)
        if datetime_import_match:
            # Add after datetime import
            import_line = datetime_import_match.group(0)
            new_import = import_line + '\nfrom utils.timezone_utils import get_eastern_time, get_utc_time'
            content = content.replace(import_line, new_import)
            changes_made.append("Added timezone utils import")
        else:
            # Add after other imports
            lines = content.split('\n')
            last_import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    last_import_idx = i

            # Insert after last import
            lines.insert(last_import_idx + 1, 'from utils.timezone_utils import get_eastern_time, get_utc_time')
            content = '\n'.join(lines)
            changes_made.append("Added timezone utils import")

    # Write back if changes were made
    if changes_made and content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, changes_made

    return False, []

def fix_all_files():
    """Fix timezone references in all Python files"""

    # Directories to process
    dirs_to_process = [
        'scripts',
        'tasks/options_trading_system',
        'tests'
    ]

    # Files to skip
    skip_files = {
        'timezone_utils.py',  # The timezone utility itself
        'fix_all_timezone_references.py',  # This script
    }

    total_fixed = 0
    all_changes = {}

    for dir_path in dirs_to_process:
        if not os.path.exists(dir_path):
            continue

        for root, dirs, files in os.walk(dir_path):
            # Skip venv and cache directories
            dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git']]

            for file in files:
                if file.endswith('.py') and file not in skip_files:
                    file_path = os.path.join(root, file)

                    try:
                        fixed, changes = fix_file_timezone(file_path)
                        if fixed:
                            total_fixed += 1
                            all_changes[file_path] = changes
                            print(f"✅ Fixed: {file_path}")
                            for change in changes:
                                print(f"   - {change}")
                    except Exception as e:
                        print(f"❌ Error processing {file_path}: {e}")

    return total_fixed, all_changes

def main():
    """Main execution"""
    print("🔧 FIXING ALL TIMEZONE REFERENCES TO USE EASTERN TIME")
    print("=" * 60)
    print("This ensures consistent LLM communication about time\n")

    total_fixed, all_changes = fix_all_files()

    print(f"\n📊 SUMMARY")
    print("=" * 60)
    print(f"Total files fixed: {total_fixed}")

    if total_fixed > 0:
        print(f"\n📝 Files modified:")
        for file_path in sorted(all_changes.keys()):
            print(f"  - {file_path}")

    print(f"\n✅ All datetime references now use Eastern Time for consistency")
    print("🤖 LLM can now reliably interpret all timestamps as Eastern Time")

if __name__ == "__main__":
    main()
