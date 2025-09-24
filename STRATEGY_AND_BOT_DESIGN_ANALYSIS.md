# Strategy and Investor Design Analysis

## Problem Statement Responses

### 1. JavaScript Error Fix ✅
**Issue**: `makePredictionWithModel` function was defined but not exposed to global window object.

**Fix**: Added `window.makePredictionWithModel = makePredictionWithModel;` to the global function exports in `dashboard/static/scripts/scripts.js` line 4189.

### 2. Investor Sport/Market Assignment Design 

**Question**: Do investors need to be assigned to a specific sport and market if strategies are?

**Analysis from codebase**:

Based on `factors.txt` design specification:
```
Each investor/investor has:
    a balance
    a sport
    a market (hth, total, spread)
    a strategy
    a model
```

**Answer**: Yes, investors should be assigned to specific sports and markets even if strategies are, for the following reasons:

1. **Granular Control**: Investors serve as the execution layer that implements strategies. A strategy might be general (e.g., "bet on favorites"), but the investor needs specific constraints about which sports/markets to apply it to.

2. **Risk Management**: Different sports have different volatility profiles. A investor assigned to NBA might have different bankroll management than one assigned to NFL due to game frequency.

3. **Model Specialization**: The system design shows each investor has its own model. Sports-specific models (NBA LSTM vs NFL Ensemble) perform better than generic models.

4. **Portfolio Diversification**: Users can run multiple investors with the same strategy across different sports/markets to diversify risk.

**Current Implementation**: The code shows investors have sport fields (`investor.sport`) and the system generates sport-specific game data and analytics.

### 3. Edit Strategy vs Strategy Builder Distinction

**Question**: Why is there "Edit Strategy" on the main page and also a Strategy Builder?

**Analysis**:

**Edit Strategy (Modal)**:
- Simple form-based interface for modifying existing strategy parameters
- Located in strategy details modal
- Focuses on parameter tuning (min_odds_edge, confidence_threshold, etc.)
- Quick edits for experienced users

**Visual Strategy Builder (Dedicated Page)**:
- Advanced drag-and-drop visual interface
- Component-based strategy construction
- Logic blocks (IF/THEN, AND/OR), betting logic, market analysis
- More comprehensive strategy creation from scratch
- Better for complex strategy design and visualization

**Design Rationale**:
1. **Different Use Cases**: Edit is for tweaks, Builder is for creation
2. **User Experience**: Simple edits don't need full builder interface
3. **Complexity Levels**: Builder handles complex logical flows, Edit handles simple parameters
4. **Workflow Efficiency**: Quick parameter changes vs. full strategy redesign

## Recommendations

### 1. Investor-Strategy-Sport-Market Relationship
```
User
├── Investors (execution layer)
│   ├── Sport: NBA/NFL/MLB/etc
│   ├── Market: spread/total/moneyline
│   ├── Strategy: reference to strategy
│   └── Model: sport-specific ML model
└── Strategies (logic layer)
    ├── Parameters: configurable rules
    ├── Logic: betting conditions
    └── Can be shared across multiple investors
```

### 2. Strategy Interface Clarification
- Keep both interfaces but improve naming/descriptions
- "Quick Edit Strategy" vs "Advanced Strategy Builder"
- Add help tooltips explaining when to use each
- Consider adding "Duplicate to Builder" option in Edit modal

### 3. TailwindCSS CDN Usage
The TailwindCSS CDN warning is expected in development. For production:
- Install TailwindCSS as PostCSS plugin
- Build CSS file during deployment
- Replace CDN link with compiled CSS file

## Implementation Status
- [x] Fixed JavaScript ReferenceError
- [x] Documented design rationale for investor/strategy relationships
- [x] Explained dual strategy interface purpose
- [ ] Consider UI improvements for strategy interface clarity

---

**Last Updated**: 9/13/2025