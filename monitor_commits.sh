#!/bin/bash

# Continuous Commit Monitoring Script
# Monitors for new commits and triggers review agents

REVIEW_NOTES="review_notes.md"
LAST_REVIEWED_FILE=".last_reviewed_commit"
CHECK_INTERVAL=300  # Check every 5 minutes

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the last reviewed commit
get_last_reviewed() {
    if [ -f "$LAST_REVIEWED_FILE" ]; then
        cat "$LAST_REVIEWED_FILE"
    else
        # If no file exists, use current HEAD
        git rev-parse HEAD
    fi
}

# Check for new commits
check_new_commits() {
    local last_reviewed=$(get_last_reviewed)
    local current_head=$(git rev-parse HEAD)
    
    if [ "$last_reviewed" != "$current_head" ]; then
        echo -e "${GREEN}New commits detected!${NC}"
        
        # Count new commits
        local new_count=$(git rev-list --count ${last_reviewed}..${current_head})
        echo "Found $new_count new commits to review"
        
        # Get commit list
        echo -e "\n${YELLOW}New commits:${NC}"
        git log --oneline ${last_reviewed}..${current_head}
        
        # Update review notes with new commits
        update_review_notes "$last_reviewed" "$current_head" "$new_count"
        
        # Update last reviewed
        echo "$current_head" > "$LAST_REVIEWED_FILE"
        
        return 0
    else
        echo "No new commits since last review"
        return 1
    fi
}

# Update review notes file
update_review_notes() {
    local from_commit=$1
    local to_commit=$2
    local count=$3
    local timestamp=$(date '+%Y-%m-%d %H:%M')
    
    # Create new review section
    cat >> "$REVIEW_NOTES" << EOF

---

## New Commits Review - $timestamp
**Commits**: $from_commit..$to_commit ($count new)
**Status**: Pending Agent Review

### Commits to Review:
\`\`\`
$(git log --oneline ${from_commit}..${to_commit})
\`\`\`

### Review Tasks:
- [ ] Security review (check for exposed credentials)
- [ ] Performance analysis (query optimization)
- [ ] Code quality check (patterns and practices)
- [ ] Test coverage verification
- [ ] Documentation updates

**Agent Assignment**: Pending automated assignment

EOF

    echo -e "${GREEN}Updated $REVIEW_NOTES with new commits${NC}"
}

# Main monitoring loop
monitor_commits() {
    echo -e "${GREEN}Starting continuous commit monitoring...${NC}"
    echo "Checking every $CHECK_INTERVAL seconds"
    echo "Review notes: $REVIEW_NOTES"
    echo -e "Press ${RED}Ctrl+C${NC} to stop monitoring\n"
    
    while true; do
        echo -e "\n[$(date '+%H:%M:%S')] Checking for new commits..."
        
        # Fetch latest changes
        git fetch --quiet
        
        # Check for new commits
        if check_new_commits; then
            echo -e "${YELLOW}Action Required: Review new commits in $REVIEW_NOTES${NC}"
            
            # Optional: Send notification (uncomment if needed)
            # osascript -e 'display notification "New commits need review" with title "Codex Dreams"'
        fi
        
        # Wait before next check
        echo "Next check in $CHECK_INTERVAL seconds..."
        sleep $CHECK_INTERVAL
    done
}

# Handle script termination
trap 'echo -e "\n${YELLOW}Monitoring stopped${NC}"; exit 0' INT TERM

# Start monitoring
monitor_commits