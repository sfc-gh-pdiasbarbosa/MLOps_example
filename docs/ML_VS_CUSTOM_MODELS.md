# ML Models vs Custom Models: A Comparison Guide

This guide explains when to use traditional ML models versus custom (non-ML) models with Snowflake's ML platform.

## 🎯 Key Insight

**Snowflake's Model Registry is not just for ML models** — it's a general-purpose model management platform that works with any Python-based logic.

## 📊 Comparison Overview

| Aspect | ML Model (sklearn, etc.) | Custom Model (non-ML) |
|--------|-------------------------|----------------------|
| **Example** | Churn Prediction | Investment Strategy |
| **Learning** | ✅ Learns from data | ❌ Rule-based logic |
| **Training** | Required | Not needed |
| **Parameters** | Learned weights | Configuration values |
| **Inference** | Probabilistic | Deterministic |
| **Registry Support** | ✅ Native | ✅ Via CustomModel |

## 🏗 Architecture Comparison

### Traditional ML Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Raw Data   │───▶│  Features   │───▶│  Training   │───▶│   Model     │
│             │    │             │    │ (Learning)  │    │ (Weights)   │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                │
                                                                ▼
                                                        ┌─────────────┐
                                                        │ Predictions │
                                                        │(Probabilistic)│
                                                        └─────────────┘
```

### Custom Model Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Raw Data   │───▶│  Features   │───▶│Registration │───▶│   Model     │
│             │    │             │    │ (No Training)│   │  (Rules)    │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                │
                                                                ▼
                                                        ┌─────────────┐
                                                        │   Output    │
                                                        │(Deterministic)│
                                                        └─────────────┘
```

## 🔄 When to Use Each Approach

### Use Traditional ML Models When:

| Scenario | Example |
|----------|---------|
| Pattern recognition needed | Image classification, NLP |
| Complex relationships in data | Churn prediction, fraud detection |
| Predictions improve with more data | Recommendation systems |
| Outcomes are probabilistic | Risk scoring |
| You need confidence scores | Medical diagnosis support |

### Use Custom Models When:

| Scenario | Example |
|----------|---------|
| Business rules are well-defined | Trading strategies |
| Deterministic outputs required | Pricing engines |
| Regulatory requirements | Explainable risk calculations |
| Mathematical formulas | Financial ratios, actuarial models |
| No historical training data | New product pricing |

## 💻 Code Comparison

### ML Model (sklearn)

```python
from sklearn.linear_model import LogisticRegression
from snowflake.ml.registry import Registry

# Train the model
clf = LogisticRegression()
clf.fit(X_train, y_train)

# Register in Model Registry
reg = Registry(session=session)
reg.log_model(
    model=clf,
    model_name="CHURN_MODEL",
    version_name="v1",
    conda_dependencies=["scikit-learn"]
)

# Inference
model_ref = reg.get_model("CHURN_MODEL").version("v1")
predictions = model_ref.run(input_df, function_name="predict")
```

### Custom Model (Non-ML)

```python
from snowflake.ml.model import custom_model
from snowflake.ml.registry import Registry

class MomentumStrategy(custom_model.CustomModel):
    """Rule-based trading strategy - no ML involved"""
    
    def __init__(self, context):
        super().__init__(context)
        self.rsi_oversold = 30
        self.rsi_overbought = 70
    
    @custom_model.inference_api
    def predict(self, input_df):
        # Apply mathematical rules (not learned)
        results = []
        for _, row in input_df.iterrows():
            if row['RSI_14'] < self.rsi_oversold:
                signal = 'BUY'
            elif row['RSI_14'] > self.rsi_overbought:
                signal = 'SELL'
            else:
                signal = 'HOLD'
            results.append({'ASSET_ID': row['ASSET_ID'], 'SIGNAL': signal})
        return pd.DataFrame(results)

# Register in Model Registry (same as ML!)
strategy = MomentumStrategy(custom_model.ModelContext())
reg = Registry(session=session)
reg.log_model(
    model=strategy,
    model_name="MOMENTUM_STRATEGY",
    version_name="v1",
    conda_dependencies=["pandas", "numpy"]
)

# Inference (identical API!)
model_ref = reg.get_model("MOMENTUM_STRATEGY").version("v1")
signals = model_ref.run(input_df, function_name="predict")
```

