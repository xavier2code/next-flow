---
phase: 01-foundation-auth
plan: 03
subsystem: auth
tags: [jwt, pyjwt, pwdlib, argon2, redis, fastapi, oauth2, refresh-tokens, tdd]

# Dependency graph
requires:
  - phase: 01-foundation-auth/01-01
    provides: FastAPI app skeleton, Redis client, database session, config settings
  - phase: 01-foundation-auth/01-02
    provides: SQLAlchemy User model with email/hashed_password, Alembic migrations
provides:
  - JWT access token (15 min) + refresh token (7 day) creation and verification via PyJWT
  - Password hashing and verification via pwdlib[argon2]
  - AuthService business logic: register, login, refresh, logout
  - UserService CRUD: get_by_email, get_by_id, create_user
  - Auth REST endpoints: POST /register, /login, /refresh, /logout, GET /me
  - get_current_user FastAPI dependency for protected endpoints
  - Refresh token rotation stored in Redis with TTL
  - 13 async integration tests covering all auth flows
affects: [02-agent-engine, 03-realtime, 04-memory, 05-mcp, 06-skills, 07-ui]

# Tech tracking
tech-stack:
  added: [pyjwt>=2.10.0, pwdlib[argon2]>=0.2.0, email-validator>=2.0.0]
  patterns:
    - "JWT with type claim (access vs refresh) and JTI for unique identification"
    - "Refresh token rotation: delete old token from Redis before issuing new pair"
    - "DUMMY_HASH for timing-attack protection on login"
    - "NullPool test engine to prevent cross-event-loop asyncpg connection errors"
    - "Test session with per-test rollback for test isolation"

key-files:
  created:
    - backend/app/core/security.py
    - backend/app/schemas/auth.py
    - backend/app/schemas/user.py
    - backend/app/schemas/error.py
    - backend/app/schemas/__init__.py
    - backend/app/services/auth_service.py
    - backend/app/services/user_service.py
    - backend/app/services/__init__.py
    - backend/app/api/v1/auth.py
    - backend/tests/__init__.py
    - backend/tests/conftest.py
    - backend/tests/test_auth.py
  modified:
    - backend/app/api/deps.py
    - backend/app/api/v1/router.py
    - backend/pyproject.toml

key-decisions:
  - "Used NullPool for test engine to prevent asyncpg cross-event-loop Future errors"
  - "Auth routes use service layer pattern (AuthService) instead of inline DB queries"
  - "get_current_user placed in deps.py alongside get_db and get_redis for single import point"
  - "Registered user fixture in conftest uses rollback pattern for test isolation"

patterns-established:
  - "TDD workflow: RED (failing tests + implementation stubs) then GREEN (routes + wiring)"
  - "Pydantic schemas for request/response validation with EmailStr and Field constraints"
  - "Service layer pattern: AuthService for business logic, UserService for data access"
  - "JWT token structure: sub=user_id, type=access|refresh, exp=expiry, jti=unique_id"
  - "Redis key naming: nextflow:refresh_token:{user_id}:{jti}"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03]

# Metrics
duration: 154min
completed: 2026-03-28
---

# Phase 01 Plan 03: Auth System Summary

**JWT auth with PyJWT/pwdlib[argon2], refresh token rotation in Redis, 13 passing integration tests**

## Performance

- **Duration:** 154 min
- **Started:** 2026-03-28T15:35:43Z
- **Completed:** 2026-03-28T18:10:30Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 15

## Accomplishments

- Complete JWT authentication system with registration, login, token refresh with rotation, and logout
- Refresh tokens stored in Redis with TTL and rotation (old token deleted before new pair issued)
- Timing-attack protection on login endpoint using DUMMY_HASH for non-existent users
- 13 integration tests covering all auth flows including edge cases (duplicate email, short password, expired token, refresh rotation)
- Pydantic request/response schemas with EmailStr validation and password minimum length
- get_current_user FastAPI dependency for protecting future endpoints

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test scaffold, schemas, security module, and auth service (RED phase)** - `649d4ce` (test)
2. **Task 2: Create auth routes, wire dependencies, and pass all tests (GREEN phase)** - `ebf0ca6` (feat)

_Note: TDD tasks: RED (failing tests + stubs) then GREEN (implementation + all tests passing)_

## Files Created/Modified

- `backend/app/core/security.py` - JWT creation/verification via PyJWT, password hashing via pwdlib[argon2], DUMMY_HASH for timing protection
- `backend/app/schemas/auth.py` - RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, LogoutRequest Pydantic models
- `backend/app/schemas/user.py` - UserResponse with from_attributes config for ORM->Pydantic conversion
- `backend/app/schemas/error.py` - ErrorDetail and ErrorResponse for consistent error format
- `backend/app/schemas/__init__.py` - Re-exports all schema classes
- `backend/app/services/auth_service.py` - AuthService: register, login, refresh, logout with Redis refresh token storage
- `backend/app/services/user_service.py` - UserService: get_by_email, get_by_id, create_user
- `backend/app/api/v1/auth.py` - Auth router: POST /register, /login, /refresh, /logout, GET /me
- `backend/app/api/deps.py` - Added get_current_user dependency with OAuth2PasswordBearer
- `backend/app/api/v1/router.py` - Added auth router to v1 aggregation
- `backend/tests/conftest.py` - Test fixtures: NullPool test engine, db_session with rollback, test_redis, async_client with dep overrides, registered_user
- `backend/tests/test_auth.py` - 13 test cases covering all auth flows
- `backend/pyproject.toml` - Added email-validator dependency

## Decisions Made

- **NullPool for test engine** - asyncpg raises "Future attached to a different loop" when the default QueuePool shares connections across pytest-asyncio test functions. NullPool opens a fresh connection per session, preventing cross-event-loop errors.
- **Service layer pattern** - Auth business logic isolated in AuthService class, data access in UserService module functions. Routes only handle HTTP concerns (request parsing, response formatting).
- **get_current_user in deps.py** - Placed alongside get_db and get_redis as a shared dependency, keeping the single-import-point pattern established in plan 01-01.
- **registered_user fixture** - Uses the actual /auth/register endpoint (not direct DB inserts) so tests exercise the full HTTP stack.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed cross-event-loop asyncpg errors in tests**
- **Found during:** Task 2 (GREEN phase - running tests)
- **Issue:** Test engine created at module import time bound connections to the import-time event loop. When pytest-asyncio ran tests in different loops, asyncpg raised "cannot perform operation: another operation is in progress" and "Task got Future attached to a different loop".
- **Fix:** Changed test_engine to use `poolclass=NullPool` so each connection is opened/closed within the same async context. Removed the `anyio_backend` fixture that was not needed.
- **Files modified:** backend/tests/conftest.py
- **Verification:** All 13 tests pass consistently
- **Committed in:** ebf0ca6 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minimal - the NullPool approach is standard for async SQLAlchemy testing. No scope creep.

## Issues Encountered

None beyond the cross-event-loop issue documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Auth foundation complete. All subsequent phases can use `Depends(get_current_user)` to protect endpoints.
- The auth router is mounted at `/api/v1/auth/*` and follows the project's layered architecture pattern.
- AuthService and UserService establish the service-layer pattern for future features.
- Test fixtures (conftest.py) establish the async testing pattern for future test suites.

## Self-Check: PASSED

- All 15 files verified present
- Both commits verified in git log (649d4ce, ebf0ca6)

---
*Phase: 01-foundation-auth*
*Completed: 2026-03-28*
