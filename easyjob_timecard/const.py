from homeassistant.const import Platform

DOMAIN = "easyjob_timecard"
PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.BINARY_SENSOR]

CONF_BASE_URL = "base_url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

CONF_VERIFY_SSL = "verify_ssl"
DEFAULT_VERIFY_SSL = True

DEFAULT_SCAN_INTERVAL_SECONDS = 60
