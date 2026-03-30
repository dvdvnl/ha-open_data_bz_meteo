"""Platform setup for the OPENdata BZ Meteo Home Assistant integration.

This module handles config entry setup and teardown, coordinator updates
for polling station/sensor data, and keeping configuration in sync when
devices are removed from the registry.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import EVENT_DEVICE_REGISTRY_UPDATED
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PLATFORMS, SCAN_INTERVAL
from open_data_bz_meteo import Client

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry.

    - Instantiate client and data coordinator.
    - Fetch initial station/sensor data on setup.
    - Hook into device registry updates for cleanup on device removal.
    - Forward setup to sensor platform.

    Returns:
        True when setup is successful. Raises ConfigEntryNotReady on failure.
    """
    client = Client()

    async def async_update_data() -> dict[str, dict]:
        """Fetch current station and sensor data from the API.

        For each configured station, fetches its metadata and sensor readings.
        Falls back to a direct station lookup if the station is absent from the
        full station list. Stations missing from the API are skipped with a warning.

        Returns:
            A dict keyed by station_code, each containing 'station' and 'sensors'.

        Raises:
            UpdateFailed: on any unexpected error during the API calls.
        """
        try:
            stations = await hass.async_add_executor_job(client.get_stations)
            station_map = {station.station_code: station for station in stations}
            configured_stations = entry.data.get("configured_stations", [])

            result: dict[str, dict] = {}
            for station_code in configured_stations:
                station = station_map.get(station_code)
                if station is None:
                    station = await hass.async_add_executor_job(
                        client.get_station, station_code
                    )

                if station is None:
                    _LOGGER.warning(
                        "Configured station %s not available from API", station_code
                    )
                    continue

                sensors = await hass.async_add_executor_job(client.get_sensors, station)
                result[station_code] = {
                    "station": station,
                    "sensors": sensors,
                }

            return result
        except Exception as err:  # pylint: disable=broad-except
            raise UpdateFailed(err) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="OPENdata BZ Meteo",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
        config_entry=entry,
    )

    # Attempt first data fetch now to ensure API is reachable before final setup.

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        # If the initial refresh fails, do not complete setup (retry later).
        raise ConfigEntryNotReady from err

    @callback
    def _async_device_registry_updated(event):
        """Update config entry when a relevant device is removed.

        Tracks device registry removals for devices added by this integration
        (identified with DOMAIN). When a station device is removed, remove it
        from the saved configured_stations entry data.
        """
        # Only react to device removal events.
        if event.data.get("action") != "remove":
            return

        # If we can't determine which device was removed, nothing to do.
        device_id = event.data.get("device_id")
        if device_id is None:
            return

        # Resolve device entry from registry.
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get(device_id)
        if device_entry is None:
            return

        # Ensure this event belongs to this integration domain.
        if not any(identifier[0] == DOMAIN for identifier in device_entry.identifiers):
            return

        # Extract station_code from identifiers attached by this integration.
        station_code = next(
            (
                identifier[1]
                for identifier in device_entry.identifiers
                if identifier[0] == DOMAIN
            ),
            None,
        )
        if station_code is None:
            return

        # Only update config data when the station was configured.
        configured_stations = list(entry.data.get("configured_stations", []))
        if station_code not in configured_stations:
            return

        # Remove deleted station from config entry list and persist it.
        configured_stations.remove(station_code)
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "configured_stations": configured_stations},
        )

    remove_device_listener = hass.bus.async_listen(
        EVENT_DEVICE_REGISTRY_UPDATED, _async_device_registry_updated
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "device_listener": remove_device_listener,
    }

    # Start platform setup (sensor only in this integration).
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and cleanup stored resources."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if entry_data is not None:
        listener = entry_data.get("device_listener")
        if listener is not None:
            # Remove event listener to avoid memory leaks.
            listener()

    if not hass.data.get(DOMAIN):
        # Remove domain key if empty
        hass.data.pop(DOMAIN, None)

    return True
