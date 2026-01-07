# Branch Protection & Security Setup Guide

This guide explains how to configure GitHub branch protection rules and environment-based approvals to secure your ML pipeline deployments.

## 📋 Overview

The Enhanced GitFlow strategy requires:

1. **Branch Protection Rules** - Prevent direct commits and require reviews
2. **Environment Protection Rules** - Manual approval gates for production
3. **Status Checks** - Ensure CI passes before merging
4. **Separate Service Accounts** - Environment-specific credentials

## 🔒 Step 1: Configure Branch Protection Rules

### Protected Branches

Configure protection for the following branches:

- ✅ `main` (Production)
- ✅ `development` (System Integration Testing)
- ✅ `release/**` (User Acceptance Testing)

### Setup Instructions

1. **Navigate to Repository Settings**
   - Go to your GitHub repository
   - Click **Settings** → **Branches** → **Add branch protection rule**

2. **Configure `main` Branch Protection**

   **Branch name pattern**: `main`

   #### Required Settings:
   
   - ✅ **Require a pull request before merging**
     - ✅ Require approvals: **2** (recommended for production)
     - ✅ Dismiss stale pull request approvals when new commits are pushed
     - ✅ Require review from Code Owners (if using CODEOWNERS file)
   
   - ✅ **Require status checks to pass before merging**
     - ✅ Require branches to be up to date before merging
     - Status checks to require:
       - `test_and_deploy` (if you add testing steps)
       - Any other CI checks you implement
   
   - ✅ **Require conversation resolution before merging**
   
   - ✅ **Require signed commits** (optional but recommended)
   
   - ✅ **Do not allow bypassing the above settings**
   
   - ✅ **Restrict who can push to matching branches**
     - Add: Repository admins only (or specific maintainer team)
   
   - ❌ **Allow force pushes**: Disabled
   
   - ❌ **Allow deletions**: Disabled

   Click **Create** or **Save changes**

3. **Configure `development` Branch Protection**

   **Branch name pattern**: `development`

   #### Required Settings:
   
   - ✅ **Require a pull request before merging**
     - ✅ Require approvals: **1** (minimum)
     - ✅ Dismiss stale pull request approvals when new commits are pushed
   
   - ✅ **Require status checks to pass before merging**
   
   - ✅ **Require conversation resolution before merging**
   
   - ❌ **Allow force pushes**: Disabled
   
   - ❌ **Allow deletions**: Disabled

   Click **Create** or **Save changes**

4. **Configure `release/**` Branch Protection**

   **Branch name pattern**: `release/**`

   #### Required Settings:
   
   - ✅ **Require a pull request before merging**
     - ✅ Require approvals: **1** (minimum)
   
   - ✅ **Require status checks to pass before merging**
   
   - ❌ **Allow force pushes**: Disabled

   Click **Create** or **Save changes**

## 🎯 Step 2: Configure Environment Protection Rules

GitHub Environments provide deployment gates and approval workflows.

### Create Production Environment

1. **Navigate to Environments**
   - Go to **Settings** → **Environments**
   - Click **New environment**
   - Name: `production`
   - Click **Configure environment**

2. **Configure Protection Rules**

   #### Required reviewers:
   - ✅ Enable **Required reviewers**
   - Add reviewers (people or teams):
     - ML Lead
     - DevOps Engineer
     - Product Owner
   - Minimum: **2 reviewers** (recommended for production)

   #### Wait timer:
   - Optional: Set a wait timer (e.g., 5 minutes) to allow last-minute cancellation
   - Recommended: **0 minutes** (rely on reviewer judgment)

   #### Deployment branches:
   - ✅ **Selected branches**
   - Add rule: `main` only
   - This ensures only main branch can deploy to production

   #### Environment secrets (configure here):
   - `SNOWFLAKE_PRD_ROLE` (will be used instead of repository secret)

3. **Save Protection Rules**

### Create Non-Production Environment (Optional)

For DEV, SIT, UAT environments with less strict controls:

1. **Create environment**: `non-production`
2. **No required reviewers** (auto-approve)
3. **Deployment branches**: All branches
4. This allows feature branches to deploy without approval

## 🔑 Step 3: Configure Environment-Specific Secrets

Instead of using a single `SNOWFLAKE_ROLE` secret for all environments, use environment-specific roles for better security.

### Repository-Level Secrets

Navigate to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add the following secrets:

| Secret Name | Value | Notes |
|-------------|-------|-------|
| `SNOWFLAKE_ACCOUNT` | `myorg-myaccount` | See format below |
| `SNOWFLAKE_USER` | `github_actions_user` | Service account |
| `SNOWFLAKE_PRIVATE_KEY` | `-----BEGIN PRIVATE KEY-----...` | Full PEM content |
| `SNOWFLAKE_ROLE` | `ML_CICD_ROLE` | Fallback role |

#### Account Identifier Format

⚠️ **This is a common source of errors!**

| ✅ Correct | ❌ Wrong |
|-----------|----------|
| `myorg-myaccount` | `myorg-myaccount.snowflakecomputing.com` |
| `xy12345.us-east-1` | `https://xy12345.snowflakecomputing.com` |

**How to find your account identifier:**
1. Log into Snowsight
2. Look at URL: `https://app.snowflake.com/ORGNAME/ACCOUNTNAME/`
3. Your account = `ORGNAME-ACCOUNTNAME`

