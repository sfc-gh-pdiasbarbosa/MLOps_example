-- ============================================================================
-- Warehouse Setup for ML Pipeline
-- ============================================================================
-- Description: Creates compute warehouses for each environment
-- Execute as: ACCOUNTADMIN or role with CREATE WAREHOUSE privilege
-- ============================================================================

USE ROLE ACCOUNTADMIN;

-- Development Warehouse (Extra Small)
CREATE WAREHOUSE IF NOT EXISTS DEV_WH_XS
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Development warehouse for ML pipelines - XS size for cost efficiency';

-- System Integration Test Warehouse (Small)
CREATE WAREHOUSE IF NOT EXISTS SIT_WH_S
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 120
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'SIT warehouse for ML pipelines - S size for integration testing';

-- Production Warehouse (Large)
CREATE WAREHOUSE IF NOT EXISTS PRD_WH_L
    WAREHOUSE_SIZE = 'LARGE'
    AUTO_SUSPEND = 300
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Production warehouse for ML pipelines - L size for production workloads';

-- Grant usage to appropriate roles (adjust as needed)
-- GRANT USAGE ON WAREHOUSE DEV_WH_XS TO ROLE ML_DEV_ROLE;
-- GRANT USAGE ON WAREHOUSE SIT_WH_S TO ROLE ML_SIT_ROLE;
-- GRANT USAGE ON WAREHOUSE PRD_WH_L TO ROLE ML_PRD_ROLE;

-- Verify warehouses created
SHOW WAREHOUSES LIKE '%_WH_%';

