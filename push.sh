#!/bin/bash

MSG="small code updates"
[ -n "$1" ] && MSG="$1"

echo "Pushing:\"$MSG\""

git add --all && \
git commit -m "$MSG" && \
git push -u origin master:main || \
echo "Error: One or more git operations failed, check output." >&2
