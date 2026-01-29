# Review Summary

Synthesize the following code reviews from multiple reviewers into a comprehensive summary.

## Diff Statistics
- Files Changed: {files_changed}
- Additions: +{additions}
- Deletions: -{deletions}

## Individual Reviews

{agent_reviews}

## Instructions

Create a comprehensive summary that:

### 1. Overall Assessment
Provide a brief (2-3 sentences) overall assessment of the code changes:
- Are the changes ready to merge?
- What is the general quality level?
- Are there any blocking issues?

### 2. Priority Issues
List the most critical issues that must be addressed before merging, organized by severity:

#### Blocking (ERROR)
Issues that must be fixed before merge.

#### Important (WARNING)
Issues that should be addressed but may not block merge.

#### Suggestions (INFO)
Nice-to-have improvements for consideration.

### 3. Key Themes
Identify recurring themes or patterns across the reviews:
- Common issues found by multiple reviewers
- Systemic concerns that should be addressed
- Positive patterns worth maintaining

### 4. Action Items
Provide a clear, prioritized list of action items for the developer:
1. What to fix immediately
2. What to address in this PR
3. What to consider for future improvements

### 5. Recommendations
Based on all reviews, provide final recommendations:
- Should this PR be approved, require changes, or rejected?
- What follow-up work might be needed?
- Are there any broader concerns to address in future work?

Be concise but thorough. Focus on actionable feedback that helps the developer improve the code efficiently.
