#!/usr/bin/env python3
"""
DEAD Simple Strategy - Volume Spike Detection
Detect and follow institutional money flow on expiration days

Core Philosophy:
- Find abnormal volume (Vol/OI > 10, Volume > 500)
- Verify institutional size (Volume × Price × $20 > $100K)
- Follow the direction (Calls = Long, Puts = Short)
- Hold until price hits strike
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class InstitutionalSignal:
    """Represents an institutional flow signal"""
    strike: float
    option_type: str  # 'CALL' or 'PUT'
    volume: int
    open_interest: int
    vol_oi_ratio: float
    option_price: float
    dollar_size: float
    direction: str  # 'LONG' or 'SHORT'
    target_price: float
    confidence: str  # 'EXTREME', 'VERY_HIGH', 'HIGH', 'MODERATE'
    timestamp: datetime
    expiration_date: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d

class DeadSimpleVolumeSpike:
    """
    DEAD Simple Strategy Implementation
    Detects institutional positioning through abnormal options volume
    """
    
    # Strategy parameters
    MIN_VOL_OI_RATIO = 10
    MIN_VOLUME = 500
    MIN_DOLLAR_SIZE = 100_000
    CONTRACT_MULTIPLIER = 20  # $20 per point for NQ mini
    
    # Confidence thresholds
    EXTREME_RATIO = 50
    VERY_HIGH_RATIO = 30
    HIGH_RATIO = 20
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize with optional custom configuration"""
        if config:
            self.MIN_VOL_OI_RATIO = config.get('min_vol_oi_ratio', self.MIN_VOL_OI_RATIO)
            self.MIN_VOLUME = config.get('min_volume', self.MIN_VOLUME)
            self.MIN_DOLLAR_SIZE = config.get('min_dollar_size', self.MIN_DOLLAR_SIZE)
    
    def analyze_strike(self, strike_data: Dict, current_price: float) -> Optional[InstitutionalSignal]:
        """
        Analyze a single strike for institutional activity
        
        Args:
            strike_data: Dictionary containing strike information
            current_price: Current underlying price
            
        Returns:
            InstitutionalSignal if criteria met, None otherwise
        """
        try:
            # Extract required fields with proper null handling
            raw_strike = strike_data.get('strike')
            raw_volume = strike_data.get('volume')
            raw_oi = strike_data.get('openInterest')
            raw_price = strike_data.get('lastPrice')
            
            # Skip if critical fields are None or empty
            if any(x is None for x in [raw_strike, raw_volume, raw_oi]):
                return None
            
            strike = float(raw_strike or 0)
            volume = int(raw_volume or 0)
            open_interest = int(raw_oi or 0)
            option_type = str(strike_data.get('optionType', '') or '').upper()
            option_price = float(raw_price or 0)
            
            # Skip if no open interest (avoid division by zero) or zero volume
            if open_interest == 0 or volume == 0:
                return None
            
            # Calculate volume/OI ratio
            vol_oi_ratio = volume / open_interest
            
            # Apply basic filters
            if vol_oi_ratio < self.MIN_VOL_OI_RATIO or volume < self.MIN_VOLUME:
                return None
            
            # Calculate dollar size (institutional footprint)
            dollar_size = volume * option_price * self.CONTRACT_MULTIPLIER
            
            if dollar_size < self.MIN_DOLLAR_SIZE:
                return None
            
            # Determine trading direction
            direction = 'LONG' if option_type == 'CALL' else 'SHORT'
            
            # Calculate confidence level
            confidence = self._calculate_confidence(vol_oi_ratio)
            
            # Create signal
            signal = InstitutionalSignal(
                strike=strike,
                option_type=option_type,
                volume=volume,
                open_interest=open_interest,
                vol_oi_ratio=vol_oi_ratio,
                option_price=option_price,
                dollar_size=dollar_size,
                direction=direction,
                target_price=strike,  # Target is the strike price
                confidence=confidence,
                timestamp=datetime.now(timezone.utc),
                expiration_date=strike_data.get('expirationDate', '')
            )
            
            logger.info(f"Institutional signal detected: {strike}{option_type} "
                       f"Vol/OI={vol_oi_ratio:.1f}x ${dollar_size:,.0f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing strike {strike_data}: {e}")
            return None
    
    def _calculate_confidence(self, vol_oi_ratio: float) -> str:
        """Calculate confidence level based on volume/OI ratio"""
        if vol_oi_ratio >= self.EXTREME_RATIO:
            return 'EXTREME'
        elif vol_oi_ratio >= self.VERY_HIGH_RATIO:
            return 'VERY_HIGH'
        elif vol_oi_ratio >= self.HIGH_RATIO:
            return 'HIGH'
        else:
            return 'MODERATE'
    
    def find_institutional_flow(self, options_chain: List[Dict], current_price: float) -> List[InstitutionalSignal]:
        """
        Scan entire options chain for institutional activity
        
        Args:
            options_chain: List of option strikes data
            current_price: Current underlying price
            
        Returns:
            List of institutional signals sorted by confidence and size
        """
        signals = []
        
        for strike_data in options_chain:
            signal = self.analyze_strike(strike_data, current_price)
            if signal:
                signals.append(signal)
        
        # Sort by confidence (priority) then by dollar size
        confidence_order = {'EXTREME': 0, 'VERY_HIGH': 1, 'HIGH': 2, 'MODERATE': 3}
        signals.sort(key=lambda s: (confidence_order.get(s.confidence, 999), -s.dollar_size))
        
        return signals
    
    def generate_trade_plan(self, signal: InstitutionalSignal, current_price: float) -> Dict:
        """
        Generate a specific trade plan based on institutional signal
        
        Args:
            signal: The institutional signal to trade
            current_price: Current underlying price
            
        Returns:
            Dictionary containing trade plan details
        """
        # Calculate entry and stops
        distance_to_target = abs(current_price - signal.target_price)
        
        if signal.direction == 'LONG':
            stop_loss = current_price - (distance_to_target * 0.5)
            take_profit = signal.target_price
        else:  # SHORT
            stop_loss = current_price + (distance_to_target * 0.5)
            take_profit = signal.target_price
        
        # Position sizing based on confidence
        confidence_multipliers = {
            'EXTREME': 3.0,
            'VERY_HIGH': 2.0,
            'HIGH': 1.5,
            'MODERATE': 1.0
        }
        
        size_multiplier = confidence_multipliers.get(signal.confidence, 1.0)
        
        trade_plan = {
            'signal': signal.to_dict(),
            'entry_price': current_price,
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'direction': signal.direction,
            'size_multiplier': size_multiplier,
            'risk_reward_ratio': 2.0,  # Fixed 1:2 risk/reward
            'notes': f"Following ${signal.dollar_size:,.0f} institutional flow at {signal.strike}"
        }
        
        return trade_plan
    
    def filter_actionable_signals(self, signals: List[InstitutionalSignal], 
                                 current_price: float,
                                 max_distance_percent: float = 2.0) -> List[InstitutionalSignal]:
        """
        Filter signals for actionable trades based on distance from current price
        
        Args:
            signals: List of institutional signals
            current_price: Current underlying price
            max_distance_percent: Maximum % distance from current price
            
        Returns:
            Filtered list of actionable signals
        """
        actionable = []
        
        for signal in signals:
            distance_percent = abs(signal.target_price - current_price) / current_price * 100
            
            if distance_percent <= max_distance_percent:
                actionable.append(signal)
            else:
                logger.debug(f"Signal at {signal.strike} too far ({distance_percent:.1f}%)")
        
        return actionable
    
    def summarize_institutional_activity(self, signals: List[InstitutionalSignal]) -> Dict:
        """
        Summarize overall institutional positioning
        
        Args:
            signals: List of institutional signals
            
        Returns:
            Summary statistics and positioning
        """
        if not signals:
            return {
                'total_signals': 0,
                'total_dollar_volume': 0,
                'call_dollar_volume': 0,
                'put_dollar_volume': 0,
                'net_positioning': 'NEUTRAL',
                'top_strikes': []
            }
        
        call_volume = sum(s.dollar_size for s in signals if s.option_type == 'CALL')
        put_volume = sum(s.dollar_size for s in signals if s.option_type == 'PUT')
        total_volume = call_volume + put_volume
        
        # Determine net positioning
        if total_volume > 0:
            call_percent = call_volume / total_volume * 100
            if call_percent > 65:
                net_positioning = 'BULLISH'
            elif call_percent < 35:
                net_positioning = 'BEARISH'
            else:
                net_positioning = 'MIXED'
        else:
            net_positioning = 'NEUTRAL'
        
        # Get top 5 strikes by dollar volume
        top_strikes = sorted(signals, key=lambda s: s.dollar_size, reverse=True)[:5]
        
        summary = {
            'total_signals': len(signals),
            'total_dollar_volume': total_volume,
            'call_dollar_volume': call_volume,
            'put_dollar_volume': put_volume,
            'net_positioning': net_positioning,
            'call_percentage': call_volume / total_volume * 100 if total_volume > 0 else 0,
            'put_percentage': put_volume / total_volume * 100 if total_volume > 0 else 0,
            'top_strikes': [
                {
                    'strike': s.strike,
                    'type': s.option_type,
                    'dollar_size': s.dollar_size,
                    'vol_oi_ratio': s.vol_oi_ratio,
                    'confidence': s.confidence
                }
                for s in top_strikes
            ]
        }
        
        return summary

