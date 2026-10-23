from datetime import timedelta

DOMAIN = "ha_open_data_bz_meteo"
PLATFORMS = ["sensor"]
SCAN_INTERVAL = timedelta(minutes=10)

CONF_API_URL = "api_url"
DEFAULT_API_URL = "https://geoservices.buergernetz.bz.it/services/meteo/v1"
