-- ============================================================================
-- UAT Environment Setup for ML Pipeline
-- ============================================================================
-- Description: Creates all Snowflake objects for User Acceptance Test environment
-- Execute as: ACCOUNTADMIN or role with appropriate privileges
-- ============================================================================

USE ROLE ACCOUNTADMIN;

-- Create UAT Warehouse (Medium size - production-like scale)
CREATE WAREHOUSE IF NOT EXISTS UAT_WH_M
    WAREHOUSE_SIZE = 'MEDIUM'
    AUTO_SUSPEND = 180
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'UAT warehouse for ML pipelines - M size for pre-production validation';

USE WAREHOUSE UAT_WH_M;

-- ============================================================================
-- 1. RAW DATA DATABASE & OBJECTS
-- ============================================================================

CREATE DATABASE IF NOT EXISTS UAT_RAW_DB
    COMMENT = 'UAT - Raw data source database';

USE DATABASE UAT_RAW_DB;

CREATE SCHEMA IF NOT EXISTS PUBLIC
    COMMENT = 'Raw data schema for UAT';

-- Sample raw data table (customers)
CREATE OR REPLACE TABLE UAT_RAW_DB.PUBLIC.CUSTOMERS (
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
COMMENT = 'UAT: Raw customer data for churn prediction';

-- ============================================================================
-- 2. ML WORKLOAD DATABASE & SCHEMAS
-- ============================================================================

CREATE DATABASE IF NOT EXISTS UAT_ML_DB
    COMMENT = 'UAT - ML pipeline database';

USE DATABASE UAT_ML_DB;

-- Schema for DAG Tasks and Stored Procedures
CREATE SCHEMA IF NOT EXISTS PIPELINES
    COMMENT = 'UAT: Contains ML pipeline tasks and DAG definitions';

-- Schema for Feature Store
CREATE SCHEMA IF NOT EXISTS FEATURES
    COMMENT = 'UAT: Feature Store objects and feature views';

-- Schema for Model Outputs
CREATE SCHEMA IF NOT EXISTS OUTPUT
    COMMENT = 'UAT: ML inference outputs and predictions';

-- ============================================================================
-- 3. STAGES
-- ============================================================================

USE SCHEMA UAT_ML_DB.PIPELINES;

-- Stage for Python code artifacts
CREATE STAGE IF NOT EXISTS ML_CODE_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'UAT: Storage for Python ML logic files';

-- Stage for model artifacts
CREATE STAGE IF NOT EXISTS MODELS_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'UAT: Storage for trained ML models';

-- ============================================================================
-- 4. OUTPUT TABLES
-- ============================================================================

USE SCHEMA UAT_ML_DB.OUTPUT;

-- Predictions output table with production-like settings
CREATE TABLE IF NOT EXISTS PREDICTIONS (
    CUSTOMER_ID VARCHAR(50),
    PREDICTION INTEGER,
    PREDICTION_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    MODEL_VERSION VARCHAR(50),
    CONFIDENCE_SCORE DECIMAL(5,4)
)
DATA_RETENTION_TIME_IN_DAYS = 3
COMMENT = 'UAT: ML model prediction outputs';

-- Validation metrics table for UAT testing
CREATE TABLE IF NOT EXISTS UAT_VALIDATION_METRICS (
    TEST_RUN_ID VARCHAR(100),
    TEST_NAME VARCHAR(200),
    METRIC_NAME VARCHAR(100),
    METRIC_VALUE DECIMAL(18,6),
    TEST_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    STATUS VARCHAR(20),
    NOTES VARCHAR(1000)
)
COMMENT = 'UAT: Validation metrics for pre-production testing';

-- ============================================================================
-- 5. SAMPLE DATA (Production-like volume)
-- ============================================================================

-- Insert sample data into raw customers table (production-like volume)
USE SCHEMA UAT_RAW_DB.PUBLIC;

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
FROM TABLE(GENERATOR(ROWCOUNT => 10000));

-- ============================================================================
-- 6. MONITORING VIEWS (UAT-specific)
-- ============================================================================

USE SCHEMA UAT_ML_DB.OUTPUT;

-- View for recent predictions
CREATE OR REPLACE VIEW RECENT_PREDICTIONS AS
SELECT 
    CUSTOMER_ID,
    PREDICTION,
    PREDICTION_TIMESTAMP,
    MODEL_VERSION,
    CONFIDENCE_SCORE
FROM PREDICTIONS
WHERE PREDICTION_TIMESTAMP >= DATEADD(DAY, -3, CURRENT_TIMESTAMP())
ORDER BY PREDICTION_TIMESTAMP DESC;

-- View for test validation summary
CREATE OR REPLACE VIEW UAT_TEST_SUMMARY AS
SELECT 
    DATE_TRUNC('DAY', TEST_TIMESTAMP) AS TEST_DATE,
    TEST_NAME,
    STATUS,
    COUNT(*) AS TEST_COUNT,
    AVG(METRIC_VALUE) AS AVG_METRIC_VALUE
FROM UAT_VALIDATION_METRICS
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 2;

-- ============================================================================
-- 7. VERIFY SETUP
-- ============================================================================

SHOW DATABASES LIKE 'UAT%';
SHOW SCHEMAS IN DATABASE UAT_ML_DB;
SHOW STAGES IN SCHEMA UAT_ML_DB.PIPELINES;
SHOW TABLES IN SCHEMA UAT_ML_DB.OUTPUT;
SHOW VIEWS IN SCHEMA UAT_ML_DB.OUTPUT;

SELECT 'UAT Environment Setup Complete!' AS STATUS,
       COUNT(*) AS SAMPLE_RECORDS 
FROM UAT_RAW_DB.PUBLIC.CUSTOMERS;

SELECT '⚠️  UAT is for pre-production validation with production-like data volume' AS INFO;

