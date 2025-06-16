# Configuration Guide for Deployment Scenarios

## Overview
The IFD v3.0 trading system supports multiple deployment scenarios with environment-specific configurations. This guide provides comprehensive configuration options for development, staging, and production environments.

## Configuration Structure

### Configuration Hierarchy
```
config/
├── profiles/                    # Algorithm-specific profiles
│   ├── ifd_v3_production.json  # Production IFD configuration
│   ├── ifd_v3_development.json # Development IFD configuration
│   └── ifd_v3_conservative.json # Conservative trading profile
├── databento_only.json         # Databento-exclusive data source
├── barchart_only.json          # Barchart-exclusive data source
├── all_sources.json            # All data sources enabled
├── shadow_trading.json         # Shadow trading validation
├── testing.json                # Test environment configuration
└── alerting.json               # Alert system configuration
```

### Environment Variables (.env)
```bash
# Data Sources
DATABENTO_API_KEY=db-your-key-here
POLYGON_API_KEY=your-polygon-key
TRADOVATE_CID=your-cid
TRADOVATE_SECRET=your-secret

# Environment
ENVIRONMENT=production          # development|staging|production
LOG_LEVEL=INFO                 # DEBUG|INFO|WARNING|ERROR
ENABLE_METRICS=true            # true|false

# Performance
MAX_WORKERS=4                  # Number of processing threads
BUFFER_SIZE=10000             # Event buffer capacity
WEBSOCKET_TIMEOUT=30          # WebSocket timeout in seconds

# Security
ENABLE_SSL=true               # Enable SSL/TLS
API_RATE_LIMIT=1000          # Requests per minute
ALLOWED_IPS=127.0.0.1        # Comma-separated allowed IPs

# Monitoring
ENABLE_ALERTS=true           # Enable alert system
ALERT_EMAIL=admin@company.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

## Deployment Scenarios

### 1. Development Environment

#### Configuration: `config/development.json`
```json
{
  "environment": "development",
  "data_sources": {
    "databento": {
      "enabled": true,
      "mode": "simulated",
      "symbols": ["NQM5"],
      "rate_limit": 100
    },
    "barchart": {
      "enabled": true,
      "cache_ttl": 300,
      "fallback_enabled": true
    }
  },
  "processing": {
    "max_workers": 2,
    "buffer_size": 1000,
    "batch_size": 100,
    "enable_profiling": true
  },
  "ifd_v3": {
    "confidence_threshold": 0.60,
    "pressure_baseline_days": 5,
    "enable_debug_logging": true,
    "simulation_mode": true
  },
  "websocket": {
    "enabled": true,
    "port": 8765,
    "max_clients": 5,
    "heartbeat_interval": 30
  },
  "alerts": {
    "enabled": true,
    "channels": ["console", "file"],
    "thresholds": {
      "cpu_usage": 80,
      "memory_usage": 70,
      "error_rate": 0.10
    }
  },
  "logging": {
    "level": "DEBUG",
    "file_logging": true,
    "console_logging": true,
    "max_file_size": "10MB"
  }
}
```

#### Setup Commands
```bash
# Development environment setup
cp .env.example .env.development
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG

# Start development services
python3 scripts/run_pipeline.py --config config/development.json
python3 scripts/nq_realtime_ifd_dashboard.py --debug
```

### 2. Staging Environment

#### Configuration: `config/staging.json`
```json
{
  "environment": "staging",
  "data_sources": {
    "databento": {
      "enabled": true,
      "mode": "live",
      "symbols": ["NQM5", "ESM5"],
      "rate_limit": 500,
      "backup_enabled": true
    },
    "barchart": {
      "enabled": true,
      "cache_ttl": 300,
      "fallback_enabled": true
    }
  },
  "processing": {
    "max_workers": 4,
    "buffer_size": 5000,
    "batch_size": 500,
    "enable_profiling": false
  },
  "ifd_v3": {
    "confidence_threshold": 0.70,
    "pressure_baseline_days": 20,
    "enable_debug_logging": false,
    "simulation_mode": false,
    "conservative_mode": true
  },
  "websocket": {
    "enabled": true,
    "port": 8765,
    "max_clients": 20,
    "heartbeat_interval": 30,
    "ssl_enabled": true
  },
  "alerts": {
    "enabled": true,
    "channels": ["email", "slack", "file"],
    "rate_limiting": {
      "max_per_hour": 50,
      "burst_limit": 10
    },
    "thresholds": {
      "cpu_usage": 70,
      "memory_usage": 80,
      "error_rate": 0.05,
      "latency_p99": 100
    }
  },
  "monitoring": {
    "enabled": true,
    "metrics_retention_days": 7,
    "performance_tracking": true,
    "sla_monitoring": true
  },
  "logging": {
    "level": "INFO",
    "file_logging": true,
    "console_logging": false,
    "max_file_size": "50MB",
    "retention_days": 7
  }
}
```

#### Setup Commands
```bash
# Staging environment setup
cp .env.example .env.staging
export ENVIRONMENT=staging
export ENABLE_SSL=true

