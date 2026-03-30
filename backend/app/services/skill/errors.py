"""Classified skill validation and storage errors."""


class SkillError(Exception):
    """Base error for skill operations."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class SkillValidationError(SkillError):
    """Validation error: invalid SKILL.md or ZIP structure."""

    pass


class SkillStorageError(SkillError):
    """Storage error: MinIO upload/download failure."""

    pass


class SkillToolError(Exception):
    """Base error for skill tool invocation failures."""

    def __init__(self, tool_name: str, message: str) -> None:
        self.tool_name = tool_name
        super().__init__(message)


class SkillToolTimeoutError(SkillToolError):
    """Timeout error for skill tool execution."""

    def __init__(self, tool_name: str, timeout: float) -> None:
        self.timeout = timeout
        super().__init__(
            tool_name,
            f"Skill tool '{tool_name}' timed out after {timeout}s. "
            f"The sandbox may be overloaded.",
        )


class SkillToolConnectionError(SkillToolError):
    """Connection error for skill tool sandbox."""

    def __init__(self, tool_name: str, detail: str) -> None:
        super().__init__(
            tool_name,
            f"Skill tool '{tool_name}' failed: sandbox unreachable. {detail}",
        )


class SkillToolExecutionError(SkillToolError):
    """Execution error during skill tool invocation."""

    def __init__(self, tool_name: str, detail: str) -> None:
        super().__init__(
            tool_name,
            f"Skill tool '{tool_name}' execution error: {detail}",
        )
