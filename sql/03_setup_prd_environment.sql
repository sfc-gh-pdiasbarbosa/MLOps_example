-- ============================================================================
-- PRD Environment Setup for ML Pipeline
-- ============================================================================
-- Description: Creates all Snowflake objects for Production environment
-- Execute as: ACCOUNTADMIN or role with appropriate privileges
-- WARNING: Production environment - review carefully before execution
-- ============================================================================

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE PRD_WH_L;

-- ============================================================================
-- 1. RAW DATA DATABASE & OBJECTS
-- ============================================================================

CREATE DATABASE IF NOT EXISTS PRD_RAW_DB
    COMMENT = 'PRODUCTION - Raw data source database';

USE DATABASE PRD_RAW_DB;

CREATE SCHEMA IF NOT EXISTS PUBLIC
    COMMENT = 'Raw data schema for production';

-- Sample raw data table (customers)
-- NOTE: In production, this table likely already exists or is populated via data pipeline
CREATE TABLE IF NOT EXISTS PRD_RAW_DB.PUBLIC.CUSTOMERS (
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
COMMENT = 'PRODUCTION: Raw customer data for churn prediction';

-- ============================================================================
-- 2. ML WORKLOAD DATABASE & SCHEMAS
-- ============================================================================

CREATE DATABASE IF NOT EXISTS PRD_ML_DB
    COMMENT = 'PRODUCTION - ML pipeline database';

USE DATABASE PRD_ML_DB;

-- Schema for DAG Tasks and Stored Procedures
CREATE SCHEMA IF NOT EXISTS PIPELINES
    COMMENT = 'PRD: Contains ML pipeline tasks and DAG definitions';

-- Schema for Feature Store
CREATE SCHEMA IF NOT EXISTS FEATURES
    COMMENT = 'PRD: Feature Store objects and feature views';

-- Schema for Model Outputs
CREATE SCHEMA IF NOT EXISTS OUTPUT
    COMMENT = 'PRD: ML inference outputs and predictions';

-- ============================================================================
-- 3. STAGES
-- ============================================================================

USE SCHEMA PRD_ML_DB.PIPELINES;

-- Stage for Python code artifacts
CREATE STAGE IF NOT EXISTS ML_CODE_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'PRD: Storage for Python ML logic files';

-- Stage for model artifacts
CREATE STAGE IF NOT EXISTS MODELS_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'PRD: Storage for trained ML models';

-- ============================================================================
-- 4. OUTPUT TABLES
-- ============================================================================

USE SCHEMA PRD_ML_DB.OUTPUT;

-- Predictions output table with time travel and fail-safe
CREATE TABLE IF NOT EXISTS PREDICTIONS (
    CUSTOMER_ID VARCHAR(50),
    PREDICTION INTEGER,
    PREDICTION_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    MODEL_VERSION VARCHAR(50),
    CONFIDENCE_SCORE DECIMAL(5,4)
)
DATA_RETENTION_TIME_IN_DAYS = 7
COMMENT = 'PRODUCTION: ML model prediction outputs';

-- Optional: Create an audit/history table for production tracking
CREATE TABLE IF NOT EXISTS PREDICTIONS_HISTORY (
    CUSTOMER_ID VARCHAR(50),
    PREDICTION INTEGER,
    PREDICTION_TIMESTAMP TIMESTAMP_NTZ,
    MODEL_VERSION VARCHAR(50),
    CONFIDENCE_SCORE DECIMAL(5,4),
    ARCHIVED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'PRODUCTION: Historical archive of predictions';

-- ============================================================================
-- 5. MONITORING VIEWS (Production Only)
-- ============================================================================

USE SCHEMA PRD_ML_DB.OUTPUT;

-- View for recent predictions
CREATE OR REPLACE VIEW RECENT_PREDICTIONS AS
SELECT 
    CUSTOMER_ID,
    PREDICTION,
    PREDICTION_TIMESTAMP,
    MODEL_VERSION,
    CONFIDENCE_SCORE
FROM PREDICTIONS
WHERE PREDICTION_TIMESTAMP >= DATEADD(DAY, -7, CURRENT_TIMESTAMP())
ORDER BY PREDICTION_TIMESTAMP DESC;

-- View for prediction statistics
CREATE OR REPLACE VIEW PREDICTION_STATS AS
SELECT 
    DATE_TRUNC('DAY', PREDICTION_TIMESTAMP) AS PREDICTION_DATE,
    MODEL_VERSION,
    COUNT(*) AS TOTAL_PREDICTIONS,
    SUM(CASE WHEN PREDICTION = 1 THEN 1 ELSE 0 END) AS CHURN_PREDICTIONS,
    SUM(CASE WHEN PREDICTION = 0 THEN 1 ELSE 0 END) AS RETAINED_PREDICTIONS,
    AVG(CONFIDENCE_SCORE) AS AVG_CONFIDENCE,
    MIN(CONFIDENCE_SCORE) AS MIN_CONFIDENCE,
    MAX(CONFIDENCE_SCORE) AS MAX_CONFIDENCE
FROM PREDICTIONS
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- ============================================================================
-- 6. VERIFY SETUP
-- ============================================================================

SHOW DATABASES LIKE 'PRD%';
SHOW SCHEMAS IN DATABASE PRD_ML_DB;
SHOW STAGES IN SCHEMA PRD_ML_DB.PIPELINES;
SHOW TABLES IN SCHEMA PRD_ML_DB.OUTPUT;
SHOW VIEWS IN SCHEMA PRD_ML_DB.OUTPUT;

SELECT 'PRD Environment Setup Complete!' AS STATUS,
       COUNT(*) AS EXISTING_RECORDS 
FROM PRD_RAW_DB.PUBLIC.CUSTOMERS;

-- NOTE: Production data should be loaded through proper ETL pipelines
-- Do NOT run sample data generation in production

