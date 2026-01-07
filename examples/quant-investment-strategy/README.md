# Non-ML Example: Quantitative Investment Strategy

This example demonstrates how to use Snowflake's ML platform features with **non-ML mathematical models**—specifically, a rule-based quantitative investment strategy.

## 🎯 Why This Matters

Many organizations have rule-based, mathematical, or algorithmic models that:
- Don't use machine learning
- Rely on deterministic calculations
- Need version control, deployment pipelines, and governance

**Snowflake's Model Registry supports these use cases** through the `CustomModel` class, proving that the ML platform is really a **model management platform** for any Python-based logic.

## 📋 Overview

| Aspect | Details |
|--------|---------|
| **Use Case** | Momentum-based Investment Strategy |
| **Model Type** | Custom Python class (non-ML) |
| **Features** | Technical indicators (RSI, Moving Averages) |
| **Output** | Trading signals (BUY/SELL/HOLD) |

## 🏗 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Market Price   │───▶│  Feature Store  │───▶│ Custom Strategy │
│     Data        │    │ (Tech Indicators)│    │  (Registry)     │
└─────────────────┘    └─────────────────┘    └────────┬────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │ Trading Signals │
                                              │   (BUY/SELL)    │
                                              └─────────────────┘
```

## 📁 Structure

```
quant-investment-strategy/
├── src/
│   └── strategy_logic.py       # Strategy implementation & CustomModel
├── scripts/
│   └── deploy_pipeline.py      # DAG deployment script
├── config/
│   └── environments.yml        # Environment-specific settings
└── README.md                   # This file
```

## 💡 Key Concepts

### 1. Custom Model Class

The core of this example is the `MomentumStrategy` class that extends Snowflake's `CustomModel`:

```python
from snowflake.ml.model import custom_model

class MomentumStrategy(custom_model.CustomModel):
    def __init__(self, context: custom_model.ModelContext):
        super().__init__(context)
        # Strategy parameters (versioned with the model)
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.ma_short_window = 20
    
    @custom_model.inference_api
    def predict(self, input_df: pd.DataFrame) -> pd.DataFrame:
        # Apply mathematical rules to generate signals
        # No ML involved - pure algorithmic logic
        ...
```

### 2. Feature Store for Technical Indicators

Feature Store isn't just for ML features! It's perfect for:
- Technical indicators (RSI, MACD, Bollinger Bands)
- Financial ratios
- Risk metrics
- Any derived calculations

### 3. Model Registry for Strategy Versioning

Register your strategy just like an ML model:
```python
reg = Registry(session=session)
reg.log_model(
    model=strategy,
    model_name="MOMENTUM_STRATEGY",
    version_name="v1_momentum",
    comment="Non-ML custom model"
)
```

## 🔄 Pipeline Tasks

### Task 1: Calculate Technical Indicators
- Reads raw market data (OHLCV)
- Calculates RSI, Moving Averages, Volatility
- Registers as Feature View (hourly refresh)

### Task 2: Register Strategy
- Wraps strategy logic in CustomModel
- Registers in Model Registry with:
  - Version tracking
  - Parameter documentation
  - Sample input signature

### Task 3: Generate Signals
- Loads strategy from Registry
- Applies rules to current data
- Outputs trading signals with:
  - Signal type (BUY/SELL/HOLD)
  - Signal strength (0-1)
  - Reasoning explanation

## 📊 Strategy Logic

The `MomentumStrategy` uses these rules:

| Condition | Signal | Weight |
|-----------|--------|--------|
| RSI < 30 (oversold) | BUY | 0.4 |
| RSI > 70 (overbought) | SELL | 0.4 |
| Price > MA20 > MA50 | BUY | 0.3 |
| Price < MA20 < MA50 | SELL | 0.3 |
| MA20 > MA50 (golden cross) | BUY | 0.2 |
| MA20 < MA50 (death cross) | SELL | 0.2 |

Final signal based on weighted score (threshold: 0.5)

## 🚀 Deployment

```bash
# Set environment variables
export SNOWFLAKE_ACCOUNT="your_account"
export SNOWFLAKE_USER="your_user"
export SNOWFLAKE_PRIVATE_KEY="your_key"
export SNOWFLAKE_ROLE="ML_DEV_ROLE"
export SNOWFLAKE_WAREHOUSE="DEV_WH_XS"
export SNOWFLAKE_DATABASE="DEV_ML_DB"
export SNOWFLAKE_SCHEMA="PIPELINES"

# Deploy to DEV
python scripts/deploy_pipeline.py DEV
```

## 📈 Output Example

```
| ASSET_ID | SIGNAL | STRENGTH | POSITION_SIZE | REASONING                           |
|----------|--------|----------|---------------|-------------------------------------|
| AAPL     | BUY    | 0.7500   | 0.0150        | RSI=28.5 (oversold); Golden cross   |
| MSFT     | HOLD   | 0.4500   | 0.0000        | RSI=55.0 (neutral); Price > MA20    |
| GOOGL    | SELL   | 0.6000   | 0.0000        | RSI=72.3 (overbought); Death cross  |
```

## 🔑 Benefits of This Approach

| Benefit | Description |
|---------|-------------|
| **Version Control** | Strategy parameters tracked in Model Registry |
| **Audit Trail** | Every signal generation logged with strategy version |
| **Consistency** | Same strategy logic across all environments |
| **Governance** | Approval workflows before production deployment |
| **Scalability** | Snowflake handles execution at scale |

## 🔗 Related

- [ML Example: Churn Prediction](../ml-churn-prediction/) - Traditional ML approach
- [Comparison Guide](../../docs/ML_VS_CUSTOM_MODELS.md) - When to use each approach
- [Snowflake Custom Models Docs](https://docs.snowflake.com/en/developer-guide/snowpark-ml/model-registry/custom-models)

## ⚠️ Disclaimer

This is an **educational example** for demonstrating Snowflake capabilities. The investment strategy shown is simplified and should not be used for actual trading decisions.

