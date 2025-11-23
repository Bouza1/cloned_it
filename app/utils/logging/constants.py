LOG_LEVEL = "log_level"
DEBUG = "DEBUG"
INFO = "INFO"
WARNING = "WARNING"
ERROR = "ERROR"
CRITICAL = "CRITICAL"
LOG_LEVELS = [DEBUG, INFO, WARNING, ERROR, CRITICAL]

LOG_REQUEST_KEYS = [
    "name",
    "msg",
    "args",
    "created",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "thread",
    "threadName",
    "exc_info",
    "exc_text",
    "stack_info",
    "correlation_id",
    "request_path",
    "request_method",
    "user_agent",
    "user_id",
]

NO_REQUEST = "no-request"
CORRELATION_ID = "correlation_id"
USER_AGENT_HEADER = "User-Agent"
UNKNOWN = "unknown"
ANONYMOUS = "anonymous"
REMOTE_ADDR = "remote_addr"
SEVERITY = "severity"
EXCEPTION = "exception"
LOGGER = "logger"
PATH = "path"
METHOD = "method"

REQUEST = "request"
REQUEST_METHOD = "request_method"
REQUEST_PATH = "request_path"
USER_AGENT = "user_agent"
USER_ID = "user_id"
IP_ADDRESS = "ip_address"
X_FORWARDED_FOR = "X-Forwarded-For"

IP_FORWARDED_FOR = "ip_forwarded_for"
X_CORRELATION_ID = "X-Correlation-ID"

EVENT_TYPE = "event_type"
SUCCESS = "success"
TIMESTAMP = "timestamp"
SECURITY_EVENT = "security_event"
AUDIT_EVENT = "audit_event"
RESOURCE = "resource"
ACTION = "action"
GRANTED = "granted"
SECURITY_VIOLATION = "security_violation"
DESCRIPTION = "description"

STATUS_CODE = "status_code"
RESPONSE_SIZE = "response_size"


USER_ID = "user_id"
USER_EMAIL = "user_email"
FAILURE_REASON = "failure_reason"
DENIAL_REASON = "denial_reason"
CHANGED_BY = "changed_by"
SESSION_ID_PARTIAL = "session_id_partial"
