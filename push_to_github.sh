#!/bin/bash
set -e
TOKEN=$(cat /home/toolbox/.github_token)
TMPDIR=/tmp/toolbox_github_sync_$$
git clone --depth=1 https://$TOKEN@github.com/moooniia/bangong02.git $TMPDIR
rsync -av --delete   --exclude='.git'   --exclude='outputs/'   --exclude='uploads/'   --exclude='*.env'   --exclude='__pycache__/'   --exclude='*.pyc'   /home/toolbox/ $TMPDIR/server/
cd $TMPDIR
git config user.email "server@toolbox" 
git config user.name "Toolbox Server"
git add -A
if git diff --cached --quiet; then
  echo "No changes to push"
else
  git commit -m "auto: server sync $(date +'%Y-%m-%d %H:%M')"
  git push
  echo "Pushed to GitHub OK"
fi
rm -rf $TMPDIR

