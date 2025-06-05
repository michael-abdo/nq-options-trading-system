# Risk Analysis ("Who Has More Skin in the Game?")

## Philosophy & Meaning

The **Risk Analysis** is a systematic examination of open interest positioning to identify where the largest financial commitments exist in the options chain, revealing institutional positioning and potential support/resistance levels based on "skin in the game" analysis.

### Core Philosophy
- **Follow the Money**: Large open interest positions represent significant financial commitments
- **Defense Theory**: Options writers will defend their positions, creating natural support/resistance
- **Asymmetric Risk**: Identify which side (calls vs puts) has more to lose from price movement
- **Battle Zone Mapping**: Locate critical price levels where major options positions face expiration risk

### Key Concepts
1. **Total Risk Calculation**: Open Interest × Premium × Multiplier = Dollar Risk
2. **Dominance Analysis**: Compare total call risk vs total put risk for directional bias
3. **Proximity Danger**: Near-the-money positions have higher defense urgency
4. **Battle Zones**: Price levels with concentrated risk requiring active defense

### Risk Classifications
- **STRONG CALL DOMINANCE** (Ratio > 2.0): Bulls have much more to lose → Upward pressure expected
- **STRONG PUT DOMINANCE** (Ratio < 0.5): Bears have much more to lose → Downward pressure expected  
- **BALANCED RISK** (0.5 ≤ Ratio ≤ 2.0): Contested territory → Sideways/choppy action expected

## Pseudocode

