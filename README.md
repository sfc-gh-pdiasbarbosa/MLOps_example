# MLOps Pipeline Example - Snowflake ML

A comprehensive example of MLOps best practices for deploying and managing Machine Learning pipelines on Snowflake using GitHub Actions, Snowpark, and Snowflake ML features (Feature Store, Model Registry).

## 📋 Overview

This repository demonstrates an end-to-end ML pipeline for **customer churn prediction** that follows industry best practices for:

- ✅ **Environment Promotion**: DEV → SIT → UAT → PRD
- ✅ **GitFlow Branching Strategy**: Feature branches, development, release, and main
- ✅ **Infrastructure as Code**: SQL scripts for Snowflake object management
- ✅ **CI/CD Automation**: GitHub Actions for automated deployments
- ✅ **Security**: Role-based access control (RBAC) and environment-specific service accounts
- ✅ **ML Best Practices**: Feature Store, Model Registry, and DAG-based orchestration

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ feature/**   │  │ development  │  │  release/**  │  main    │
│  │   branches   │  │   branch     │  │   branches   │  branch  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  ────┬──│
└─────────┼──────────────────┼──────────────────┼──────────────┼──┘
          │                  │                  │              │
          ▼                  ▼                  ▼              ▼
    ┌─────────┐        ┌─────────┐       ┌─────────┐    ┌─────────┐
    │   DEV   │───────▶│   SIT   │──────▶│   UAT   │───▶│   PRD   │
    │ (XS WH) │        │  (S WH) │       │  (M WH) │    │  (L WH) │
    └─────────┘        └─────────┘       └─────────┘    └─────────┘
    Auto Deploy        Auto Deploy       Auto Deploy    Manual Approval
```

### Pipeline Flow

1. **Feature Engineering** → Reads raw data, transforms features, creates Feature View
2. **Model Training** → Trains scikit-learn model using Feature Store data
3. **Model Registration** → Registers model in Snowflake Model Registry
4. **Batch Inference** → Runs predictions and saves to output table

All orchestrated via **Snowflake DAG** (Task Graph) with configurable scheduling.

## 📁 Repository Structure

```
.
├── .github/
│   ├── workflows/
│   │   └── snowflake_ml_deploy.yml    # CI/CD pipeline definition
│   └── actionlint.yaml                 # GitHub Actions linter config
│
├── config/
│   └── environments.yml                # Environment-specific configurations
│
├── scripts/
│   └── deploy_pipeline.py              # DAG deployment script
│
├── src/
│   └── ml_logic.py                     # ML pipeline logic (feature eng, training, inference)
│
├── sql/
│   ├── 00_setup_warehouses.sql         # Warehouse creation
│   ├── 01_setup_dev_environment.sql    # DEV environment setup
│   ├── 02_setup_sit_environment.sql    # SIT environment setup
│   ├── 02b_setup_uat_environment.sql   # UAT environment setup
│   ├── 03_setup_prd_environment.sql    # PRD environment setup
│   ├── 04_setup_roles_and_grants.sql   # RBAC setup
│   ├── 99_setup_all_environments.sql   # All-in-one setup script
│   └── README.md                       # SQL scripts documentation
│
├── docs/
│   └── BRANCH_PROTECTION.md            # Branch protection setup guide
│
├── requirements.txt                     # Python dependencies
└── README.md                           # This file
```

## 🚀 Quick Start

### Prerequisites

- Snowflake account with ACCOUNTADMIN access
- GitHub repository with Actions enabled
- Python 3.12+ (for local development)
- Snowflake CLI installed (optional, for local testing)

### Step 1: Setup Snowflake Infrastructure

Execute SQL scripts in order (in Snowsight or via SnowSQL):

```bash
# Option A: Individual scripts (recommended for production)
sql/00_setup_warehouses.sql         # Creates compute warehouses
sql/01_setup_dev_environment.sql    # DEV environment
sql/02_setup_sit_environment.sql    # SIT environment
sql/02b_setup_uat_environment.sql   # UAT environment
sql/03_setup_prd_environment.sql    # PRD environment
sql/04_setup_roles_and_grants.sql   # Security & RBAC

# Option B: All-in-one (good for demos)
sql/99_setup_all_environments.sql   # Creates everything at once
```

### Step 2: Configure GitHub Secrets

Navigate to **Settings → Secrets and variables → Actions** and add:

```yaml
# Common secrets (used across all environments)
SNOWFLAKE_ACCOUNT: "<your_account_identifier>"
SNOWFLAKE_USER: "<github_actions_service_account>"
SNOWFLAKE_PRIVATE_KEY: "<private_key_content>"

# Environment-specific role secrets
SNOWFLAKE_DEV_ROLE: "ML_DEV_ROLE"
SNOWFLAKE_SIT_ROLE: "ML_SIT_ROLE"
SNOWFLAKE_UAT_ROLE: "ML_UAT_ROLE"
SNOWFLAKE_PRD_ROLE: "ML_PRD_ROLE"
```

### Step 3: Setup Branch Protection

Follow instructions in [`docs/BRANCH_PROTECTION.md`](./docs/BRANCH_PROTECTION.md) to configure:

- Required pull request reviews
- Status checks before merging
- Manual approval environment for production

### Step 4: Deploy Your First Pipeline

```bash
# Create a feature branch
git checkout -b feature/initial-pipeline

# Make changes and push
git add .
git commit -m "Initial ML pipeline setup"
git push origin feature/initial-pipeline

# GitHub Actions will automatically deploy to DEV
# Check Actions tab for deployment status
```

## 🔄 Branching & Deployment Strategy

This repository follows **Enhanced GitFlow** with environment promotion:

| Branch Pattern | Environment | Auto-Deploy | Approval Required | DAG Schedule |
|----------------|-------------|-------------|-------------------|--------------|
| `feature/**`   | DEV         | ✅ Yes      | ❌ No             | Suspended    |
| `development`  | SIT         | ✅ Yes      | ❌ No             | Suspended    |
| `release/**`   | UAT         | ✅ Yes      | ❌ No             | Suspended    |
| `main`         | PRD         | ✅ Yes      | ✅ **Yes**        | Active (24h) |

### Workflow

1. **Feature Development**: Create `feature/your-feature` → Auto-deploys to DEV
2. **Integration Testing**: Merge to `development` → Auto-deploys to SIT
3. **Pre-Production**: Create `release/v1.0.0` → Auto-deploys to UAT
4. **Production**: Merge release to `main` → **Requires manual approval** → Deploys to PRD

### Manual Approval for Production

Production deployments require approval from designated reviewers:

1. Configure GitHub Environment: **Settings → Environments → production**
2. Add required reviewers
3. Set environment protection rules

See [`docs/BRANCH_PROTECTION.md`](./docs/BRANCH_PROTECTION.md) for detailed setup.

## 🧪 Environment Details

| Environment | Purpose | Warehouse | Data Volume | Retention |
|-------------|---------|-----------|-------------|-----------|
| **DEV** | Feature development & experimentation | XS | 1K records | 1 day |
| **SIT** | Integration testing | Small | 5K records | 1 day |
| **UAT** | Pre-production validation | Medium | 10K records | 3 days |
| **PRD** | Production workloads | Large | Production data | 7 days |

### Snowflake Objects Created per Environment

- **Databases**: `{ENV}_RAW_DB`, `{ENV}_ML_DB`
- **Schemas**: `PIPELINES`, `FEATURES`, `OUTPUT`
- **Stages**: `ML_CODE_STAGE`, `MODELS_STAGE`
- **Tables**: `CUSTOMERS` (raw), `CUSTOMER_FEATURES` (feature store), `PREDICTIONS` (output)
- **Roles**: `ML_{ENV}_ROLE`

## 🔐 Security & Access Control

### Service Accounts

Each environment uses a separate role for isolation:

- `ML_DEV_ROLE` - Full access to DEV
- `ML_SIT_ROLE` - Full access to SIT
- `ML_UAT_ROLE` - Full access to UAT
- `ML_PRD_ROLE` - Controlled access to PRD (read-only on raw data)
- `ML_CICD_ROLE` - Inherits all roles for CI/CD deployments

### Creating CI/CD Service Account

```sql
USE ROLE ACCOUNTADMIN;

-- Generate key-pair locally first:
-- openssl genrsa -out snowflake_key.pem 2048
-- openssl rsa -in snowflake_key.pem -pubout -out snowflake_key.pub

CREATE USER github_actions_user
    RSA_PUBLIC_KEY = '<paste_public_key_content>'
    DEFAULT_ROLE = ML_CICD_ROLE
    MUST_CHANGE_PASSWORD = FALSE;

GRANT ROLE ML_CICD_ROLE TO USER github_actions_user;
```

## 🛠 Local Development

### Setup

```bash
# Clone repository
git clone <repo_url>
cd MLOps_example

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Test Locally

```bash
# Set environment variables
export SNOWFLAKE_ACCOUNT="<your_account>"
export SNOWFLAKE_USER="<your_user>"
export SNOWFLAKE_PRIVATE_KEY="<your_private_key>"
export SNOWFLAKE_ROLE="ML_DEV_ROLE"
export SNOWFLAKE_WAREHOUSE="DEV_WH_XS"
export SNOWFLAKE_DATABASE="DEV_ML_DB"
export SNOWFLAKE_SCHEMA="PIPELINES"

# Run deployment script
python scripts/deploy_pipeline.py DEV
```

## 📊 Monitoring & Validation

### Check DAG Status

```sql
-- View deployed DAGs
SHOW TASKS IN SCHEMA DEV_ML_DB.PIPELINES;

-- Check DAG execution history
SELECT *
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
    SCHEDULED_TIME_RANGE_START => DATEADD('day', -7, CURRENT_TIMESTAMP())
))
WHERE NAME LIKE 'ML_RETRAINING_PIPELINE%'
ORDER BY SCHEDULED_TIME DESC;
```

### Monitor Predictions (PRD only)

```sql
USE SCHEMA PRD_ML_DB.OUTPUT;

-- Recent predictions
SELECT * FROM RECENT_PREDICTIONS LIMIT 100;

-- Prediction statistics
SELECT * FROM PREDICTION_STATS;
```

## 📚 Key Components

### 1. ML Logic (`src/ml_logic.py`)

Three main functions:

- `feature_engineering_task()` - Creates Feature Store with Entity and Feature View
- `model_training_task()` - Trains and registers model in Model Registry
- `inference_task()` - Runs batch predictions

### 2. Deployment Script (`scripts/deploy_pipeline.py`)

- Reads environment config from `config/environments.yml`
- Creates Snowpark session with key-pair auth
- Defines DAG with three tasks and dependencies
- Deploys to Snowflake using DAGOperation API

### 3. CI/CD Workflow (`.github/workflows/snowflake_ml_deploy.yml`)

- Triggers on push to `feature/**`, `development`, `release/**`, `main`
- Determines target environment based on branch
- Uploads Python code to Snowflake stage
- Executes deployment script
- Requires manual approval for production

## ⚠️ Limitations & Recommendations for Production

This is an **example/reference implementation** designed for learning and demonstration. For production-grade MLOps, consider implementing:

### 🔴 Critical Gaps

1. **No Automated Testing**
   - ❌ Missing unit tests for ML logic
   - ❌ No integration tests for Snowflake connectivity
   - ❌ No data validation tests
   - 💡 **Recommendation**: Add pytest with Snowpark testing, data quality checks (Great Expectations), and model validation tests

2. **No Model Validation Gates**
   - ❌ Models deploy without performance validation
   - ❌ No A/B testing or champion/challenger comparison
   - 💡 **Recommendation**: Implement model performance thresholds, drift detection, and automated rollback on degradation

3. **Limited Monitoring & Observability**
   - ❌ No model performance monitoring in production
   - ❌ No drift detection (data/concept drift)
   - ❌ No alerting on pipeline failures
   - 💡 **Recommendation**: Integrate with monitoring tools (DataDog, Evidently AI), add custom metrics tables, implement SLO/SLA tracking

4. **No Rollback Strategy**
   - ❌ Failed deployments require manual intervention
   - ❌ No versioning for DAG definitions
   - 💡 **Recommendation**: Implement blue-green deployments, maintain model version history, automated rollback on failure

### 🟡 Important Enhancements

5. **Basic Error Handling**
   - ⚠️ Limited exception handling in ML logic
   - ⚠️ No retry logic for transient failures
   - 💡 **Recommendation**: Add comprehensive error handling, implement exponential backoff, dead letter queues for failed records

6. **Simplified Feature Engineering**
   - ⚠️ Basic feature transformations only
   - ⚠️ No feature validation or schema enforcement
   - 💡 **Recommendation**: Implement feature contracts, add data quality checks, use Snowflake's data quality functions

7. **Single Model Architecture**
   - ⚠️ Only supports one model at a time
   - ⚠️ No ensemble or multi-model support
   - 💡 **Recommendation**: Support model ensembles, A/B testing infrastructure, shadow mode deployments

8. **Limited Security Hardening**
   - ⚠️ Service account uses single key-pair
   - ⚠️ No secrets rotation policy
   - ⚠️ No audit logging for model changes
   - 💡 **Recommendation**: Implement secrets rotation, enable Snowflake audit logs, add change management tracking

9. **No Cost Optimization**
   - ⚠️ Warehouses may run longer than needed
   - ⚠️ No automatic scaling based on workload
   - 💡 **Recommendation**: Implement auto-suspend policies, use query tags for cost attribution, optimize warehouse sizing

10. **Documentation & Governance**
    - ⚠️ No model cards or documentation
    - ⚠️ Limited lineage tracking
    - ⚠️ No compliance/regulatory considerations
    - 💡 **Recommendation**: Implement model cards, use Snowflake's object tagging for lineage, add compliance metadata

### 🟢 Nice-to-Have Features

11. **Advanced ML Features**
    - Feature store versioning and time-travel
    - Hyperparameter tuning automation
    - Online feature serving (if needed)
    - Model explainability (SHAP, LIME)

12. **Developer Experience**
    - Pre-commit hooks for code quality
    - Local development environment with Docker
    - Jupyter notebooks for experimentation
    - VS Code/Cursor integration guides

13. **Advanced CI/CD**
    - Canary deployments
    - Progressive rollouts
    - Automated performance benchmarking
    - Integration with Jira/project management

## 🤝 Contributing

This is an example repository for learning purposes. Feel free to fork and adapt to your needs!

## 📄 License

This example is provided as-is for educational purposes.

## 🙋 Support & Resources

- [Snowflake ML Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-ml/index)
- [Snowflake Feature Store](https://docs.snowflake.com/en/developer-guide/snowpark-ml/feature-store/overview)
- [Snowflake Model Registry](https://docs.snowflake.com/en/developer-guide/snowpark-ml/model-registry/overview)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

**Last Updated**: 2025-11-25  
**Version**: 1.0  
**Snowflake ML SDK**: Compatible with latest Snowpark ML Python SDK

