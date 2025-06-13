# 5-Minute Chart Performance Tuning Guide

## Overview
This guide provides recommendations for optimizing the performance of the 5-minute NQ futures chart system for different use cases.

## Configuration Optimization

### Memory Usage

**Minimal Memory Configuration:**
```bash
python3 scripts/nq_5m_chart.py --config minimal --hours 2 --no-volume
```

**Settings to reduce memory:**
- Reduce `time_range_hours` (fewer bars in memory)
- Disable volume subplot with `--no-volume`
- Disable indicators: `--indicators`
- Increase `cache_duration_minutes` to reduce API calls

### Update Frequency

**High-Frequency Trading:**
```bash
python3 scripts/nq_5m_chart.py --config scalping --update 10
```

**Low-Frequency Analysis:**
```bash
python3 scripts/nq_5m_chart.py --config swing_trading --update 60
```

**Recommended update intervals by use case:**
- Scalping: 5-15 seconds
- Day trading: 15-30 seconds
- Swing analysis: 60-120 seconds
- Position monitoring: 300+ seconds

## Data Source Performance

### Databento API Optimization

**Cache Settings:**
- Enable caching: `"cache_enabled": true`
- Adjust cache duration based on trading style:
  - Scalping: 5-10 minutes
  - Day trading: 15-30 minutes
  - Swing trading: 30-60 minutes

**API Rate Limiting:**
- Databento allows up to 10 requests/second
- Recommended: 1 request every 10-30 seconds
- Monitor your API usage via Databento dashboard

### Network Performance

**Connection Optimization:**
- Use stable internet connection
- Consider co-location for ultra-low latency
- Monitor network latency to Databento servers

## System Resources

### CPU Usage

**Indicator Performance:**
- SMA: Fastest calculation
- EMA: Moderate CPU usage
- VWAP: Higher CPU usage (requires volume data)

**Chart Rendering:**
- Plotly is CPU-intensive for large datasets
- Limit data points: reduce `time_range_hours`
- Use minimal theme for faster rendering

### Memory Management

**Data Buffer Optimization:**
```json
{
  "chart": {
    "time_range_hours": 4,
    "update_interval": 30
  },
  "data": {
    "cache_enabled": true,
    "cache_duration_minutes": 15
  }
}
```

**Memory usage by time range:**
- 1 hour: ~50MB RAM
- 4 hours: ~200MB RAM
- 8 hours: ~400MB RAM
- 24 hours: ~1.2GB RAM

## Configuration Presets by Use Case

### Scalping (High Performance)
```bash
python3 scripts/nq_5m_chart.py --config scalping
```
- 2-hour time window
- 10-second updates
- EMA + VWAP indicators
- High chart resolution

### Day Trading (Balanced)
```bash
python3 scripts/nq_5m_chart.py --config default
```
- 4-hour time window
- 30-second updates
- SMA indicators
- Standard resolution

### Swing Analysis (Low Resource)
```bash
python3 scripts/nq_5m_chart.py --config swing_trading
```
- 8-hour time window
- 60-second updates
- Multiple timeframe SMAs
- PDF export optimized

### Monitoring (Minimal Resource)
```bash
python3 scripts/nq_5m_chart.py --config minimal
```
- 4-hour time window
- No indicators
- No volume subplot
- Minimal CPU/memory usage

## Browser Performance

### Chart Rendering

**Recommended browsers:**
1. Chrome/Chromium (best Plotly performance)
2. Firefox (good performance)
3. Safari (adequate performance)
4. Edge (adequate performance)

**Browser settings:**
- Enable hardware acceleration
- Close unnecessary tabs
- Disable ad blockers on chart page
- Use fullscreen mode for better performance

### Display Settings

**Optimal chart dimensions:**
- Width: 1200-1600px (balance detail vs performance)
- Height: 800-1000px
- Avoid very large dimensions (>2000px)

## Monitoring and Debugging

### Performance Metrics

**Monitor these metrics:**
- API response time (should be <500ms)
- Chart update frequency (actual vs configured)
- Memory usage growth over time
- CPU usage spikes

**Enable debug logging:**
```bash
export PYTHONPATH=$PWD
python3 scripts/nq_5m_chart.py --config default --debug
```

### Troubleshooting

**Common performance issues:**

1. **Slow chart updates:**
   - Check internet connection
   - Verify Databento API status
   - Reduce update frequency
   - Check system CPU usage

2. **High memory usage:**
   - Reduce time_range_hours
   - Disable volume subplot
   - Clear browser cache
   - Restart chart application

3. **API rate limiting:**
   - Increase update interval
   - Enable caching
   - Check Databento usage limits

## Production Deployment

### Server Requirements

**Minimum specifications:**
- CPU: 2 cores, 2.4GHz
- RAM: 4GB
- Network: 10Mbps stable connection
- OS: Linux, macOS, or Windows

**Recommended specifications:**
- CPU: 4+ cores, 3.0GHz
- RAM: 8GB+
- Network: 100Mbps low-latency connection
- SSD storage for caching

### Docker Deployment

**Performance optimizations:**
```dockerfile
# Optimize Python for production
ENV PYTHONOPTIMIZE=1
ENV PYTHONUNBUFFERED=1

# Use multi-stage build
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

### Monitoring in Production

**Key metrics to track:**
- Chart update latency
- API success rate
- Memory usage trends
- Error rates
- User session duration

**Alerting thresholds:**
- API latency > 1 second
- Memory usage > 80%
- Error rate > 5%
- Update frequency deviation > 20%

## Cost Optimization

### Databento Usage

**API cost management:**
- Use appropriate update intervals
- Enable smart caching
- Monitor monthly usage
- Set up billing alerts

**Estimated costs (USD/month):**
- Light usage (30 updates/day): ~$10-20
- Moderate usage (200 updates/day): ~$50-100
- Heavy usage (1000+ updates/day): ~$200-500

### Infrastructure Costs

**Cloud hosting estimates:**
- AWS t3.small: ~$15/month
- Digital Ocean droplet: ~$12/month
- Local server: One-time hardware cost

## Best Practices Summary

1. **Start with default configuration**
2. **Adjust update frequency based on trading style**
3. **Monitor resource usage regularly**
4. **Use caching to reduce API costs**
5. **Choose appropriate time ranges**
6. **Test configuration changes in non-market hours**
7. **Keep system and dependencies updated**
8. **Have backup data sources configured**
9. **Monitor Databento service status**
10. **Set up proper error handling and alerting**