Or run in Snowflake:
```sql
SELECT CURRENT_ORGANIZATION_NAME() || '-' || CURRENT_ACCOUNT_NAME();
```

#### Private Key Format

The private key must be **unencrypted** (no passphrase). Generate with:

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out snowflake_key.p8 -nocrypt
openssl rsa -in snowflake_key.p8 -pubout -out snowflake_key.pub
```

The secret should contain the **entire file content** including headers:
```
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASC...
...multiple lines...
-----END PRIVATE KEY-----
```

#### Environment-Specific Roles (Optional)

For more granular access control:

```yaml
SNOWFLAKE_DEV_ROLE: ML_DEV_ROLE
SNOWFLAKE_SIT_ROLE: ML_SIT_ROLE
SNOWFLAKE_UAT_ROLE: ML_UAT_ROLE
SNOWFLAKE_PRD_ROLE: ML_PRD_ROLE
```

If not configured, the workflow falls back to `SNOWFLAKE_ROLE`.

### Environment-Level Secrets (Optional, More Secure)

For production, you can override at environment level:

1. Go to **Settings** → **Environments** → **production**
2. Add environment secrets:
   - `SNOWFLAKE_USER`: `github_actions_prd_user` (separate production user)
   - `SNOWFLAKE_PRIVATE_KEY`: `<production_specific_key>`
   - `SNOWFLAKE_PRD_ROLE`: `ML_PRD_ROLE`

This ensures production uses completely separate credentials.

## 🧪 Step 4: Test Your Setup

### Test Branch Protection

```bash
# This should FAIL (direct push to main blocked)
git checkout main
echo "test" >> test.txt
git add test.txt
git commit -m "Test direct push"
git push origin main
# Expected: Error - branch protection rules prevent direct push
```

### Test PR Workflow

```bash
# Create feature branch
git checkout -b feature/test-protection
echo "test" >> test.txt
git add test.txt
git commit -m "Test PR workflow"
git push origin feature/test-protection

# Create PR via GitHub UI
# Try to merge without approval - should be blocked
# Add approval - should allow merge
```

### Test Production Approval

```bash
# Create a release branch
git checkout development
git pull
git checkout -b release/v1.0.0
git push origin release/v1.0.0

# Deploy to UAT automatically (no approval needed)

# Create PR from release/v1.0.0 to main
# Try to merge - will trigger production environment
# Should require manual approval from designated reviewers
# After approval - deploys to production
```

## 📊 Step 5: Monitoring & Audit

### View Deployment History

- **Actions** → **All workflows** → Filter by environment
- Each production deployment shows:
  - Who approved
  - When approved
  - Deployment logs

### View Protection Rules

- **Settings** → **Branches** → See all protected branches
- **Settings** → **Environments** → See protection rules per environment

### Audit Log

For GitHub Enterprise:
- **Settings** → **Audit log** → Filter by:
  - Branch protection changes
  - Environment approvals
  - Secret access

## 🔧 Advanced Configuration

### CODEOWNERS File

Create `.github/CODEOWNERS` to automatically request reviews:

```bash
# Default owners for everything
* @ml-team-lead @devops-lead

# Specific owners for different parts
/src/ml_logic.py @data-scientist @ml-engineer
/sql/ @database-admin @devops-lead
/.github/workflows/ @devops-lead @platform-engineer
/config/ @ml-team-lead
```

### Status Checks (When You Add Tests)

Update workflow to create status checks:

```yaml
jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Unit Tests
        run: pytest tests/
      - name: Run Integration Tests
        run: pytest tests/integration/
  
  deploy:
    needs: test  # Deploy only if tests pass
    # ... rest of deployment
```

Then require `test` status check in branch protection.

## 🚨 Troubleshooting

### Issue: Can't push to protected branch

**Solution**: Create a PR instead of direct push

```bash
git checkout -b feature/my-changes
git push origin feature/my-changes
# Then create PR via GitHub UI
```

### Issue: Status checks not showing up

**Solution**: 
1. Run the workflow at least once
2. Go to branch protection settings
3. Refresh the status checks list
4. Select the required checks

### Issue: Approval not showing in Actions

**Solution**: 
1. Check environment is configured correctly
2. Verify workflow references correct environment name
3. Ensure `environment:` field matches environment name exactly

### Issue: Secrets not accessible

**Solution**:
1. Verify secret names match exactly (case-sensitive)
2. Check environment-level secrets override repository-level
3. Ensure service account has permissions in Snowflake

## 📚 Best Practices

1. ✅ **Minimum 2 approvers for production** - Reduces single point of failure
2. ✅ **Separate service accounts per environment** - Limits blast radius
3. ✅ **Regular key rotation** - Schedule quarterly key updates
4. ✅ **Document exceptions** - When bypassing protection, document why
5. ✅ **Review audit logs** - Monthly review of deployments and approvals
6. ✅ **Test in lower environments** - Always test in DEV/SIT before UAT/PRD
7. ✅ **Automate where possible** - Use status checks instead of manual verification
8. ✅ **Keep protection rules in sync** - Document any changes to protection rules

## 🔗 Additional Resources

- [GitHub Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [GitHub Actions Security Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [CODEOWNERS Documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)

---

**Last Updated**: 2025-11-25  
**Version**: 1.0

