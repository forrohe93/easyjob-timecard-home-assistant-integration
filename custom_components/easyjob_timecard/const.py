from homeassistant.const import Platform

DOMAIN = "easyjob_timecard"
NAME = "easyjob Timecard"
MANUFACTURER = "protonic"


PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.SWITCH,
    Platform.SELECT,
]

CONF_BASE_URL = "base_url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

CONF_VERIFY_SSL = "verify_ssl"
DEFAULT_VERIFY_SSL = True

DEFAULT_SCAN_INTERVAL_SECONDS = 60

# Calendar filtering (IdT values)
DEFAULT_FILTERED_IDT = [34, 3]
CONF_FILTERED_IDT = "filtered_idt"

DEFAULT_LOOKAHEAD_DAYS = 30

# New: dynamic resource status binary sensors (list of IdResourceStateType)
CONF_STATUS_BINARY_SENSORS = "status_binary_sensors"
DEFAULT_STATUS_BINARY_SENSORS: list[int] = []
