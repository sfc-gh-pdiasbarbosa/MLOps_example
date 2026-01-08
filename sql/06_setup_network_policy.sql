-- ============================================================================
-- Network Policy Setup for GitHub Actions CI/CD
-- ============================================================================
-- Description: Configures network access for GitHub Actions runners
-- Execute as: SECURITYADMIN or ACCOUNTADMIN
-- 
-- IMPORTANT: Review and adjust based on your organization's existing
-- network policies before executing.
-- ============================================================================

USE ROLE SECURITYADMIN;

-- ============================================================================
-- OPTION 1: Create a dedicated network policy for CI/CD
-- Use this if you want a separate policy for the CI/CD service account
-- ============================================================================

-- Create network rule for GitHub Actions (if not already exists)
-- Note: Your organization may already have this rule (e.g., GITHUBACTIONS_GLOBAL)
CREATE NETWORK RULE IF NOT EXISTS GITHUB_ACTIONS_RULE
    MODE = INGRESS
    TYPE = HOST_PORT
    VALUE_LIST = (
        -- GitHub Actions uses Azure IP ranges
        -- These are examples - check https://api.github.com/meta for current ranges
        'github.com:443',
        'api.github.com:443'
    )
    COMMENT = 'Network rule for GitHub Actions runners';

-- Create network policy using the rule
CREATE NETWORK POLICY IF NOT EXISTS ML_CICD_NETWORK_POLICY
    ALLOWED_NETWORK_RULE_LIST = ('GITHUB_ACTIONS_RULE')
    COMMENT = 'Network policy for ML pipeline CI/CD deployments';

-- Apply policy to the CI/CD service account user
ALTER USER github_actions_user SET NETWORK_POLICY = ML_CICD_NETWORK_POLICY;

-- ============================================================================
-- OPTION 2: Add GitHub rule to existing network policy
-- Use this if you have an existing policy you want to extend
-- ============================================================================

-- Uncomment and modify the following if you have an existing policy:

-- -- First, check your existing policy
-- DESCRIBE NETWORK POLICY <YOUR_EXISTING_POLICY_NAME>;

-- -- Add GitHub Actions network rule to existing policy
-- -- This preserves existing ALLOWED_IP_LIST
-- ALTER NETWORK POLICY <YOUR_EXISTING_POLICY_NAME> SET
--     ALLOWED_NETWORK_RULE_LIST = ('GITHUBACTIONS_GLOBAL');

-- -- If you need to set both IPs and rules (preserving existing IPs):
-- ALTER NETWORK POLICY <YOUR_EXISTING_POLICY_NAME> SET
--     ALLOWED_IP_LIST = (
--         -- Your existing IPs (copy from DESCRIBE output)
--         '10.0.0.0/8',
--         '192.168.1.0/24'
--         -- ... add all existing IPs here
--     ),
--     ALLOWED_NETWORK_RULE_LIST = ('GITHUBACTIONS_GLOBAL');

-- ============================================================================
-- OPTION 3: Permissive policy for testing (NOT for production!)
-- ============================================================================

-- Uncomment for quick testing only - allows all IPs
-- CREATE OR REPLACE NETWORK POLICY ML_CICD_NETWORK_POLICY_TESTING
--     ALLOWED_IP_LIST = ('0.0.0.0/0')
--     COMMENT = 'TESTING ONLY - Permissive policy - RESTRICT BEFORE PRODUCTION';
-- 
-- ALTER USER github_actions_user SET NETWORK_POLICY = ML_CICD_NETWORK_POLICY_TESTING;

-- ============================================================================
-- OPTION 4: Use existing organization-wide GitHub rule
-- ============================================================================

-- If your organization already has a GitHub Actions network rule,
-- create a policy that uses it:

-- CREATE NETWORK POLICY IF NOT EXISTS ML_CICD_NETWORK_POLICY
--     ALLOWED_NETWORK_RULE_LIST = ('GITHUBACTIONS_GLOBAL')  -- Your existing rule name
--     COMMENT = 'Network policy for ML pipeline CI/CD using org GitHub rule';
-- 
-- ALTER USER github_actions_user SET NETWORK_POLICY = ML_CICD_NETWORK_POLICY;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Show all network policies
SHOW NETWORK POLICIES;

-- Show network rules
SHOW NETWORK RULES;

-- Check what policy is applied to the CI/CD user
DESCRIBE USER github_actions_user;

-- Test: Check if a specific IP would be allowed
-- SELECT SYSTEM$ALLOWLIST_PRIVATELINK_IPS();

SELECT 'Network Policy Setup Complete!' AS STATUS;
SELECT 'Verify the CI/CD user has the correct policy attached' AS NEXT_STEP;

