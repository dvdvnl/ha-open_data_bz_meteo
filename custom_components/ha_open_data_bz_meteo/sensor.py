from .const import DOMAIN
from open_data_bz_meteo import Client


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up sensors from YAML (not used, but required for platform discovery)."""
    return
