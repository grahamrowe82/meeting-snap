# Meeting Snap Codebase Audit - September 17, 2025

## Executive Summary

The meeting-snap repository is in a **problematic state** with significant discrepancies between documentation, dependencies, and actual functionality. The codebase has grown substantially from the original simple Flask app but contains fundamental infrastructure issues that prevent basic operation.

## Critical Issues Found

### 1. **Flask Version Incompatibility**
- **Issue**: Flask 2.3.3 installed has different `run()` method signature than expected
- **Evidence**: `Flask.run()` only accepts `debug` parameter, not `host`, `port`, etc.
- **Impact**: Cannot start the web server using documented methods
- **Root Cause**: Documentation assumes newer Flask API

### 2. **Dependency Management Chaos**
- **Issue**: Multiple conflicting dependency management approaches
- **Evidence**: 
  - `requirements.txt` contains only `Flask==2.3.3`
  - Documentation mentions `openai` and `pytest` as dependencies
  - Actual code imports many modules not in requirements
  - Custom Flask/Pydantic stubs in `flask/` and `pydantic/` directories
- **Impact**: Impossible to reliably reproduce environment

### 3. **Documentation-Reality Gap**
- **Issue**: Documentation doesn't match actual codebase structure or capabilities
- **Evidence**:
  - README says run with `python -m t008_meeting_snap.app` (doesn't work)
  - DEVELOPMENT.md shows Flask commands that fail
  - Pre-deploy checklist assumes working web server
- **Impact**: New developers cannot onboard, deployment procedures are broken

## Codebase Structure Analysis

### Current Size (Lines of Code)
- **Application Code**: 1,929 lines
- **Tests**: 399 lines  
- **Total Project**: 1,929 lines (excluding venv)

### File Breakdown
```
t008_meeting_snap/logic.py      407 lines - Core extraction logic
t008_meeting_snap/app.py        323 lines - Flask application  
t008_meeting_snap/llm_openai.py 158 lines - OpenAI integration
t008_meeting_snap/schema.py     156 lines - Data validation
t008_meeting_snap/metrics.py    102 lines - Prometheus metrics
t008_meeting_snap/export.py     100 lines - Markdown export
t008_meeting_snap/llm.py         84 lines - LLM abstraction
t008_meeting_snap/config.py      62 lines - Configuration
t008_meeting_snap/safety.py     57 lines - Rate limiting/safety
t008_meeting_snap/extractor.py   39 lines - Provider orchestration
t008_meeting_snap/llm_fake.py    24 lines - Fake LLM for testing
t008_meeting_snap/adapter.py     20 lines - Adapter utilities
t008_meeting_snap/__init__.py     3 lines - Package init
```

### Dependencies Actually Installed
```
Flask==2.3.3
pytest==8.4.2
blinker==1.9.0
click==8.2.1
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.2
Werkzeug==3.1.3
```

### Dependencies Missing/Undocumented
- `openai` (mentioned in docs, used in code, not installed)
- Various other imports that may be using stdlib or custom stubs

## Architecture Assessment

### What Works
- **Test Suite**: 16 tests pass, comprehensive coverage
- **Core Logic**: Rule-based extraction in `logic.py` is functional
- **Modular Design**: Clean separation of concerns
- **Custom Stubs**: Clever Flask/Pydantic stubs for testing

### What's Broken
- **Web Server**: Cannot start Flask application
- **Dependency Chain**: Unclear what's actually required
- **Documentation**: Completely out of sync with reality
- **Development Workflow**: Basic commands don't work

## Technical Debt Analysis

### High Priority Issues
1. **Flask API Compatibility**: Need to fix server startup
2. **Requirements Management**: Consolidate and document all dependencies  
3. **Documentation Update**: Align docs with actual codebase
4. **Development Setup**: Create working local development instructions

### Medium Priority Issues
1. **Custom Stubs**: Document why Flask/Pydantic stubs exist
2. **Testing Strategy**: Clarify test vs production dependency split
3. **Configuration**: Environment variable handling needs documentation

### Low Priority Issues
1. **Code Organization**: Some files approaching complexity limits
2. **Error Handling**: Could be more robust in places

## Recommendations

### Immediate Actions (Critical)
1. **Fix Flask Startup**: Update app.py to use correct Flask API
2. **Create Complete requirements.txt**: Include ALL dependencies
3. **Update Documentation**: Rewrite setup instructions that actually work
4. **Test Basic Functionality**: Ensure core features work end-to-end

### Short Term (1-2 weeks)
1. **Dependency Audit**: Document purpose of all custom stubs
2. **Environment Setup**: Create foolproof development setup script
3. **Integration Testing**: Test all provider scenarios work

### Long Term (1+ months)
1. **Architecture Review**: Evaluate if custom stubs are still needed
2. **Performance Testing**: Ensure system handles expected load
3. **Security Review**: Audit rate limiting and input validation

## Risk Assessment

**HIGH RISK**: Current state prevents basic operation and deployment
- Cannot run the application
- Documentation is misleading
- Dependency management is broken
- New team members cannot contribute

**MEDIUM RISK**: Technical debt will slow future development
- Custom stubs may become maintenance burden
- Testing strategy is unclear
- Configuration management needs work

## Conclusion

The meeting-snap codebase has grown significantly in functionality but has fundamental infrastructure problems that must be addressed before any feature work or deployment can proceed. The core logic appears sound, but the surrounding infrastructure is in a broken state.

**Recommendation**: Stop all feature development and focus on infrastructure repair. The codebase needs a "back to basics" approach to get it into a working state before proceeding with the pre-deploy checklist or any new features.