# Integration with pipeline
def create_dead_simple_analyzer(config: Optional[Dict] = None) -> DeadSimpleVolumeSpike:
    """Factory function to create analyzer instance"""
    return DeadSimpleVolumeSpike(config)

# Example usage and testing
if __name__ == "__main__":
    # Example options data (would come from Barchart/Tradovate)
    sample_options = [
        {
            'strike': 21840,
            'optionType': 'PUT',
            'volume': 2750,
            'openInterest': 50,
            'lastPrice': 35.5,
            'expirationDate': '2024-01-10'
        },
        {
            'strike': 21900,
            'optionType': 'CALL',
            'volume': 1200,
            'openInterest': 100,
            'lastPrice': 42.0,
            'expirationDate': '2024-01-10'
        }
    ]
    
    # Initialize analyzer
    analyzer = DeadSimpleVolumeSpike()
    
    # Find institutional flow
    current_price = 21870
    signals = analyzer.find_institutional_flow(sample_options, current_price)
    
    # Display results
    print("\n=== DEAD Simple Strategy Analysis ===")
    print(f"Current Price: ${current_price:,.2f}")
    print(f"\nFound {len(signals)} institutional signals:")
    
    for signal in signals:
        print(f"\n{signal.strike}{signal.option_type[0]}:")
        print(f"  Vol/OI: {signal.vol_oi_ratio:.1f}x")
        print(f"  Dollar Size: ${signal.dollar_size:,.0f}")
        print(f"  Direction: {signal.direction} → {signal.target_price}")
        print(f"  Confidence: {signal.confidence}")
        
        # Generate trade plan
        trade_plan = analyzer.generate_trade_plan(signal, current_price)
        print(f"  Entry: ${trade_plan['entry_price']}")
        print(f"  Stop: ${trade_plan['stop_loss']}")
        print(f"  Target: ${trade_plan['take_profit']}")
    
    # Summary
    summary = analyzer.summarize_institutional_activity(signals)
    print(f"\n=== Institutional Summary ===")
    print(f"Total Dollar Volume: ${summary['total_dollar_volume']:,.0f}")
    print(f"Net Positioning: {summary['net_positioning']}")
    print(f"Call %: {summary['call_percentage']:.1f}%")
    print(f"Put %: {summary['put_percentage']:.1f}%")