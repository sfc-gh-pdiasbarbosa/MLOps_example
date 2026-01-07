# ML Example: Customer Churn Prediction

This example demonstrates a **traditional ML pipeline** using Snowflake's ML capabilities for predicting customer churn.

## 📋 Overview

| Aspect | Details |
|--------|---------|
| **Use Case** | Customer Churn Prediction |
| **Model Type** | scikit-learn LogisticRegression |
| **Features** | Customer behavior & demographics |
| **Output** | Binary classification (churn/retain) |

## 🏗 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Raw Customer   │───▶│  Feature Store  │───▶│   ML Model      │
│     Data        │    │  (Dynamic Table)│    │  (Registry)     │
└─────────────────┘    └─────────────────┘    └────────┬────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Predictions   │
                                              │   (Output Table)│
                                              └─────────────────┘
```

## 📁 Structure

```
ml-churn-prediction/
├── src/
│   └── ml_logic.py         # Core ML pipeline logic
├── scripts/
│   └── deploy_pipeline.py  # DAG deployment script
├── config/
│   └── environments.yml    # Environment-specific settings
└── README.md               # This file
```

## 🔄 Pipeline Tasks

### Task 1: Feature Engineering
- Reads raw customer data
- Creates Entity in Feature Store (CUSTOMER_ID as key)
- Registers Feature View with automated refresh

### Task 2: Model Training
- Loads features from Feature Store
- Trains LogisticRegression model
- Registers model in Model Registry with:
  - Version tracking
  - Conda dependencies
  - Sample input for signature inference

### Task 3: Batch Inference
- Loads model from Registry
- Runs predictions on feature data
- Saves results to output table

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

## 📊 Key Snowflake Features Used

| Feature | Purpose |
|---------|---------|
| **Feature Store** | Centralized feature management with automated refresh |
| **Model Registry** | Version-controlled model storage with metadata |
| **DAG Tasks** | Orchestrated pipeline execution |
| **Dynamic Tables** | Automated feature materialization |

## 🔗 Related

- [Non-ML Example: Investment Strategy](../quant-investment-strategy/) - Same patterns with custom models
- [Comparison Guide](../../docs/ML_VS_CUSTOM_MODELS.md) - When to use each approach

