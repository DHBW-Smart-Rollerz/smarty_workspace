#!/bin/bash

# Get a list of all staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(c|cpp|h|hpp)$')

# Check if there are any staged files to process
if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# Run ament_uncrustify on each staged file
for FILE in $STAGED_FILES; do
    ament_uncrustify --reformat "$FILE"
    # Add the reformatted file back to the staging area
    git add "$FILE"
done

# Exit with success
exit 0
