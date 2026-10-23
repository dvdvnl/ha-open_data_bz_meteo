"""Platform setup for the OPENdata BZ Meteo Home Assistant integration.

A single config entry holds the API URL and language; every weather station is
a `station` subentry of it. One coordinator polls all stations.
"""

from __future__ import annotations

import logging
from types import MappingProxyType

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from open_data_bz_meteo import Client

from .const import (
    CONF_API_LANGUAGE,
    CONF_API_URL,
    CONF_STATION_CODE,
    DEFAULT_API_URL,
    DOMAIN,
    PLATFORMS,
    SCAN_INTERVAL,
    SUBENTRY_TYPE_STATION,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _setting(entry: ConfigEntry, key: str, default: str) -> str:
    """Return a setting, preferring options over data."""
    return entry.options.get(key, entry.data.get(key, default))


def _station_codes(entry: ConfigEntry) -> list[str]:
    """Return the station codes of all station subentries."""
    return [
        subentry.data[CONF_STATION_CODE]
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_STATION
    ]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Merge the per-station config entries of older versions into one."""
    await _async_migrate_legacy_entries(hass)
    return True


async def _async_migrate_legacy_entries(hass: HomeAssistant) -> None:
    """Turn one-entry-per-station (version >= 1.1.0) into one entry with subentries.

    The first legacy entry becomes the parent and keeps its URL and language.
    Every station becomes a subentry; devices and entities are moved to it
    (keeping their IDs and history) before the other legacy entries are removed.
    """
    entries = hass.config_entries.async_entries(DOMAIN)
    legacy = [entry for entry in entries if entry.version < 2]
    if not legacy:
        return

    current = [entry for entry in entries if entry.version >= 2]
    parent = current[0] if current else legacy[0]

    codes: list[str] = []
    for entry in legacy:
        for code in entry.data.get("configured_stations", []):
            if code not in codes:
                codes.append(code)

    settings = {
        CONF_API_LANGUAGE: _setting(legacy[0], CONF_API_LANGUAGE, "de"),
        CONF_API_URL: _setting(legacy[0], CONF_API_URL, DEFAULT_API_URL),
    }

    subentry_ids: dict[str, str] = {}
    for subentry in parent.subentries.values():
        subentry_ids[subentry.data[CONF_STATION_CODE]] = subentry.subentry_id
    for code in codes:
        if code in subentry_ids:
            continue
        subentry = ConfigSubentry(
            data=MappingProxyType({CONF_STATION_CODE: code}),
            subentry_type=SUBENTRY_TYPE_STATION,
            title=code,
            unique_id=code,
        )
        hass.config_entries.async_add_subentry(parent, subentry)
        subentry_ids[code] = subentry.subentry_id

    if parent in legacy:
        hass.config_entries.async_update_entry(
            parent, data=settings, options={}, version=2
        )

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    for entry in legacy:
        for entity in er.async_entries_for_config_entry(
            entity_registry, entry.entry_id
        ):
            code = max(
                (
                    code
                    for code in subentry_ids
                    if (entity.unique_id or "").startswith(f"{code}_")
                ),
                key=len,
                default=None,
            )
            if code is not None:
                entity_registry.async_update_entity(
                    entity.entity_id,
                    config_entry_id=parent.entry_id,
                    config_subentry_id=subentry_ids[code],
                )

        for device in dr.async_entries_for_config_entry(
            device_registry, entry.entry_id
        ):
            code = next(
                (ident for domain, ident in device.identifiers if domain == DOMAIN),
                None,
            )
            if code in subentry_ids:
                device_registry.async_update_device(
                    device.id,
                    new_config_entry_id=parent.entry_id,
                    new_config_subentry_id=subentry_ids[code],
                )

    for entry in legacy:
        if entry is not parent:
            await hass.config_entries.async_remove(entry.entry_id)

    _LOGGER.info("Merged %d station entries into one entry", len(legacy))


def _async_sync_subentry_titles(
    hass: HomeAssistant, entry: ConfigEntry, data: dict[str, dict]
) -> None:
    """Title each station subentry with the station name in the current language."""
    language = _setting(entry, CONF_API_LANGUAGE, "de")
    for subentry in entry.subentries.values():
        code = subentry.data[CONF_STATION_CODE]
        station = (data.get(code) or {}).get("station")
        if station is None:
            continue
        name = (
            {
                "de": station.name_deu,
                "it": station.name_ita,
                "lld": station.name_lld,
            }.get(language)
            or station.name_eng
            or station.name_deu
        )
        title = f"{name} ({code})" if name else code
        if subentry.title != title:
            hass.config_entries.async_update_subentry(entry, subentry, title=title)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry.

    - Instantiate client and data coordinator for all station subentries.
    - Fetch initial station/sensor data on setup.
    - Forward setup to sensor platform.

    Returns:
        True when setup is successful. Raises ConfigEntryNotReady on failure.
    """
    client = Client(base_url=_setting(entry, CONF_API_URL, DEFAULT_API_URL))

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

            result: dict[str, dict] = {}
            for station_code in _station_codes(entry):
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

    _async_sync_subentry_titles(hass, entry, coordinator.data)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    # Reload when options or subentries (stations) change.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Start platform setup (sensor only in this integration).
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after its options or subentries changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and cleanup stored resources."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    if not hass.data.get(DOMAIN):
        # Remove domain key if empty
        hass.data.pop(DOMAIN, None)

    return True
