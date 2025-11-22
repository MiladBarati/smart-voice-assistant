#!/bin/bash
# Script to check git status and push changes to GitHub

cd /home/milad/projects/pjsua-installation || cd "$(dirname "$0")"

echo "=== Current Directory ==="
pwd
echo ""

echo "=== Git Status ==="
git status
echo ""

echo "=== Checking for uncommitted changes ==="
if [ -n "$(git status --porcelain)" ]; then
    echo "Found uncommitted changes. Staging all changes..."
    git add .
    
    echo "Committing changes following GitCommitPractices.md guidelines..."
    git commit -m "docs: add git commit best practices guide"
    echo ""
fi

echo "=== Checking for unpushed commits ==="
git log origin/main..HEAD --oneline 2>/dev/null || git log origin/master..HEAD --oneline 2>/dev/null
echo ""

echo "=== Pushing to GitHub ==="
git push origin main 2>&1 || git push origin master 2>&1
echo ""

echo "=== Final Status ==="
git status

