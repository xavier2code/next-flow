---
phase: 02-agent-engine-core
plan: 02
subsystem: agent-engine
tags: [langchain, openai, ollama, llm-factory, streaming, langgraph]

# Dependency graph
requires:
  - phase: 01-foundation-auth
    provides: Settings class in config.py, project structure, pyproject.toml
provides:
  - "get_llm() factory function with OpenAI + Ollama provider routing"
  - "Extended Settings with LLM provider configuration fields"
  - "12 unit tests covering all factory behaviors"
affects: [02-agent-engine-core, 03-realtime-api]

# Tech tracking
tech-stack:
  added: [langchain-openai>=0.3.0, langchain-ollama>=1.0.0, langchain-community>=0.3.0, langgraph>=1.1.0, langchain-core>=0.3.0]
  patterns: [llm-factory-pattern, provider-routing, streaming-by-default]

key-files:
  created:
    - backend/app/services/agent_engine/__init__.py
    - backend/app/services/agent_engine/llm.py
    - backend/tests/unit/__init__.py
    - backend/tests/unit/test_llm_factory.py
  modified:
    - backend/app/core/config.py
    - backend/pyproject.toml
    - backend/.env.example

key-decisions:
  - "Used langchain-ollama instead of deprecated langchain-community ChatOllama"
  - "Tests mock settings object to avoid requiring real API keys"
  - "api_key=settings.openai_api_key or None allows empty string fallback"

patterns-established:
  - "LLM Factory pattern: get_llm(config) creates provider-specific ChatModel instances"
  - "Settings extension pattern: add LLM config fields to existing Pydantic Settings class"
  - "Provider routing via simple if/elif chain with ValueError for unknown providers"

requirements-completed: [AGNT-04]

# Metrics
duration: 4min
completed: 2026-03-29
---

# Phase 2 Plan 2: LLM Factory Summary

**Multi-provider LLM factory (OpenAI + Ollama) with streaming=True default, Settings extension for LLM configuration, and 12 passing unit tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-28T23:59:23Z
- **Completed:** 2026-03-29T00:03:24Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- get_llm() factory function creates ChatOpenAI or ChatOllama based on provider string
- Settings extended with 4 new LLM fields: default_provider, default_model, openai_api_key, ollama_base_url
- All LLM instances created with streaming=True per D-10
- Graceful fallback to Settings defaults when config is None or empty dict
- .env.example updated with LLM provider configuration entries
- 12 unit tests covering Settings fields, provider routing, default fallback, overrides, and error handling

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for LLM factory and Settings extension** - `e6100c6` (test)
2. **Task 2: Implement Settings extension and LLM factory to pass all tests** - `a544c86` (feat)

_Note: TDD flow -- Task 1 is RED (failing tests), Task 2 is GREEN (implementation)._

## Files Created/Modified
- `backend/app/services/agent_engine/llm.py` - LLM factory function with OpenAI/Ollama provider routing
- `backend/app/services/agent_engine/__init__.py` - New agent_engine service package
- `backend/tests/unit/test_llm_factory.py` - 12 unit tests for LLM factory and Settings
- `backend/tests/unit/__init__.py` - Unit test package init
- `backend/app/core/config.py` - Extended Settings with 4 LLM configuration fields
- `backend/pyproject.toml` - Added langchain-openai, langchain-ollama, langchain-community, langgraph, langchain-core dependencies
- `backend/.env.example` - Added LLM provider environment variable entries

## Decisions Made
- Used `langchain-ollama>=1.0.0` instead of `langchain-community` ChatOllama (which is deprecated since langchain-community 0.3.1)
- Used `api_key=settings.openai_api_key or None` to handle empty string default properly (ChatOpenAI expects None when no key is set)
- Tests mock the settings object via `patch("app.services.agent_engine.llm.settings")` to avoid requiring real API credentials

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test mock missing model attribute**
- **Found during:** Task 2 (running tests after implementation)
- **Issue:** test_get_llm_temperature_override and test_get_llm_max_tokens_override did not pass model in config, causing settings.default_model to be a MagicMock object passed to ChatOpenAI constructor
- **Fix:** Added explicit "model": "gpt-4o" to both test config dicts
- **Files modified:** backend/tests/unit/test_llm_factory.py
- **Verification:** All 12 tests pass
- **Committed in:** a544c86 (Task 2 commit)

**2. [Rule 1 - Bug] Switched from deprecated langchain-community ChatOllama to langchain-ollama**
- **Found during:** Task 2 (running tests, saw LangChainDeprecationWarning)
- **Issue:** ChatOllama from langchain_community.chat_models is deprecated since 0.3.1 and will be removed in 1.0.0
- **Fix:** Installed langchain-ollama>=1.0.0, updated imports in llm.py and test file
- **Files modified:** backend/app/services/agent_engine/llm.py, backend/tests/unit/test_llm_factory.py, backend/pyproject.toml
- **Verification:** All 12 tests pass with no deprecation warnings
- **Committed in:** a544c86 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both auto-fixes necessary for correctness. langchain-ollama is the recommended replacement by the library authors. No scope creep.

## Issues Encountered
- pyproject.toml setuptools complained about multiple top-level packages when running `uv pip install -e ".[dev]"` -- used direct `uv pip install` instead for dependency installation

## User Setup Required
None - no external service configuration required. LLM providers are configured via environment variables when needed.

## Next Phase Readiness
- get_llm() factory ready for use in Plan node and Respond node implementations (Plan 03)
- Settings LLM fields available for all agent engine components
- langchain-openai and langchain-ollama installed and tested
- Tests demonstrate the factory pattern works with mocked providers

---
*Phase: 02-agent-engine-core*
*Completed: 2026-03-29*

## Self-Check: PASSED

- All created files verified to exist
- All task commits verified in git log (e6100c6, a544c86)
- All 12 unit tests passing
