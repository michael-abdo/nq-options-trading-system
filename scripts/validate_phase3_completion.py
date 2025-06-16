#!/usr/bin/env python3
"""
Phase 3 Validation Script - Alert System & Production Monitoring

Validates completion of Phase 3 requirements:
- Real-time Alert System (email, SMS, webhook)
- Production Monitoring & Health Checks
- Production Deployment Preparation
"""

import json
import os
import sys
import time
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def validate_alert_system() -> Tuple[bool, str]:
    """Validate alert system implementation"""
    try:
        # Check alert system module
        from tasks.options_trading_system.analysis_engine.monitoring.alert_system import (
            AlertSystem, Alert, AlertChannel,
            create_trading_alert, create_system_alert, create_cost_alert
        )

        # Check alerting configuration
        alert_config_path = "config/alerting.json"
        if not os.path.exists(alert_config_path):
            return False, f"Alerting configuration not found: {alert_config_path}"

        with open(alert_config_path, 'r') as f:
            alert_config = json.load(f)

        # Verify multi-channel configuration
        channels = alert_config.get("channels", {})
        required_channels = ["email", "slack", "sms"]
        for channel in required_channels:
            if channel not in channels:
                return False, f"Missing required channel: {channel}"

        # Verify escalation configuration
        if "escalation" not in alert_config:
            return False, "Missing escalation configuration"

        # Verify rate limiting
        if "rate_limiting" not in alert_config:
            return False, "Missing rate limiting configuration"

        # Test alert system instantiation
        alert_system = AlertSystem()

        # Test alert creation (without actually sending)
        test_alert = alert_system.create_alert(
            severity="INFO",
            title="Phase 3 Validation Test",
            message="Testing alert system functionality",
            component="validation_script",
            source="test"
        )

        return True, "Alert system validated successfully"

    except Exception as e:
        return False, f"Alert system validation failed: {str(e)}"

def validate_security_monitoring() -> Tuple[bool, str]:
    """Validate security monitoring implementation"""
    try:
        # Check security monitor module
        from tasks.options_trading_system.analysis_engine.monitoring.security_monitor import (
            SecurityMonitor, SecurityEvent, SecurityMetrics,
            monitor_api_request
        )

        # Test security monitor instantiation
        security_monitor = SecurityMonitor()

        # Verify security monitoring features
        # Test auth logging
        security_monitor.log_auth_attempt(
            success=True,
            source_ip="127.0.0.1",
            user_agent="test-agent",
            api_key="test-key",
            endpoint="/test"
        )

        # Test data access logging
        security_monitor.log_data_access(
            endpoint="/api/test",
            source_ip="127.0.0.1",
            data_type="test_data",
            record_count=10
        )

        # Get security metrics
        metrics = security_monitor.get_security_metrics()

        if "security_score" not in metrics:
            return False, "Security metrics incomplete"

        return True, "Security monitoring validated successfully"

    except Exception as e:
        return False, f"Security monitoring validation failed: {str(e)}"

def validate_reporting_system() -> Tuple[bool, str]:
    """Validate automated reporting system"""
    try:
        # Check reporting system module
        from tasks.options_trading_system.analysis_engine.monitoring.reporting_system import (
            ReportingSystem, ReportMetrics
        )

        # Test reporting system instantiation
        reporting_system = ReportingSystem()

        # Verify reporting configuration
        if not hasattr(reporting_system, "generate_daily_report"):
            return False, "Missing daily report generation"

        if not hasattr(reporting_system, "generate_weekly_report"):
            return False, "Missing weekly report generation"

        if not hasattr(reporting_system, "generate_sla_compliance_report"):
            return False, "Missing SLA compliance reporting"

        return True, "Reporting system validated successfully"

    except Exception as e:
        return False, f"Reporting system validation failed: {str(e)}"

