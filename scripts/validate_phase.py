#!/usr/bin/env python3
"""
Phase Validation Script
Validates that a specific phase implementation meets all requirements
"""

import os
import sys
import json
import argparse
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class PhaseValidator:
    """Validates phase implementation against requirements"""

    def __init__(self, phase_number: int):
        self.phase_number = phase_number
        self.base_path = Path(__file__).parent.parent
        self.analysis_engine_path = self.base_path / "tasks/options_trading_system/analysis_engine"
        self.validation_results = {
            "phase": phase_number,
            "timestamp": get_eastern_time().isoformat(),
            "checks": {},
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }

    def validate(self) -> bool:
        """Run all validations for the phase"""
        print(f"\n{'='*60}")
        print(f"PHASE {self.phase_number} VALIDATION")
        print(f"{'='*60}\n")

        # Run phase-specific validations
        if self.phase_number == 1:
            self.validate_phase1()
        elif self.phase_number == 2:
            self.validate_phase2()
        elif self.phase_number == 3:
            self.validate_phase3()
        elif self.phase_number == 4:
            self.validate_phase4()
        else:
            print(f"⚠️  Phase {self.phase_number} validation not implemented")
            return False

        # Summary
        self.print_summary()

        # Save results
        self.save_results()

        return self.validation_results["failed"] == 0

    def validate_phase1(self):
        """Validate Phase 1: Enhanced Databento Client"""
        print("Validating Phase 1: Enhanced Databento Client\n")

        # Check required files
        self.check_file_exists(
            "data_ingestion/databento_api/solution.py",
            "Databento API implementation"
        )

        # Check MBO streaming capability
        self.check_module_imports(
            "data_ingestion.databento_api.solution",
            ["DatabentoPipeline", "create_databento_pipeline"],
            "MBO streaming components"
        )

        # Check caching implementation
        self.check_file_exists(
            "outputs/databento_cache",
            "Databento cache directory",
            is_dir=True
        )

        # Check test files
        self.check_file_exists(
            "data_ingestion/databento_api/test_validation.py",
            "Databento validation tests"
        )

        # Check evidence
        self.check_file_exists(
            "data_ingestion/databento_api/evidence.json",
            "Performance evidence"
        )

    def validate_phase2(self):
        """Validate Phase 2: IFD v3.0 Analysis Engine"""
        print("Validating Phase 2: IFD v3.0 Analysis Engine\n")

        # Check required files
        self.check_file_exists(
            "institutional_flow_v3/solution.py",
            "IFD v3.0 implementation"
        )

        # Check analysis components
        self.check_module_imports(
            "institutional_flow_v3.solution",
            ["create_institutional_flow_detector_v3"],
            "IFD v3.0 detector"
        )

        # Check baseline system
        self.check_file_exists(
            "outputs/ifd_v3_baselines.db",
            "Historical baseline database"
        )

        # Check test files
        self.check_file_exists(
            "institutional_flow_v3/test_validation.py",
            "IFD v3.0 validation tests"
        )

        # Check evidence
        self.check_file_exists(
            "institutional_flow_v3/evidence.json",
            "Algorithm performance evidence"
        )

    def validate_phase3(self):
        """Validate Phase 3: Integration and Testing"""
        print("Validating Phase 3: Integration and Testing\n")

        # Check integration files
        self.check_file_exists(
            "integration.py",
            "Main integration module"
        )

        self.check_file_exists(
            "config_manager.py",
            "Configuration management"
        )

        # Check integration components
        self.check_module_imports(
            "integration",
            ["AnalysisEngine"],
            "Analysis engine integration"
        )

        self.check_module_imports(
            "config_manager",
            ["ConfigManager", "AlgorithmVersion", "TestingMode"],
            "Configuration components"
        )

        # Check A/B testing capability
        self.check_file_exists(
            "strategies/ab_testing_coordinator.py",
            "A/B testing framework"
        )

        # Check configuration profiles
        self.check_file_exists(
            "config/profiles",
            "Configuration profiles directory",
            is_dir=True
        )

    def validate_phase4(self):
        """Validate Phase 4: Production Deployment"""
        print("Validating Phase 4: Production Deployment\n")

        # Check all Phase 4 components
        phase4_components = [
            ("phase4/success_metrics_tracker.py", "Success metrics tracking"),
            ("phase4/websocket_backfill_manager.py", "WebSocket backfill manager"),
            ("phase4/monthly_budget_dashboard.py", "Budget monitoring dashboard"),
            ("phase4/adaptive_threshold_manager.py", "Adaptive threshold optimization"),
            ("phase4/staged_rollout_framework.py", "Staged rollout framework"),
            ("phase4/historical_download_cost_tracker.py", "Cost tracking"),
            ("phase4/latency_monitor.py", "Latency monitoring"),
            ("phase4/uptime_monitor.py", "Uptime monitoring"),
            ("phase4/adaptive_integration.py", "Adaptive integration")
        ]

        for file_path, description in phase4_components:
            self.check_file_exists(file_path, description)

        # Check monitoring outputs
        self.check_file_exists(
            "outputs/performance_tracking",
            "Performance tracking directory",
            is_dir=True
        )

        # Check deployment documentation
        deployment_docs = [
            ("../../../DEPLOYMENT_GUIDE.md", "Deployment guide"),
            ("docs/PHASE4_COMPLETION_SUMMARY.md", "Phase 4 completion summary"),
            ("docs/ROLLBACK_PROCEDURES.md", "Rollback procedures")
        ]

        for doc_path, description in deployment_docs:
            self.check_file_exists(doc_path, description)

    def check_file_exists(self, path: str, description: str, is_dir: bool = False) -> bool:
        """Check if a required file or directory exists"""
        full_path = self.analysis_engine_path / path
        exists = full_path.is_dir() if is_dir else full_path.exists()

        check_name = f"File: {path}"
        if exists:
            self.validation_results["checks"][check_name] = "PASSED"
            self.validation_results["passed"] += 1
            print(f"✅ {description}")
            return True
        else:
            self.validation_results["checks"][check_name] = "FAILED"
            self.validation_results["failed"] += 1
            print(f"❌ {description} - NOT FOUND")
            return False

    def check_module_imports(self, module_name: str, required_items: List[str], description: str) -> bool:
        """Check if a module can be imported and has required items"""
        check_name = f"Module: {module_name}"

        # Change to the analysis engine directory for imports
        original_cwd = os.getcwd()
        os.chdir(self.analysis_engine_path)

        try:
            # Add current directory to Python path
            if str(self.analysis_engine_path) not in sys.path:
                sys.path.insert(0, str(self.analysis_engine_path))

            module = __import__(module_name, fromlist=required_items)

            missing_items = []
            for item in required_items:
                if not hasattr(module, item):
                    missing_items.append(item)

            if missing_items:
                self.validation_results["checks"][check_name] = "PARTIAL"
                self.validation_results["warnings"] += 1
                print(f"⚠️  {description} - Missing: {missing_items}")
                return False
            else:
                self.validation_results["checks"][check_name] = "PASSED"
                self.validation_results["passed"] += 1
                print(f"✅ {description}")
                return True

        except ImportError as e:
            self.validation_results["checks"][check_name] = "FAILED"
            self.validation_results["failed"] += 1
            print(f"❌ {description} - Import error: {str(e)}")
            return False
        finally:
            os.chdir(original_cwd)

    def check_test_results(self, test_file: str, description: str) -> bool:
        """Check if tests pass for a given test file"""
        check_name = f"Tests: {test_file}"

        # For now, just check if test file exists
        # In a real implementation, we would run the tests
        return self.check_file_exists(test_file, f"{description} tests")

    def print_summary(self):
        """Print validation summary"""
        total = self.validation_results["passed"] + self.validation_results["failed"] + self.validation_results["warnings"]

        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total Checks: {total}")
        print(f"✅ Passed: {self.validation_results['passed']}")
        print(f"❌ Failed: {self.validation_results['failed']}")
        print(f"⚠️  Warnings: {self.validation_results['warnings']}")

        if self.validation_results["failed"] == 0:
            print(f"\n🎉 Phase {self.phase_number} validation PASSED!")
        else:
            print(f"\n❌ Phase {self.phase_number} validation FAILED!")

    def save_results(self):
        """Save validation results to file"""
        output_dir = self.base_path / "outputs" / "validation"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"phase{self.phase_number}_validation_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2)

        print(f"\nResults saved to: {output_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Validate phase implementation")
    parser.add_argument("--phase", type=int, required=True, choices=[1, 2, 3, 4, 5, 6],
                       help="Phase number to validate")
    parser.add_argument("--strict", action="store_true",
                       help="Fail on warnings")

    args = parser.parse_args()

    validator = PhaseValidator(args.phase)
    success = validator.validate()

    if args.strict and validator.validation_results["warnings"] > 0:
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