## 🎁 Benefits of Using Model Registry for Custom Models

| Benefit | Description |
|---------|-------------|
| **Version Control** | Track strategy versions just like ML models |
| **Audit Trail** | Who deployed what, when |
| **Consistent API** | Same `run()` method for all model types |
| **Governance** | Approval workflows apply equally |
| **Lineage** | Track from data → features → model → output |
| **Rollback** | Easy version switching if issues arise |

## 📁 Feature Store Comparison

### ML Features (Churn Prediction)

```yaml
Features:
  - CUSTOMER_ID (entity key)
  - ACCOUNT_BALANCE (numeric)
  - TENURE_MONTHS (numeric)
  - NUM_PRODUCTS (numeric)
  - IS_ACTIVE_MEMBER (boolean)
  - TARGET_LABEL (label for training)

Purpose: Input to ML training algorithm
Refresh: Daily (or when data changes)
```

### Non-ML Features (Investment Strategy)

```yaml
Features:
  - ASSET_ID (entity key)
  - RSI_14 (technical indicator)
  - MA_20 (moving average)
  - MA_50 (moving average)
  - CURRENT_PRICE (latest price)
  - VOLATILITY_20 (risk metric)

Purpose: Input to rule-based calculations
Refresh: Hourly (or real-time for trading)
```

## 🔄 DAG Task Comparison

### ML Pipeline Tasks

| Task | Purpose | Training Involved |
|------|---------|-------------------|
| Feature Engineering | Calculate/transform features | No |
| Model Training | Learn patterns from data | **Yes** |
| Batch Inference | Apply learned model | No |

### Custom Model Pipeline Tasks

| Task | Purpose | Training Involved |
|------|---------|-------------------|
| Feature Engineering | Calculate indicators | No |
| Strategy Registration | Package & version rules | No |
| Signal Generation | Apply deterministic rules | No |

## 🌟 Real-World Use Cases

### ML Models

1. **Customer Churn Prediction** - Predict which customers will leave
2. **Fraud Detection** - Identify suspicious transactions
3. **Product Recommendations** - Suggest relevant items
4. **Demand Forecasting** - Predict future demand
5. **Sentiment Analysis** - Classify text sentiment

### Custom Models

1. **Investment Strategies** - Rule-based trading signals
2. **Pricing Engines** - Dynamic pricing calculations
3. **Risk Calculations** - VaR, stress testing
4. **Actuarial Models** - Insurance premium calculations
5. **Portfolio Optimization** - Asset allocation rules
6. **Credit Scoring Rules** - Deterministic credit decisions
7. **Compliance Checks** - Regulatory rule application

## 🎓 Key Takeaways

1. **Same Platform, Different Logic**
   - Model Registry works with both ML and custom models
   - Feature Store serves both use cases
   - DAGs orchestrate both pipeline types

2. **Custom Models Provide**
   - Deterministic, explainable outputs
   - Version control for business rules
   - Same governance as ML models

3. **Choose Based on Problem**
   - Learning from data → ML
   - Applying known rules → Custom
   - Often: Hybrid approaches work best

4. **Implementation Pattern**
   - Extend `CustomModel` base class
   - Implement `predict()` with `@inference_api` decorator
   - Register with `log_model()` just like ML

## 🔗 Resources

- [Snowflake Custom Models Docs](https://docs.snowflake.com/en/developer-guide/snowpark-ml/model-registry/custom-models)
- [Model Registry Overview](https://docs.snowflake.com/en/developer-guide/snowpark-ml/model-registry/overview)
- [Feature Store Overview](https://docs.snowflake.com/en/developer-guide/snowpark-ml/feature-store/overview)
- [ML Example: Churn Prediction](../examples/ml-churn-prediction/)
- [Non-ML Example: Investment Strategy](../examples/quant-investment-strategy/)

---

**The key insight**: Snowflake's ML platform is really a **model management platform** that works with any Python-based logic, whether it learns from data or applies deterministic rules.

