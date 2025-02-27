#!/bin/bash

set -e
set -x

COMMIT_MSG=$(git log --no-merges -1 --oneline)

# The commit marker "[cd build]" or "[cd build pk]" will trigger the build when required
if [[ "$GITHUB_EVENT_NAME" == schedule ||
      "$COMMIT_MSG" =~ \[cd\ build\] ||
      "$COMMIT_MSG" =~ \[cd\ build\ pk\] ]]; then
    echo "build=true" >> $GITHUB_OUTPUT
fi
