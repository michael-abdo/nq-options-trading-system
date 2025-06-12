# API Key Security Best Practices

## 🔐 How to Prevent API Key Exposure

Your Databento API key was previously exposed in a public repository. Here's how to prevent this from happening again:

## ✅ Current Security Measures (Already Implemented)

### 1. `.env` File Protection
- ✅ **API keys stored in `.env` file** (not in source code)
- ✅ **`.env` added to `.gitignore`** (line 53)
- ✅ **Template provided** (`.env.example`)

### 2. Environment Variable Loading
```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('DATABENTO_API_KEY')
```

### 3. Git Ignore Configuration
```gitignore
# Environment variables
.env
.env.local
.env.development
.env.test
.env.production
```

## 🚨 Additional Security Measures to Implement

### 1. Pre-commit Hooks (Recommended)
Install git hooks to scan for API keys before committing:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
EOF

# Install hooks
pre-commit install
```

### 2. Secret Scanning Tools

**Option A: GitHub Secret Scanning (Free)**
- Enable in repository settings
- Automatically scans commits for API keys
- Sends alerts when secrets detected

**Option B: Local scanning with git-secrets**
```bash
# Install git-secrets
brew install git-secrets

# Set up git-secrets for this repo
git secrets --install
git secrets --register-aws
git secrets --add 'db-[A-Za-z0-9]{26}'  # Databento key pattern
```

### 3. Environment-Specific Configuration
```bash
# Development environment
cp .env.example .env.development
# Edit with development keys

# Production environment
cp .env.example .env.production
# Edit with production keys

# Use different files per environment
```

### 4. Key Rotation Strategy
```bash
# Set up regular key rotation (every 90 days)
# 1. Generate new API key in Databento dashboard
# 2. Update .env file
# 3. Test new key
# 4. Revoke old key
# 5. Update team members
```

## 🔍 How to Check for Exposed Keys

### 1. Repository History Scan
```bash
# Scan entire git history for API keys
git log --all --grep="db-" --oneline
git log --all -S "DATABENTO_API_KEY" --oneline

# If found, you MUST:
# 1. Revoke the exposed key immediately
# 2. Generate new key
# 3. Consider repository as compromised
```

### 2. GitHub Advanced Security
- Enable dependency scanning
- Enable code scanning
- Review security advisories

## 📋 Emergency Response Checklist

If API key is exposed:
- [ ] **Immediately revoke exposed key** in Databento dashboard
- [ ] **Generate new API key**
- [ ] **Update `.env` file** with new key
- [ ] **Test new key functionality**
- [ ] **Review git history** for other potential exposures
- [ ] **Consider key rotation for other services**
- [ ] **Implement additional security measures**

## 🛡️ Prevention Checklist

Before every commit:
- [ ] **Run git status** - check what files are being committed
- [ ] **Review diff** - `git diff --cached` to see exact changes
- [ ] **Never commit `.env`** files
- [ ] **Use `.env.example`** for templates
- [ ] **Set up pre-commit hooks**
- [ ] **Enable secret scanning**

## 💡 Best Practices Summary

### DO:
- ✅ Store API keys in `.env` files
- ✅ Add `.env` to `.gitignore`
- ✅ Use environment variables in code
- ✅ Provide `.env.example` templates
- ✅ Rotate keys regularly
- ✅ Use pre-commit hooks
- ✅ Enable GitHub secret scanning

### DON'T:
- ❌ Hardcode API keys in source code
- ❌ Commit `.env` files to git
- ❌ Share API keys in chat/email
- ❌ Use production keys in development
- ❌ Leave default/test keys in code
- ❌ Ignore security warnings

## 🔧 Implementation Commands

```bash
# 1. Verify current security
git check-ignore .env                    # Should output: .env
grep -r "db-" . --exclude-dir=.git      # Should only find .env

# 2. Set up pre-commit hooks
pip install pre-commit
pre-commit install

# 3. Enable GitHub secret scanning
# Go to: Settings > Security & analysis > Secret scanning

# 4. Test security
echo "db-test-key-123456789012345678" > test-key.txt
git add test-key.txt
git commit -m "test"  # Should be blocked by pre-commit
```

## 📚 Resources

- [Databento API Security](https://docs.databento.com/security)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [Git Secrets Tool](https://github.com/awslabs/git-secrets)
- [Pre-commit Hooks](https://pre-commit.com/)

---

**Remember**: Security is not a one-time setup. It requires ongoing vigilance and regular reviews of your practices.