```pseudocode
FUNCTION analyzeOptionsRisk(currentPrice, optionsChain, multiplier):
    
    // Initialize risk containers
    callsAtRisk = []
    putsAtRisk = []
    totalCallRisk = 0
    totalPutRisk = 0
    
    // STEP 1: CLASSIFY RISK BY STRIKE
    FOR each strike in optionsChain:
        callRisk = strike.callOpenInterest * strike.callPremium * multiplier
        putRisk = strike.putOpenInterest * strike.putPremium * multiplier
        distance = ABS(strike.level - currentPrice)
        
        // Calls at risk if OTM (strike > current price)
        IF strike.level > currentPrice AND callRisk > 0:
            callsAtRisk.ADD({
                strike: strike.level,
                openInterest: strike.callOpenInterest,
                premium: strike.callPremium,
                totalRisk: callRisk,
                distance: strike.level - currentPrice
            })
            totalCallRisk += callRisk
        
        // Puts at risk if OTM (strike < current price)  
        IF strike.level < currentPrice AND putRisk > 0:
            putsAtRisk.ADD({
                strike: strike.level,
                openInterest: strike.putOpenInterest,
                premium: strike.putPremium,
                totalRisk: putRisk,
                distance: currentPrice - strike.level
            })
            totalPutRisk += putRisk
    END FOR
    
    // STEP 2: CALCULATE DOMINANCE METRICS
    riskRatio = totalCallRisk / totalPutRisk
    
    IF riskRatio > 2.0:
        verdict = "STRONG CALL DOMINANCE - Bulls have much more to lose"
        bias = "UPWARD PRESSURE EXPECTED"
    ELSE IF riskRatio < 0.5:
        verdict = "STRONG PUT DOMINANCE - Bears have much more to lose"  
        bias = "DOWNWARD PRESSURE EXPECTED"
    ELSE:
        verdict = "BALANCED RISK - Contested territory"
        bias = "SIDEWAYS/CHOPPY ACTION EXPECTED"
    END IF
    
    // STEP 3: FIND CRITICAL BATTLE ZONES
    SORT callsAtRisk BY distance ASCENDING
    SORT putsAtRisk BY distance ASCENDING
    
    nearestCallThreat = callsAtRisk[0] IF callsAtRisk.LENGTH > 0
    nearestPutThreat = putsAtRisk[0] IF putsAtRisk.LENGTH > 0
    
    // STEP 4: VOLUME ANALYSIS (REINFORCEMENTS)
    FUNCTION calculateReinforcementStrength(strike):
        IF strike.openInterest > 0:
            activityRatio = strike.todayVolume / strike.openInterest
            IF activityRatio > 1.0:
                RETURN "HEAVY REINFORCEMENTS"
            ELSE IF activityRatio > 0.5:
                RETURN "MODERATE ACTIVITY" 
            ELSE:
                RETURN "EXISTING POSITIONS"
            END IF
        ELSE:
            RETURN "NEW POSITIONS ONLY"
        END IF
    END FUNCTION
    
    // STEP 5: PROXIMITY DANGER SCORING
    FUNCTION calculateDangerScore(riskAmount, distance):
        IF distance <= 10:
            urgency = "IMMEDIATE"
            multiplier = 3.0
        ELSE IF distance <= 25:
            urgency = "NEAR TERM" 
            multiplier = 2.0
        ELSE IF distance <= 50:
            urgency = "MEDIUM TERM"
            multiplier = 1.0
        ELSE:
            urgency = "DISTANT"
            multiplier = 0.5
        END IF
        
        RETURN riskAmount * multiplier, urgency
    END FUNCTION
    
    // STEP 6: BATTLE ZONE MAPPING
    battleZones = []
    
    FOR each strike in (callsAtRisk + putsAtRisk):
        dangerScore, urgency = calculateDangerScore(strike.totalRisk, strike.distance)
        
        battleZones.ADD({
            strike: strike.strike,
            type: IF strike in callsAtRisk THEN "CALL DEFENSE" ELSE "PUT DEFENSE",
            riskAmount: strike.totalRisk,
            distance: strike.distance,
            dangerScore: dangerScore,
            urgency: urgency
        })
    END FOR
    
    SORT battleZones BY dangerScore DESCENDING
    
    // STEP 7: GENERATE TRADING SIGNALS
    signals = []
    
    // Immediate threats (within 10 points)
    FOR each zone in battleZones:
        IF zone.urgency == "IMMEDIATE":
            IF zone.type == "CALL DEFENSE":
                signals.ADD("STRONG SUPPORT expected at " + zone.strike)
            ELSE:
                signals.ADD("STRONG RESISTANCE expected at " + zone.strike)
            END IF
        END IF
    END FOR
    
    // Directional bias
    IF nearestCallThreat AND nearestPutThreat:
        IF nearestCallThreat.distance < nearestPutThreat.distance:
            signals.ADD("UPWARD BIAS - Calls closer to danger")
        ELSE:
            signals.ADD("DOWNWARD BIAS - Puts closer to danger")
        END IF
    END IF
    
    RETURN {
        summary: {
            totalCallRisk: totalCallRisk,
            totalPutRisk: totalPutRisk,
            riskRatio: riskRatio,
            verdict: verdict,
            bias: bias
        },
        threats: {
            nearestCallThreat: nearestCallThreat,
            nearestPutThreat: nearestPutThreat
        },
        battleZones: battleZones[0:5],  // Top 5 critical zones
        signals: signals
    }
END FUNCTION
```

## Trading Signals Generated
- **DIRECTIONAL BIAS**: Market pressure direction based on risk asymmetry
- **SUPPORT/RESISTANCE LEVELS**: Price levels where large positions will defend
- **BATTLE ZONES**: Critical strikes with concentrated risk and high danger scores
- **INSTITUTIONAL POSITIONING**: Where smart money has significant commitments

## Integration Role
Provides **institutional positioning context** and **key level identification** to complement Expected Value trades. When EV identifies an opportunity, risk analysis reveals whether institutional positioning supports the trade and identifies critical levels for entries and exits.

## Configuration
- `multiplier`: Contract multiplier for dollar risk calculation (typically 20 for NQ)
- `immediate_threat_distance`: Distance threshold for immediate urgency (default: 10 points)
- `near_term_distance`: Distance threshold for near-term urgency (default: 25 points)
- `medium_term_distance`: Distance threshold for medium-term urgency (default: 50 points)

## Files
- `risk_analysis.txt` - Complete pseudocode implementation
- `README.md` - This documentation