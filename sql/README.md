# Snowflake ML Pipeline - SQL Setup Scripts

This directory contains SQL scripts to manually set up all required Snowflake objects for the ML pipeline across all environments.

## 📋 Overview

These scripts create databases, schemas, warehouses, stages, tables, and security roles needed for the customer churn prediction ML pipeline.

## 🚀 Quick Start

Execute the scripts in order in Snowsight:

1. **Warehouses** → `00_setup_warehouses.sql`
2. **DEV Environment** → `01_setup_dev_environment.sql`
3. **SIT Environment** → `02_setup_sit_environment.sql`
4. **UAT Environment** → `02b_setup_uat_environment.sql`
5. **PRD Environment** → `03_setup_prd_environment.sql`
6. **Security & Roles** → `04_setup_roles_and_grants.sql`
7. **Market Data (for Investment Strategy)** → `05_setup_market_data_tables.sql`

## 📁 Script Details

### 00_setup_warehouses.sql
Creates compute warehouses for each environment:
- `DEV_WH_XS` - Extra Small warehouse for development
- `SIT_WH_S` - Small warehouse for integration testing
- `PRD_WH_L` - Large warehouse for production

**Required Role:** `ACCOUNTADMIN` or role with `CREATE WAREHOUSE` privilege

---

### 01_setup_dev_environment.sql
Sets up the Development environment:
- **Databases:**
  - `DEV_RAW_DB` - Raw source data
  - `DEV_ML_DB` - ML workloads
- **Schemas:**
  - `PIPELINES` - DAG tasks and stored procedures
  - `FEATURES` - Feature Store objects
  - `OUTPUT` - Prediction outputs
- **Stages:**
  - `ML_CODE_STAGE` - Python code storage
  - `MODELS_STAGE` - Model artifacts storage
- **Tables:**
  - `CUSTOMERS` - Sample raw data (1,000 records generated)
  - `PREDICTIONS` - Model output table

**Required Role:** `ACCOUNTADMIN` or role with appropriate privileges

---

### 02_setup_sit_environment.sql
Sets up the System Integration Test environment:
- Same structure as DEV
- Uses `SIT_` prefix for all objects
- Includes 5,000 sample customer records for testing

**Required Role:** `ACCOUNTADMIN` or role with appropriate privileges

---

### 02b_setup_uat_environment.sql
Sets up the User Acceptance Test environment:
- Same structure as DEV/SIT
- Uses `UAT_` prefix for all objects
- Includes 10,000 sample customer records (production-like volume)
- Additional UAT validation metrics table
- Medium warehouse for production-like performance testing

**Required Role:** `ACCOUNTADMIN` or role with appropriate privileges

---

### 03_setup_prd_environment.sql
Sets up the Production environment:
- Same structure as DEV/SIT
- Uses `PRD_` prefix for all objects
- **Additional Features:**
  - Extended data retention (7 days)
  - Historical predictions archive table
  - Monitoring views for production observability
- **Note:** Does NOT generate sample data (production data should come from ETL pipelines)

**Required Role:** `ACCOUNTADMIN` or role with appropriate privileges

⚠️ **WARNING:** Review carefully before executing in production!

---

### 04_setup_roles_and_grants.sql
Creates security roles and grants permissions:

**Roles Created:**
- `ML_DEV_ROLE` - Development access
- `ML_SIT_ROLE` - Integration testing access
- `ML_UAT_ROLE` - Pre-production validation access
- `ML_PRD_ROLE` - Production pipeline execution
- `ML_CICD_ROLE` - CI/CD deployment (inherits all environment roles)

**Permissions:**
- DEV: Full access to all objects
- SIT: Full access to all objects
- PRD: Read-only on raw data, controlled write access to ML objects

**Required Role:** `SECURITYADMIN` or `ACCOUNTADMIN`

**Action Required:** Uncomment and update user assignments at the end of the script

---

### 05_setup_market_data_tables.sql
Sets up tables for the **Investment Strategy (non-ML) example**:
- **Tables:**
  - `MARKET_DATA` - Raw OHLCV price data with technical indicators
  - `TRADING_SIGNALS` - Strategy output signals (BUY/SELL/HOLD)
- **Stages:**
  - `STRATEGY_CODE_STAGE` - Strategy Python code
  - `STRATEGY_MODELS_STAGE` - Registered strategy artifacts
- **Sample Data:** 10 assets × 100 days of simulated price data

**Required Role:** `ACCOUNTADMIN` or role with appropriate privileges

**Note:** Run this AFTER the main environment setup scripts (00-04)

---

## 🔐 Security Configuration

### For CI/CD (GitHub Actions)

After running the scripts, you need to:

1. **Create a service account user:**
   ```sql
   USE ROLE ACCOUNTADMIN;
   CREATE USER github_actions_user
       RSA_PUBLIC_KEY = '<your_public_key>'
       DEFAULT_ROLE = ML_CICD_ROLE
       MUST_CHANGE_PASSWORD = FALSE;
   
   GRANT ROLE ML_CICD_ROLE TO USER github_actions_user;
   ```

