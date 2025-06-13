#!/usr/bin/env python3
"""
Validate Eastern Time consistency across entire codebase
Ensures all timestamps are in Eastern Time for LLM communication
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class EasternTimeValidator:
    """Validates Eastern Time usage across codebase"""

    def __init__(self):
        self.issues = []
        self.files_checked = 0
        self.files_with_issues = 0

        # Patterns to check
        self.problematic_patterns = [
            # UTC usage that should be Eastern for display
            (r'\.strftime\([^)]*\).*UTC', 'UTC in strftime - should use Eastern for display'),
            (r'timezone\.utc.*strftime', 'UTC timezone with strftime - use Eastern'),
            (r'print.*UTC', 'Printing UTC time - should display Eastern'),
            (r'logger\.(info|warning|error|debug).*UTC', 'Logging UTC - should log Eastern'),

            # Naive datetime usage
            (r'datetime\.now\(\)\s*[^.]', 'datetime.now() without timezone - use get_eastern_time()'),
            (r'datetime\.utcnow\(\)', 'datetime.utcnow() - use get_utc_time() from timezone_utils'),

            # Direct pytz usage instead of utilities
            (r'pytz\.timezone\(["\']US/Eastern["\']', 'Direct pytz Eastern - use EASTERN_TZ from timezone_utils'),
            (r'pytz\.UTC(?!_TZ)', 'Direct pytz.UTC - use UTC_TZ from timezone_utils'),

            # Timestamp formatting without timezone
            (r'timestamp.*=.*datetime\.now\(\)\.', 'Timestamp without timezone - use get_eastern_time()'),
            (r'\.isoformat\(\).*timestamp', 'ISO format timestamp - ensure Eastern Time'),
        ]

        # Files/patterns to skip
        self.skip_patterns = [
            'venv/', '__pycache__/', '.git/', 'archive/',
            'timezone_utils.py',  # The utility itself
            'validate_eastern_time_consistency.py',  # This file
            'fix_all_timezone_references.py',  # The fix script
        ]

    def should_skip_file(self, file_path: str) -> bool:
        """Check if file should be skipped"""
        for pattern in self.skip_patterns:
            if pattern in file_path:
                return True
        return False

    def check_file(self, file_path: str) -> List[Tuple[int, str, str]]:
        """Check a single file for timezone issues"""
        if self.should_skip_file(file_path):
            return []

        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # Check if file imports timezone utils
            has_timezone_import = 'from utils.timezone_utils import' in content

            # Check each problematic pattern
            for pattern, description in self.problematic_patterns:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        # Special case: skip if it's importing timezone_utils
                        if 'from utils.timezone_utils import' in line:
                            continue

                        issues.append((i, line.strip(), description))

            # Check for files that use datetime but don't import timezone utils
            if ('datetime.now()' in content or 'datetime.utcnow()' in content) and not has_timezone_import:
                issues.append((0, '', 'File uses datetime but missing timezone_utils import'))

        except Exception as e:
            issues.append((0, '', f'Error reading file: {e}'))

        return issues

    def validate_directory(self, directory: str) -> Dict[str, List]:
        """Validate all Python files in directory"""
        all_issues = {}

        for root, dirs, files in os.walk(directory):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'archive']]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self.files_checked += 1

                    issues = self.check_file(file_path)
                    if issues:
                        self.files_with_issues += 1
                        all_issues[file_path] = issues
                        self.issues.extend([(file_path, *issue) for issue in issues])

        return all_issues

    def generate_report(self) -> str:
        """Generate validation report"""
        report = []
        report.append("🕐 EASTERN TIME CONSISTENCY VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Files checked: {self.files_checked}")
        report.append(f"Files with issues: {self.files_with_issues}")
        report.append(f"Total issues found: {len(self.issues)}")
        report.append("")

        if self.issues:
            report.append("❌ ISSUES FOUND:")
            report.append("-" * 60)

            # Group by file
            current_file = None
            for file_path, line_num, code, description in sorted(self.issues):
                if file_path != current_file:
                    report.append(f"\n📄 {file_path}")
                    current_file = file_path

                if line_num > 0:
                    report.append(f"  Line {line_num}: {description}")
                    if code:
                        report.append(f"    Code: {code[:80]}...")
                else:
                    report.append(f"  File-level: {description}")
        else:
            report.append("✅ NO ISSUES FOUND - All files use Eastern Time consistently!")

        return "\n".join(report)

    def check_critical_files(self) -> List[str]:
        """Check critical files that must use Eastern Time"""
        critical_files = [
            'scripts/run_pipeline.py',
            'scripts/run_shadow_trading.py',
            'scripts/production_monitor.py',
            'scripts/monitoring_dashboard.py',
            'scripts/nq_5m_chart.py',
            'scripts/nq_5m_dash_app.py',
        ]

        critical_issues = []

        for file in critical_files:
            if os.path.exists(file):
                with open(file, 'r') as f:
                    content = f.read()

                # Must import timezone utils
                if 'from utils.timezone_utils import' not in content:
                    critical_issues.append(f"{file}: Missing timezone_utils import")

                # Must use get_eastern_time
                if 'get_eastern_time()' not in content and 'datetime.now()' in content:
                    critical_issues.append(f"{file}: Uses datetime.now() instead of get_eastern_time()")

        return critical_issues


def main():
    """Main validation function"""
    print("🔍 Validating Eastern Time Consistency")
    print("=" * 60)
    print("Checking all Python files for timezone issues...\n")

    validator = EasternTimeValidator()

    # Check main directories
    dirs_to_check = ['scripts', 'tasks', 'tests']

    for directory in dirs_to_check:
        if os.path.exists(directory):
            print(f"Checking {directory}/...")
            validator.validate_directory(directory)

    # Check critical files
    print("\nChecking critical files...")
    critical_issues = validator.check_critical_files()

    # Generate report
    report = validator.generate_report()
    print("\n" + report)

    if critical_issues:
        print("\n🚨 CRITICAL FILE ISSUES:")
        for issue in critical_issues:
            print(f"  - {issue}")

    # Summary
    print("\n" + "=" * 60)
    if validator.files_with_issues == 0:
        print("✅ SUCCESS: All files use Eastern Time consistently!")
        print("🤖 LLM can reliably interpret all timestamps as Eastern Time")
        return 0
    else:
        print(f"❌ ISSUES FOUND: {validator.files_with_issues} files need attention")
        print("Run 'python3 scripts/fix_all_timezone_references.py' to fix automatically")
        return 1


if __name__ == "__main__":
    sys.exit(main())