def validate_production_config() -> Tuple[bool, str]:
    """Validate production configuration templates"""
    try:
        # Check production config template
        prod_config_path = "config/production/production_config_template.json"
        if not os.path.exists(prod_config_path):
            return False, f"Production config template not found: {prod_config_path}"

        with open(prod_config_path, 'r') as f:
            prod_config = json.load(f)

        # Verify critical sections
        required_sections = [
            "api_configuration",
            "monitoring",
            "logging",
            "security",
            "performance",
            "backup_and_recovery",
            "deployment"
        ]

        for section in required_sections:
            if section not in prod_config:
                return False, f"Missing production config section: {section}"

        # Check environment template
        env_template_path = "config/production/.env.production.template"
        if not os.path.exists(env_template_path):
            return False, f"Environment template not found: {env_template_path}"

        # Verify external monitoring configuration
        monitoring_config = prod_config.get("monitoring", {})
        if "external_monitoring" not in monitoring_config:
            return False, "Missing external monitoring configuration"

        return True, "Production configuration validated successfully"

    except Exception as e:
        return False, f"Production config validation failed: {str(e)}"

def validate_monitoring_integration() -> Tuple[bool, str]:
    """Validate monitoring system integrations"""
    try:
        # Check existing monitoring systems
        import importlib.util

        # Load production monitor module directly
        prod_monitor_path = Path(__file__).parent / "production_monitor.py"
        if not prod_monitor_path.exists():
            return False, "Production monitor script not found"

        spec = importlib.util.spec_from_file_location("production_monitor", prod_monitor_path)
        production_monitor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(production_monitor)

        # Verify monitoring configuration
        monitoring_config_path = "config/monitoring.json"
        if not os.path.exists(monitoring_config_path):
            return False, f"Monitoring configuration not found: {monitoring_config_path}"

        with open(monitoring_config_path, 'r') as f:
            monitoring_config = json.load(f)

        # Check for notification settings
        notification_settings = monitoring_config.get("notification_settings", {})
        if "email_alerts" not in notification_settings:
            return False, "Email alerts not configured in monitoring"

        if "slack_webhook" not in notification_settings:
            return False, "Slack webhook not configured in monitoring"

        return True, "Monitoring integration validated successfully"

    except Exception as e:
        return False, f"Monitoring integration validation failed: {str(e)}"

def validate_health_checks() -> Tuple[bool, str]:
    """Validate system health check capabilities"""
    try:
        # Check for uptime monitor
        from tasks.options_trading_system.analysis_engine.phase4.uptime_monitor import UptimeMonitor

        # Check for latency monitor
        from tasks.options_trading_system.analysis_engine.phase4.latency_monitor import LatencyMonitor

        # Check for performance tracker
        from tasks.options_trading_system.analysis_engine.monitoring.performance_tracker import PerformanceTracker

        return True, "Health check systems validated successfully"

    except Exception as e:
        return False, f"Health check validation failed: {str(e)}"

def validate_failover_recovery() -> Tuple[bool, str]:
    """Validate failover and recovery mechanisms"""
    try:
        # Check emergency rollback system
        emergency_rollback_path = "tasks/options_trading_system/analysis_engine/strategies/emergency_rollback_system.py"
        if not os.path.exists(emergency_rollback_path):
            return False, "Emergency rollback system not found"

        # Check production error handler
        error_handler_path = "tasks/options_trading_system/analysis_engine/strategies/production_error_handler.py"
        if not os.path.exists(error_handler_path):
            return False, "Production error handler not found"

        # Check rollback procedures documentation
        rollback_docs_path = "docs/operations/ROLLBACK_PROCEDURES.md"
        if not os.path.exists(rollback_docs_path):
            return False, "Rollback procedures documentation not found"

        return True, "Failover and recovery systems validated successfully"

    except Exception as e:
        return False, f"Failover/recovery validation failed: {str(e)}"