# Start staging services
python3 scripts/production_monitor.py --config config/staging.json
python3 scripts/run_pipeline.py --config config/staging.json --validate
```

### 3. Production Environment

#### Configuration: `config/production.json`
```json
{
  "environment": "production",
  "data_sources": {
    "databento": {
      "enabled": true,
      "mode": "live",
      "symbols": ["NQM5", "ESM5", "YMM5", "RTM5"],
      "rate_limit": 1000,
      "backup_enabled": true,
      "redundancy": true
    },
    "barchart": {
      "enabled": false,
      "fallback_only": true
    }
  },
  "processing": {
    "max_workers": 8,
    "buffer_size": 10000,
    "batch_size": 1000,
    "enable_profiling": false,
    "priority_queue": true
  },
  "ifd_v3": {
    "confidence_threshold": 0.75,
    "pressure_baseline_days": 20,
    "enable_debug_logging": false,
    "simulation_mode": false,
    "conservative_mode": false,
    "performance_optimized": true
  },
  "websocket": {
    "enabled": true,
    "port": 8765,
    "max_clients": 100,
    "heartbeat_interval": 15,
    "ssl_enabled": true,
    "compression": true
  },
  "alerts": {
    "enabled": true,
    "channels": ["email", "slack", "sms", "webhook"],
    "escalation": {
      "enabled": true,
      "levels": 3,
      "timeout_minutes": [5, 15, 30]
    },
    "rate_limiting": {
      "max_per_hour": 100,
      "burst_limit": 20
    },
    "thresholds": {
      "cpu_usage": 80,
      "memory_usage": 85,
      "error_rate": 0.01,
      "latency_p99": 50,
      "signal_accuracy": 0.70
    }
  },
  "monitoring": {
    "enabled": true,
    "metrics_retention_days": 30,
    "performance_tracking": true,
    "sla_monitoring": true,
    "external_monitoring": true
  },
  "security": {
    "ssl_required": true,
    "rate_limiting": true,
    "ip_whitelist": true,
    "api_key_rotation": true
  },
  "backup": {
    "enabled": true,
    "s3_bucket": "ifd-system-backups",
    "retention_days": 90,
    "encryption": true
  },
  "logging": {
    "level": "INFO",
    "file_logging": true,
    "console_logging": false,
    "max_file_size": "100MB",
    "retention_days": 30,
    "centralized_logging": true
  }
}
```

#### Setup Commands
```bash
# Production environment setup
cp .env.example .env.production
export ENVIRONMENT=production
export ENABLE_SSL=true
export ENABLE_METRICS=true

# Start production services with monitoring
python3 scripts/production_monitor.py --config config/production.json --daemon
python3 scripts/run_pipeline.py --config config/production.json --production
python3 scripts/monitoring_dashboard.py --port 8080
```

## Specialized Configurations

### 4. Shadow Trading Configuration

#### Configuration: `config/shadow_trading.json`
```json
{
  "environment": "shadow_trading",
  "data_sources": {
    "databento": {
      "enabled": true,
      "mode": "live",
      "symbols": ["NQM5"],
      "validation_mode": true
    }
  },
  "processing": {
    "max_workers": 4,
    "buffer_size": 5000,
    "parallel_validation": true
  },
  "ifd_v3": {
    "confidence_threshold": 0.70,
    "validation_enabled": true,
    "comparison_baseline": "ifd_v1",
    "signal_logging": true
  },
  "shadow_trading": {
    "enabled": true,
    "paper_trading": true,
    "position_tracking": true,
    "performance_analysis": true,
    "risk_limits": {
      "max_position_size": 10,
      "daily_loss_limit": 1000,
      "max_trades_per_day": 20
    }
  },
  "validation": {
    "signal_comparison": true,
    "performance_tracking": true,
    "accuracy_measurement": true,
    "reporting_interval": "1h"
  }
}
```

### 5. High-Frequency Trading Configuration

#### Configuration: `config/hft_optimized.json`
```json
{
  "environment": "hft_production",
  "data_sources": {
    "databento": {
      "enabled": true,
      "mode": "live",
      "symbols": ["NQM5"],
      "ultra_low_latency": true,
      "dedicated_connection": true
    }
  },
  "processing": {
    "max_workers": 16,
    "buffer_size": 50000,
    "batch_size": 100,
    "cpu_affinity": true,
    "memory_pinning": true
  },
  "ifd_v3": {
    "confidence_threshold": 0.80,
    "ultra_fast_mode": true,
    "simplified_calculations": true,
    "cache_optimization": true
  },
  "performance": {
    "target_latency_ms": 10,
    "max_jitter_ms": 2,
    "gc_tuning": true,
    "numa_optimization": true
  }
}
```

## Configuration Management

### Dynamic Configuration Updates
```python
# Runtime configuration updates
from config_manager import ConfigManager

