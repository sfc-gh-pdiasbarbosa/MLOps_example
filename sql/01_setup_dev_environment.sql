-- ============================================================================
-- DEV Environment Setup for ML Pipeline
-- ============================================================================
-- Description: Creates all Snowflake objects for Development environment
-- Execute as: ACCOUNTADMIN or role with appropriate privileges
-- ============================================================================

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE DEV_WH_XS;

-- ============================================================================
-- 1. RAW DATA DATABASE & OBJECTS
-- ============================================================================

CREATE DATABASE IF NOT EXISTS DEV_RAW_DB
    COMMENT = 'Development - Raw data source database';

USE DATABASE DEV_RAW_DB;

CREATE SCHEMA IF NOT EXISTS PUBLIC
    COMMENT = 'Raw data schema for development';

-- Sample raw data table (customers)
-- Adjust columns based on your actual data model
CREATE OR REPLACE TABLE DEV_RAW_DB.PUBLIC.CUSTOMERS (
    CUSTOMER_ID VARCHAR(50) PRIMARY KEY,
    CUSTOMER_NAME VARCHAR(200),
    AGE INTEGER,
    ACCOUNT_BALANCE DECIMAL(18,2),
    TENURE_MONTHS INTEGER,
    NUM_PRODUCTS INTEGER,
    HAS_CREDIT_CARD BOOLEAN,
    IS_ACTIVE_MEMBER BOOLEAN,
    TARGET_LABEL INTEGER,  -- 1 = churned, 0 = retained
    LAST_UPDATED TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'DEV: Raw customer data for churn prediction';

-- ============================================================================
-- 2. ML WORKLOAD DATABASE & SCHEMAS
-- ============================================================================

CREATE DATABASE IF NOT EXISTS DEV_ML_DB
    COMMENT = 'Development - ML pipeline database';

USE DATABASE DEV_ML_DB;

-- Schema for DAG Tasks and Stored Procedures
CREATE SCHEMA IF NOT EXISTS PIPELINES
    COMMENT = 'DEV: Contains ML pipeline tasks and DAG definitions';

-- Schema for Feature Store
CREATE SCHEMA IF NOT EXISTS FEATURES
    COMMENT = 'DEV: Feature Store objects and feature views';

-- Schema for Model Outputs
CREATE SCHEMA IF NOT EXISTS OUTPUT
    COMMENT = 'DEV: ML inference outputs and predictions';

-- ============================================================================
-- 3. STAGES
-- ============================================================================

USE SCHEMA DEV_ML_DB.PIPELINES;

-- Stage for Python code artifacts
CREATE STAGE IF NOT EXISTS ML_CODE_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'DEV: Storage for Python ML logic files';

-- Stage for model artifacts
CREATE STAGE IF NOT EXISTS MODELS_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'DEV: Storage for trained ML models';

-- ============================================================================
-- 4. OUTPUT TABLES
-- ============================================================================

USE SCHEMA DEV_ML_DB.OUTPUT;

-- Predictions output table
CREATE TABLE IF NOT EXISTS PREDICTIONS (
    CUSTOMER_ID VARCHAR(50),
    PREDICTION INTEGER,
    PREDICTION_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    MODEL_VERSION VARCHAR(50),
    CONFIDENCE_SCORE DECIMAL(5,4)
)
COMMENT = 'DEV: ML model prediction outputs';

-- ============================================================================
-- 5. SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Insert sample data into raw customers table
USE SCHEMA DEV_RAW_DB.PUBLIC;

INSERT INTO CUSTOMERS (CUSTOMER_ID, CUSTOMER_NAME, AGE, ACCOUNT_BALANCE, TENURE_MONTHS, NUM_PRODUCTS, HAS_CREDIT_CARD, IS_ACTIVE_MEMBER, TARGET_LABEL)
SELECT 
    'CUST_' || SEQ4() AS CUSTOMER_ID,
    'Customer ' || SEQ4() AS CUSTOMER_NAME,
    UNIFORM(18, 75, RANDOM()) AS AGE,
    UNIFORM(0, 100000, RANDOM()) AS ACCOUNT_BALANCE,
    UNIFORM(0, 120, RANDOM()) AS TENURE_MONTHS,
    UNIFORM(1, 4, RANDOM()) AS NUM_PRODUCTS,
    CASE WHEN UNIFORM(0, 1, RANDOM()) = 1 THEN TRUE ELSE FALSE END AS HAS_CREDIT_CARD,
    CASE WHEN UNIFORM(0, 1, RANDOM()) = 1 THEN TRUE ELSE FALSE END AS IS_ACTIVE_MEMBER,
    CASE WHEN UNIFORM(0, 10, RANDOM()) > 8 THEN 1 ELSE 0 END AS TARGET_LABEL
FROM TABLE(GENERATOR(ROWCOUNT => 1000));

-- ============================================================================
-- 6. ROLE & TASK PRIVILEGES
-- ============================================================================
-- Grant EXECUTE TASK privilege to allow the role to run tasks
-- Replace 'DEV_ML_ROLE' with your actual role name

-- Create a role for ML pipeline operations (if not exists)
CREATE ROLE IF NOT EXISTS DEV_ML_ROLE
    COMMENT = 'Role for DEV ML pipeline operations';

-- Grant account-level EXECUTE TASK privilege
-- This is REQUIRED to deploy and run tasks/DAGs
GRANT EXECUTE TASK ON ACCOUNT TO ROLE DEV_ML_ROLE;
GRANT EXECUTE MANAGED TASK ON ACCOUNT TO ROLE DEV_ML_ROLE;

-- Grant usage on warehouse
GRANT USAGE ON WAREHOUSE DEV_WH_XS TO ROLE DEV_ML_ROLE;

-- Grant database privileges
GRANT USAGE ON DATABASE DEV_RAW_DB TO ROLE DEV_ML_ROLE;
GRANT USAGE ON DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;

-- Grant schema privileges
GRANT USAGE ON ALL SCHEMAS IN DATABASE DEV_RAW_DB TO ROLE DEV_ML_ROLE;
GRANT USAGE ON ALL SCHEMAS IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;

-- Grant object privileges on RAW database
GRANT SELECT ON ALL TABLES IN DATABASE DEV_RAW_DB TO ROLE DEV_ML_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA DEV_RAW_DB.PUBLIC TO ROLE DEV_ML_ROLE;
GRANT SELECT ON FUTURE TABLES IN DATABASE DEV_RAW_DB TO ROLE DEV_ML_ROLE;

-- Grant object privileges on ML database
GRANT ALL PRIVILEGES ON ALL SCHEMAS IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;
GRANT ALL PRIVILEGES ON ALL TABLES IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;
GRANT ALL PRIVILEGES ON ALL STAGES IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;
GRANT ALL PRIVILEGES ON ALL VIEWS IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;
GRANT ALL PRIVILEGES ON ALL PROCEDURES IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;
GRANT ALL PRIVILEGES ON ALL TASKS IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;

-- Grant future privileges on ML database
GRANT ALL PRIVILEGES ON FUTURE TABLES IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;
GRANT ALL PRIVILEGES ON FUTURE STAGES IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;
GRANT ALL PRIVILEGES ON FUTURE TASKS IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;
GRANT ALL PRIVILEGES ON FUTURE PROCEDURES IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;
GRANT ALL PRIVILEGES ON FUTURE VIEWS IN DATABASE DEV_ML_DB TO ROLE DEV_ML_ROLE;

-- Grant CREATE privileges needed for Feature Store
GRANT CREATE DYNAMIC TABLE ON SCHEMA DEV_ML_DB.FEATURES TO ROLE DEV_ML_ROLE;
GRANT CREATE VIEW ON SCHEMA DEV_ML_DB.FEATURES TO ROLE DEV_ML_ROLE;
GRANT CREATE TAG ON SCHEMA DEV_ML_DB.FEATURES TO ROLE DEV_ML_ROLE;
GRANT CREATE TABLE ON SCHEMA DEV_ML_DB.FEATURES TO ROLE DEV_ML_ROLE;

-- Grant CREATE privileges on PIPELINES schema for stored procedures
GRANT CREATE PROCEDURE ON SCHEMA DEV_ML_DB.PIPELINES TO ROLE DEV_ML_ROLE;
GRANT CREATE TASK ON SCHEMA DEV_ML_DB.PIPELINES TO ROLE DEV_ML_ROLE;
GRANT CREATE STAGE ON SCHEMA DEV_ML_DB.PIPELINES TO ROLE DEV_ML_ROLE;

-- Grant CREATE privileges on OUTPUT schema
GRANT CREATE TABLE ON SCHEMA DEV_ML_DB.OUTPUT TO ROLE DEV_ML_ROLE;

-- ============================================================================
-- IMPORTANT: Grant the role to your CI/CD user
-- ============================================================================
-- Uncomment and replace with your actual GitHub Actions user:
-- GRANT ROLE DEV_ML_ROLE TO USER github_actions_user;
--
-- Or if using your personal account for testing:
-- GRANT ROLE DEV_ML_ROLE TO USER your_username;

-- Also ensure the role can be used by the current user
GRANT ROLE DEV_ML_ROLE TO ROLE ACCOUNTADMIN;
GRANT ROLE DEV_ML_ROLE TO ROLE SYSADMIN;

-- ============================================================================
-- 7. VERIFY SETUP
-- ============================================================================

SHOW DATABASES LIKE 'DEV%';
SHOW SCHEMAS IN DATABASE DEV_ML_DB;
SHOW STAGES IN SCHEMA DEV_ML_DB.PIPELINES;
SHOW TABLES IN SCHEMA DEV_ML_DB.OUTPUT;

SELECT 'DEV Environment Setup Complete!' AS STATUS,
       COUNT(*) AS SAMPLE_RECORDS 
FROM DEV_RAW_DB.PUBLIC.CUSTOMERS;

