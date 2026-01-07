# Model Operations Examples for Snowflake

A comprehensive repository demonstrating best practices for deploying and managing both **ML and non-ML models** on Snowflake using Feature Store, Model Registry, DAGs, and GitHub Actions CI/CD.

## 🎯 Key Insight

> **Snowflake's ML platform isn't just for Machine Learning** — it's a complete model management platform that works with any Python-based logic, whether learned from data or based on deterministic rules.

This repository proves it with two complete examples:

| Example | Model Type | Use Case |
|---------|------------|----------|
| [ML Churn Prediction](./examples/ml-churn-prediction/) | sklearn LogisticRegression | Customer churn prediction |
| [Investment Strategy](./examples/quant-investment-strategy/) | **Custom Python (non-ML)** | Momentum trading signals |

## 🏗 Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                          │
│  ┌──────────────┐  ┌──────────────┐   ┌──────────────┐ ┌────────┐ │
│  │ feature/**   │  │ development  │   │  release/**  │ │ main   │ │
│  │   branches   │  │   branch     │   │   branches   │ │ branch │ │
│  └──────┬───────┘  └──────┬───────┘   └──────┬───────┘ └───┬────┘ │
└─────────┼─────────────────┼──────────────────┼─────────────┼──────┘
          │                 │                  │             │
          ▼                 ▼                  ▼             ▼
    ┌─────────┐        ┌─────────┐       ┌─────────┐    ┌─────────┐
    │   DEV   │───────▶│   SIT   │──────▶│   UAT   │───▶│   PRD   │
    │ (XS WH) │        │  (S WH) │       │  (M WH) │    │  (L WH) │
    └─────────┘        └─────────┘       └─────────┘    └─────────┘
    Auto Deploy        Auto Deploy       Auto Deploy    Manual Approval
```

### Shared Infrastructure, Different Logic

Both examples use the **same Snowflake features**:

| Feature | ML Example | Non-ML Example |
|---------|------------|----------------|
| **Feature Store** | Customer behavior features | Technical indicators |
| **Model Registry** | sklearn model | CustomModel class |
| **DAG Tasks** | Train → Infer | Register → Execute |
| **CI/CD** | Same GitHub Actions | Same patterns |

## 📁 Repository Structure

```
.
├── examples/
│   ├── ml-churn-prediction/           # Traditional ML example
│   │   ├── src/ml_logic.py            # sklearn-based pipeline
│   │   ├── scripts/deploy_pipeline.py
│   │   ├── config/environments.yml
│   │   └── README.md
│   │
│   └── quant-investment-strategy/     # Non-ML custom model example
│       ├── src/strategy_logic.py      # Rule-based strategy (pandas/numpy)
│       ├── scripts/deploy_pipeline.py
│       ├── config/environments.yml
│       └── README.md
│
├── sql/                               # Shared SQL setup scripts
│   ├── 00_setup_warehouses.sql
│   ├── 01_setup_dev_environment.sql
│   ├── 02_setup_sit_environment.sql
│   ├── 02b_setup_uat_environment.sql
│   ├── 03_setup_prd_environment.sql
│   ├── 04_setup_roles_and_grants.sql
│   ├── 05_setup_market_data_tables.sql  # For investment strategy
│   ├── 99_setup_all_environments.sql
│   └── README.md
│
├── docs/
│   ├── ML_VS_CUSTOM_MODELS.md         # Comparison guide
│   └── BRANCH_PROTECTION.md           # Security setup guide
│
├── .github/
│   ├── workflows/
│   │   ├── ml_churn_deploy.yml        # ML pipeline CI/CD
│   │   └── quant_strategy_deploy.yml  # Strategy pipeline CI/CD
│   └── actionlint.yaml
│
├── requirements.txt
└── README.md                          # This file
```

## 🚀 Quick Start

### Prerequisites

- Snowflake account with ACCOUNTADMIN access
- GitHub repository with Actions enabled
- Python 3.12+

### Step 1: Setup Snowflake Infrastructure

```bash
# Run SQL scripts in order (in Snowsight)
sql/00_setup_warehouses.sql
sql/01_setup_dev_environment.sql
sql/02_setup_sit_environment.sql
sql/02b_setup_uat_environment.sql
sql/03_setup_prd_environment.sql
sql/04_setup_roles_and_grants.sql
sql/05_setup_market_data_tables.sql  # For investment strategy example
```

Or use the all-in-one script: `sql/99_setup_all_environments.sql`

### Step 2: Create Snowflake Service Account

```sql
-- Generate key pair locally first:
-- openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out snowflake_key.p8 -nocrypt
-- openssl rsa -in snowflake_key.p8 -pubout -out snowflake_key.pub

USE ROLE ACCOUNTADMIN;

CREATE USER IF NOT EXISTS github_actions_user
    RSA_PUBLIC_KEY = '<paste content of snowflake_key.pub>'
    DEFAULT_ROLE = ML_CICD_ROLE
    MUST_CHANGE_PASSWORD = FALSE
    COMMENT = 'Service account for GitHub Actions CI/CD';

GRANT ROLE ML_CICD_ROLE TO USER github_actions_user;
```

### Step 3: Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret Name | Value | Format |
|-------------|-------|--------|
| `SNOWFLAKE_ACCOUNT` | Your account identifier | `orgname-accountname` or `xy12345.us-east-1` |
| `SNOWFLAKE_USER` | Service account username | `github_actions_user` |
| `SNOWFLAKE_PRIVATE_KEY` | Private key content | Full PEM including `-----BEGIN/END-----` |
| `SNOWFLAKE_ROLE` | Fallback role | `ML_CICD_ROLE` |

#### Finding Your Account Identifier

1. Log into Snowsight
2. Look at URL: `https://app.snowflake.com/ORGNAME/ACCOUNTNAME/`
3. Your account = `ORGNAME-ACCOUNTNAME`

Or run in Snowflake:
```sql
SELECT CURRENT_ORGANIZATION_NAME() || '-' || CURRENT_ACCOUNT_NAME();
```

#### ⚠️ Common Mistakes

| ❌ Wrong | ✅ Correct |
|----------|-----------|
| `myorg-myaccount.snowflakecomputing.com` | `myorg-myaccount` |
| `https://myorg-myaccount.snowflakecomputing.com` | `myorg-myaccount` |
| Encrypted private key (has passphrase) | Unencrypted key (`-nocrypt` flag) |

#### Optional: Environment-Specific Roles

For more granular access control, add these additional secrets:

```
SNOWFLAKE_DEV_ROLE: ML_DEV_ROLE
SNOWFLAKE_SIT_ROLE: ML_SIT_ROLE
SNOWFLAKE_UAT_ROLE: ML_UAT_ROLE
SNOWFLAKE_PRD_ROLE: ML_PRD_ROLE
```

If not set, the workflow falls back to `SNOWFLAKE_ROLE`.

### Step 4: Deploy an Example

```bash
# Clone and create a feature branch
git checkout -b feature/test-deployment

# Make changes to either example
# Push to trigger CI/CD
git push origin feature/test-deployment
```

## 📊 Example Comparison

### ML Example: Customer Churn Prediction

| Aspect | Details |
|--------|---------|
| **Model** | `sklearn.linear_model.LogisticRegression` |
| **Training** | ✅ Learns from historical customer data |
| **Output** | Churn probability (0-1) |
| **Refresh** | Daily (retrain on new data) |

**Pipeline Flow:**
```
Raw Customers → Feature Engineering → Model Training → Batch Inference
```

### Non-ML Example: Momentum Investment Strategy

| Aspect | Details |
|--------|---------|
| **Model** | `custom_model.CustomModel` subclass |
| **Training** | ❌ No training (rule-based) |
| **Output** | Trading signals (BUY/SELL/HOLD) |
| **Refresh** | Hourly (apply rules to new data) |

**Pipeline Flow:**
```
Market Data → Technical Indicators → Strategy Registration → Signal Generation
```

## 💡 Why This Matters

Many organizations have models that aren't traditional ML:

- **Quantitative Finance**: Trading strategies, risk models
- **Insurance**: Actuarial calculations, pricing rules
- **Retail**: Pricing engines, markdown optimization
- **Healthcare**: Clinical decision rules, dosage calculations
- **Manufacturing**: Quality control rules, optimization algorithms

**These all benefit from:**
- Version control ✅
- Audit trails ✅
- Environment promotion ✅
- Governance ✅

Snowflake's Model Registry handles all of these through the `CustomModel` class.

## 🔄 Branching Strategy

| Branch | Environment | Approval | DAG State |
|--------|-------------|----------|-----------|
| `feature/**` | DEV | Auto | Suspended |
| `development` | SIT | Auto | Suspended |
| `release/**` | UAT | Auto | Suspended |
| `main` | PRD | **Manual** | Active |

See [Branch Protection Guide](./docs/BRANCH_PROTECTION.md) for setup.

## 🧪 Environment Details

| Environment | Warehouse | Purpose | Data |
|-------------|-----------|---------|------|
| DEV | XS | Development | Sample |
| SIT | Small | Integration | Sample |
| UAT | Medium | Pre-production | Production-like |
| PRD | Large | Production | Real |

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ML vs Custom Models](./docs/ML_VS_CUSTOM_MODELS.md) | When to use each approach |
| [Branch Protection](./docs/BRANCH_PROTECTION.md) | Security setup guide |
| [SQL Setup](./sql/README.md) | Infrastructure scripts |
| [ML Example README](./examples/ml-churn-prediction/README.md) | Churn prediction details |
| [Strategy Example README](./examples/quant-investment-strategy/README.md) | Investment strategy details |

## ⚠️ Limitations & Recommendations

This is an **example repository** for learning. For production, consider:

### 🔴 Critical Gaps

1. **No Automated Testing** - Add pytest, data validation
2. **No Model Validation Gates** - Add performance thresholds
3. **Limited Monitoring** - Add drift detection, alerting
4. **No Rollback Strategy** - Implement blue-green deployments

### 🟡 Enhancements

5. **Basic Error Handling** - Add retries, dead letter queues
6. **Simplified Logic** - Production needs more robust calculations
7. **Single Model Architecture** - Consider ensembles, A/B testing
8. **Security Hardening** - Secrets rotation, audit logging

See the [full recommendations list](#) in each example's README.

## 🔗 Resources

### Snowflake Documentation
- [Model Registry](https://docs.snowflake.com/en/developer-guide/snowpark-ml/model-registry/overview)
- [Custom Models](https://docs.snowflake.com/en/developer-guide/snowpark-ml/model-registry/custom-models)
- [Feature Store](https://docs.snowflake.com/en/developer-guide/snowpark-ml/feature-store/overview)
- [DAG Tasks](https://docs.snowflake.com/en/user-guide/tasks-intro)

### GitHub Actions
- [Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)

## 🎉 Key Takeaway

> Whether you're deploying a neural network or a pricing formula, Snowflake's ML platform provides the same governance, versioning, and operational capabilities. **It's not just for ML — it's for all your models.**

---

**Version**: 2.0  
**Last Updated**: 2025-01-07  
**Examples**: ML (sklearn) + Non-ML (CustomModel)