config = ConfigManager()

# Update alert thresholds
config.update("alerts.thresholds.cpu_usage", 85)

# Enable debug mode
config.update("ifd_v3.enable_debug_logging", True)

# Reload configuration
config.reload()
```

### Configuration Validation
```bash
# Validate configuration files
python3 scripts/validate_config.py --config config/production.json

# Test configuration connectivity
python3 scripts/test_config.py --config config/production.json --verify-all

# Configuration diff
python3 scripts/config_diff.py config/staging.json config/production.json
```

## Environment-Specific Features

### Development Features
- **Debug Logging**: Detailed processing logs
- **Profiling**: Performance analysis tools
- **Hot Reload**: Configuration changes without restart
- **Mock Data**: Simulated market conditions
- **Test Utilities**: Built-in testing framework

### Staging Features
- **Load Testing**: Capacity verification
- **Integration Testing**: External system validation
- **Performance Monitoring**: Latency and throughput tracking
- **Canary Deployment**: Gradual rollout testing
- **Rollback Capability**: Quick reversion to stable version

### Production Features
- **High Availability**: Redundant component deployment
- **Auto-scaling**: Dynamic resource allocation
- **Disaster Recovery**: Automated backup and restore
- **Security Hardening**: Enhanced protection measures
- **Compliance Logging**: Regulatory requirement adherence

## Monitoring Configuration

### Metrics Collection
```json
{
  "monitoring": {
    "metrics": {
      "system": ["cpu", "memory", "disk", "network"],
      "application": ["latency", "throughput", "errors", "signals"],
      "business": ["accuracy", "profitability", "risk_metrics"]
    },
    "collection_interval": 10,
    "retention_policy": {
      "raw_data": "7d",
      "aggregated_1m": "30d",
      "aggregated_1h": "90d",
      "aggregated_1d": "2y"
    }
  }
}
```

### Alert Configuration
```json
{
  "alerts": {
    "channels": {
      "email": {
        "enabled": true,
        "smtp_server": "smtp.company.com",
        "recipients": ["admin@company.com", "trading@company.com"]
      },
      "slack": {
        "enabled": true,
        "webhook_url": "${SLACK_WEBHOOK_URL}",
        "channel": "#trading-alerts"
      },
      "sms": {
        "enabled": true,
        "provider": "twilio",
        "numbers": ["+1234567890"]
      }
    },
    "rules": {
      "system_critical": {
        "conditions": ["cpu > 90", "memory > 95", "error_rate > 0.05"],
        "channels": ["email", "slack", "sms"],
        "escalation": true
      },
      "performance_degradation": {
        "conditions": ["latency_p99 > 100", "throughput < 500"],
        "channels": ["slack"],
        "escalation": false
      }
    }
  }
}
```

## Deployment Automation

### Docker Configuration
```dockerfile
# Production Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8765 8080

CMD ["python3", "scripts/run_pipeline.py", "--config", "config/production.json"]
```

### Kubernetes Deployment
```yaml
# production-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ifd-trading-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ifd-trading
  template:
    metadata:
      labels:
        app: ifd-trading
    spec:
      containers:
      - name: ifd-app
        image: ifd-trading:latest
        ports:
        - containerPort: 8765
        - containerPort: 8080
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABENTO_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: databento-key
```

This configuration guide provides comprehensive setup instructions for all deployment scenarios, ensuring optimal performance and reliability across different environments.
