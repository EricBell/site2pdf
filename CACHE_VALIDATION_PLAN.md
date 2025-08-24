# Cache Validation and Recovery Mechanisms Plan

## Overview
This document outlines the validation and recovery mechanisms for the site2pdf caching system to ensure data integrity and graceful handling of corrupted or incomplete cache data.

## Cache Validation Mechanisms

### 1. Session Integrity Validation
- **Session metadata validation**: Verify required fields exist (session_id, base_url, created_at, status)
- **File structure validation**: Ensure session directory contains required files (session.json, pages/)
- **Status consistency**: Validate status matches actual cached data state
- **Timestamp validation**: Check created_at and last_modified are valid ISO timestamps

### 2. Page Cache Validation
- **JSON structure validation**: Verify cached pages have required fields (url, title, content, timestamp)
- **Content integrity**: Check for minimum content length and valid encoding
- **URL validation**: Ensure cached URLs match session's base domain (if scoped)
- **File corruption detection**: Validate JSON parsing succeeds for all cached pages

### 3. Preview Session Validation
- **Decision consistency**: Validate approved/excluded counts match URL lists
- **URL format validation**: Ensure all URLs are properly formatted
- **Classification validation**: Verify content type classifications are valid enum values
- **Session state validation**: Check preview session status is consistent with data

## Recovery Mechanisms

### 1. Automatic Recovery
- **Partial session recovery**: If some pages are corrupted, recover valid pages and mark session as partial
- **Status correction**: Auto-correct inconsistent session status based on actual cached data
- **Missing metadata reconstruction**: Regenerate missing timestamps and counts from cached data
- **Orphaned file cleanup**: Remove orphaned cache files without corresponding session metadata

### 2. Interactive Recovery
- **Corruption reporting**: Present detailed reports of cache issues to user with recovery options
- **Selective recovery**: Allow user to choose which corrupted sessions to attempt recovery vs. deletion
- **Data salvage**: Extract valid pages from corrupted sessions into new sessions
- **Manual intervention prompts**: Ask user for decisions when automatic recovery is ambiguous

### 3. Graceful Degradation
- **Fallback modes**: Continue operation without cache if validation fails completely
- **Warning systems**: Alert users about cache issues without breaking functionality
- **Safe mode**: Disable cache features when integrity issues are detected
- **Alternative data sources**: Use discovery mode if cached preview data is corrupted

## Implementation Strategy

### Phase 1: Basic Validation
- Implement core session and page validation functions in CacheManager
- Add validation calls during cache loading operations
- Create simple auto-repair for common issues (missing timestamps, wrong status)

### Phase 2: Advanced Recovery
- Build comprehensive cache repair utilities
- Add cache doctor CLI command for diagnostics and repair
- Implement partial session recovery mechanisms

### Phase 3: Proactive Monitoring
- Add periodic cache health checks
- Implement cache integrity monitoring during operation
- Create automated cleanup of problematic cache data

## CLI Commands for Cache Management

### Diagnostic Commands
```bash
# Check cache health
site2pdf cache doctor

# Validate specific session
site2pdf cache validate <session_id>

# Repair corrupted cache
site2pdf cache repair [--session-id <id>] [--auto-fix]
```

### Recovery Commands
```bash
# Recover partial session
site2pdf cache recover <session_id> [--salvage-pages]

# Clean corrupted sessions
site2pdf cache clean --corrupted-only

# Export data before cleanup
site2pdf cache backup [--sessions <ids>]
```

## Error Handling Strategy

1. **Fail gracefully**: Never crash due to cache issues
2. **Log comprehensively**: Record all validation failures and recovery attempts
3. **User transparency**: Inform users about cache issues and recovery actions
4. **Data preservation**: Always attempt to preserve user data when possible
5. **Safe defaults**: Default to conservative recovery options

## Testing Strategy

- Unit tests for all validation functions
- Integration tests for recovery scenarios
- Stress tests with deliberately corrupted cache data
- User experience testing for recovery workflows
- Performance impact testing of validation operations

This plan ensures the caching system is robust, self-healing, and provides excellent user experience even when cache corruption occurs.