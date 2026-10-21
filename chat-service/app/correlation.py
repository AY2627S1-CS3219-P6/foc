from contextvars import ContextVar

correlation_id = ContextVar("chat_correlation_id", default="")