2. **Configure GitHub Secrets:**
   - `SNOWFLAKE_ACCOUNT` - Your Snowflake account identifier
   - `SNOWFLAKE_USER` - `github_actions_user`
   - `SNOWFLAKE_PRIVATE_KEY` - Private key content
   - `SNOWFLAKE_ROLE` - `ML_CICD_ROLE`

### For Developers

Grant appropriate roles to user accounts:
```sql
GRANT ROLE ML_DEV_ROLE TO USER <developer_email>;
GRANT ROLE ML_SIT_ROLE TO USER <tester_email>;
GRANT ROLE ML_UAT_ROLE TO USER <uat_tester_email>;
```

---

## 🧪 Verification

After running each script, verify the setup:

```sql
-- Check databases
SHOW DATABASES LIKE 'DEV%';
SHOW DATABASES LIKE 'SIT%';
SHOW DATABASES LIKE 'UAT%';
SHOW DATABASES LIKE 'PRD%';

-- Check warehouses
SHOW WAREHOUSES LIKE '%_WH_%';

-- Check roles
SHOW ROLES LIKE 'ML_%';

-- Verify grants for a role
SHOW GRANTS TO ROLE ML_DEV_ROLE;
SHOW GRANTS TO ROLE ML_UAT_ROLE;

-- Check sample data
SELECT COUNT(*) FROM DEV_RAW_DB.PUBLIC.CUSTOMERS;
SELECT COUNT(*) FROM UAT_RAW_DB.PUBLIC.CUSTOMERS;
```

---

## 📊 Environment Summary

| Environment | Database | Warehouse | Purpose | Sample Data |
|-------------|----------|-----------|---------|-------------|
| DEV | `DEV_ML_DB` | `DEV_WH_XS` | Development & feature branches | 1,000 rows |
| SIT | `SIT_ML_DB` | `SIT_WH_S` | Integration testing | 5,000 rows |
| UAT | `UAT_ML_DB` | `UAT_WH_M` | Pre-production validation | 10,000 rows |
| PRD | `PRD_ML_DB` | `PRD_WH_L` | Production workloads | From ETL |

---

## 🔄 Pipeline Objects Created

The setup scripts prepare Snowflake for the following pipeline:

1. **Feature Engineering Task** → Reads from `RAW_DB.PUBLIC.CUSTOMERS` → Creates Feature Store in `ML_DB.FEATURES.CUSTOMER_FEATURES`
2. **Model Training Task** → Reads features → Trains model → Registers in Snowflake Model Registry
3. **Inference Task** → Loads model → Runs predictions → Saves to `ML_DB.OUTPUT.PREDICTIONS`

All tasks are orchestrated via Snowflake DAG (`ML_RETRAINING_PIPELINE`)

---

## 🛠 Customization

### Adjusting Customer Table Schema

The `CUSTOMERS` table schema is based on the churn prediction example. Modify the table definition in each environment script to match your data model:

```sql
CREATE OR REPLACE TABLE <ENV>_RAW_DB.PUBLIC.CUSTOMERS (
    -- Add your columns here
    CUSTOMER_ID VARCHAR(50) PRIMARY KEY,
    -- ... other fields ...
);
```

### Adjusting Warehouse Sizes

Modify warehouse sizes in `00_setup_warehouses.sql` based on your workload:
- DEV: `XSMALL` (cost-efficient for development)
- SIT: `SMALL` (adequate for testing)
- PRD: `LARGE` or higher (based on production volume)

---

## 📞 Support

For issues or questions:
1. Check Snowflake documentation: https://docs.snowflake.com
2. Review the GitHub Actions workflow: `.github/workflows/snowflake_ml_deploy.yml`
3. Check the deployment script: `scripts/deploy_pipeline.py`

---

## 🗑 Cleanup (Optional)

To remove all created objects (use with caution!):

```sql
-- DEV Environment
DROP DATABASE IF EXISTS DEV_RAW_DB CASCADE;
DROP DATABASE IF EXISTS DEV_ML_DB CASCADE;
DROP WAREHOUSE IF EXISTS DEV_WH_XS;

-- SIT Environment
DROP DATABASE IF EXISTS SIT_RAW_DB CASCADE;
DROP DATABASE IF EXISTS SIT_ML_DB CASCADE;
DROP WAREHOUSE IF EXISTS SIT_WH_S;

-- UAT Environment
DROP DATABASE IF EXISTS UAT_RAW_DB CASCADE;
DROP DATABASE IF EXISTS UAT_ML_DB CASCADE;
DROP WAREHOUSE IF EXISTS UAT_WH_M;

-- PRD Environment (⚠️ DANGER - Production!)
-- DROP DATABASE IF EXISTS PRD_RAW_DB CASCADE;
-- DROP DATABASE IF EXISTS PRD_ML_DB CASCADE;
-- DROP WAREHOUSE IF EXISTS PRD_WH_L;

-- Roles
DROP ROLE IF EXISTS ML_DEV_ROLE;
DROP ROLE IF EXISTS ML_SIT_ROLE;
DROP ROLE IF EXISTS ML_UAT_ROLE;
DROP ROLE IF EXISTS ML_PRD_ROLE;
DROP ROLE IF EXISTS ML_CICD_ROLE;
```

---

**Last Updated:** 2025-11-25  
**Version:** 1.0  
**Compatible with:** Snowflake ML Python SDK, Snowpark, Feature Store API