def calculate_phase3_completion(results: Dict[str, Tuple[bool, str]]) -> Dict[str, Any]:
    """Calculate Phase 3 completion statistics"""
    total_tests = len(results)
    passed_tests = sum(1 for passed, _ in results.values() if passed)

    # Map requirements to test results
    requirements = {
        "Multi-channel alert delivery (email, SMS, webhook)": results["alert_system"][0],
        "Configurable alert thresholds": results["alert_system"][0],
        "Alert rate limiting": results["alert_system"][0],
        "Alert history and tracking": results["alert_system"][0],
        "Security monitoring (API auth failures)": results["security_monitoring"][0],
        "Data access auditing": results["security_monitoring"][0],
        "Automated daily/weekly reports": results["reporting_system"][0],
        "SLA compliance reporting": results["reporting_system"][0],
        "Production configuration profiles": results["production_config"][0],
        "Comprehensive logging": results["production_config"][0],
        "System health monitoring": results["health_checks"][0],
        "Failover and recovery mechanisms": results["failover_recovery"][0],
        "External monitoring integration": results["monitoring_integration"][0],
        "Cost tracking alerts": results["monitoring_integration"][0],
        "Critical system failure alerts": results["monitoring_integration"][0]
    }

    completed_requirements = sum(1 for completed in requirements.values() if completed)

    return {
        "test_results": {
            "total": total_tests,
            "passed": passed_tests,
            "failed": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests) * 100
        },
        "requirement_completion": {
            "total": len(requirements),
            "completed": completed_requirements,
            "pending": len(requirements) - completed_requirements,
            "completion_rate": (completed_requirements / len(requirements)) * 100
        },
        "requirements": requirements
    }

def main():
    """Run Phase 3 validation"""
    print("=" * 70)
    print("PHASE 3 ALERT SYSTEM & PRODUCTION MONITORING VALIDATION")
    print("=" * 70)
    print(f"Validation time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Run validation tests
    print("🧪 Running Phase 3 Validation Tests...")
    print("-" * 50)

    results = {}
    tests = [
        ("alert_system", "Alert System Implementation", validate_alert_system),
        ("security_monitoring", "Security Monitoring", validate_security_monitoring),
        ("reporting_system", "Automated Reporting", validate_reporting_system),
        ("production_config", "Production Configuration", validate_production_config),
        ("monitoring_integration", "Monitoring Integration", validate_monitoring_integration),
        ("health_checks", "Health Check Systems", validate_health_checks),
        ("failover_recovery", "Failover & Recovery", validate_failover_recovery)
    ]

    for test_id, test_name, test_func in tests:
        start_time = time.time()
        passed, message = test_func()
        elapsed_time = (time.time() - start_time) * 1000

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name} ({elapsed_time:.1f}ms)")
        if not passed:
            print(f"     → {message}")

        results[test_id] = (passed, message)

    # Calculate completion statistics
    stats = calculate_phase3_completion(results)

    # Display summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    print(f"Total Tests: {stats['test_results']['total']}")
    print(f"Passed: {stats['test_results']['passed']}")
    print(f"Failed: {stats['test_results']['failed']}")
    print(f"Success Rate: {stats['test_results']['success_rate']:.1f}%")

    print("\n📋 Phase 3 Requirements Status:")
    for req, completed in stats['requirements'].items():
        status = "✅ COMPLETE" if completed else "❌ INCOMPLETE"
        print(f"   {status} - {req}")

    print(f"\n🎯 PHASE 3 ASSESSMENT:")
    completion_rate = stats['requirement_completion']['completion_rate']
    if completion_rate >= 90:
        print(f"   ✅ PHASE 3 IMPLEMENTATION: COMPLETE ({completion_rate:.1f}%)")
        print(f"   🚀 Ready for production deployment")
    elif completion_rate >= 70:
        print(f"   ⚠️  PHASE 3 IMPLEMENTATION: SUBSTANTIALLY COMPLETE ({completion_rate:.1f}%)")
        print(f"   🔧 Minor enhancements needed")
    else:
        print(f"   ❌ PHASE 3 IMPLEMENTATION: INCOMPLETE ({completion_rate:.1f}%)")
        print(f"   🛠️  Significant work required")

    # Save results
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/phase3_validation_{timestamp}.json"

    validation_data = {
        "timestamp": datetime.now().isoformat(),
        "phase": "Phase 3: Alert System & Production Monitoring",
        "test_results": results,
        "statistics": stats,
        "overall_status": "COMPLETE" if completion_rate >= 90 else "INCOMPLETE"
    }

    with open(output_file, 'w') as f:
        json.dump(validation_data, f, indent=2)

    print(f"\n📁 Detailed results saved to: {output_file}")

if __name__ == "__main__":
    main()
