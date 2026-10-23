"""Config flow for the OPENdata BZ Meteo custom component.

The config entry stores the API URL and the language. Weather stations are
added to it as `station` subentries.
"""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from open_data_bz_meteo import Client

from .const import (
    CONF_API_LANGUAGE,
    CONF_API_URL,
    CONF_STATION_CODE,
    DEFAULT_API_URL,
    DOMAIN,
    SUBENTRY_TYPE_STATION,
)

_LOGGER = logging.getLogger(__name__)

# Supported languages for API responses and UI labels
LANGUAGE_OPTIONS = {
    "de": "Deutsch",
    "it": "Italiano",
    "lld": "Ladin",
}


class CannotConnect(HomeAssistantError):
    """Exception raised when the config flow cannot reach the remote API."""


async def async_fetch_station_options(
    hass: HomeAssistant,
    api_url: str,
    api_language: str,
    configured_stations: list[str],
) -> dict[str, str]:
    """Fetch the selectable stations from the API.

    Excludes already configured stations and localizes the station names.

    Raises:
        CannotConnect: when the station list cannot be fetched.

    Returns:
        A mapping of station_code to human-readable display string.
    """
    client = Client(base_url=api_url)

    try:
        stations = await hass.async_add_executor_job(client.get_stations)
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Could not fetch stations: %s", err)
        raise CannotConnect from err

    items = []
    for station in stations:
        if station.station_code in configured_stations:
            continue

        name = {
            "de": station.name_deu,
            "it": station.name_ita,
            "lld": station.name_lld,
        }.get(api_language)
        if not name:
            name = station.name_eng or station.name_deu

        items.append((name, station.station_code))

    items.sort(key=lambda item: item[0])

    return {station_code: f"{name} ({station_code})" for name, station_code in items}


def _settings_schema(api_language: str, api_url: str) -> vol.Schema:
    """Build the schema shared by the setup and options forms."""
    return vol.Schema(
        {
            vol.Required(CONF_API_LANGUAGE, default=api_language): vol.In(
                LANGUAGE_OPTIONS
            ),
            vol.Required(CONF_API_URL, default=api_url): str,
        }
    )


class OpenDataBZMeteoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for OPENdata BZ Meteo."""

    VERSION = 2

    async def async_step_user(self, user_input=None):
        """Ask for the API URL and language and create the (single) entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_url = user_input[CONF_API_URL].strip()
            api_language = user_input[CONF_API_LANGUAGE]
            try:
                await async_fetch_station_options(self.hass, api_url, api_language, [])
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="OPENdata BZ Meteo",
                    data={CONF_API_LANGUAGE: api_language, CONF_API_URL: api_url},
                )

        defaults = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=_settings_schema(
                defaults.get(CONF_API_LANGUAGE, "de"),
                defaults.get(CONF_API_URL, DEFAULT_API_URL),
            ),
            errors=errors,
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: config_entries.ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the subentry types supported by this integration."""
        return {SUBENTRY_TYPE_STATION: StationSubentryFlowHandler}

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow for this config entry."""
        return OpenDataBZMeteoOptionsFlow(config_entry)


class StationSubentryFlowHandler(ConfigSubentryFlow):
    """Add a weather station as subentry."""

    async def async_step_user(self, user_input=None) -> SubentryFlowResult:
        """Let the user pick a station that is not configured yet."""
        entry = self._get_entry()
        configured = [
            subentry.data[CONF_STATION_CODE] for subentry in entry.subentries.values()
        ]

        try:
            options = await async_fetch_station_options(
                self.hass,
                entry.options.get(CONF_API_URL, entry.data.get(CONF_API_URL)),
                entry.options.get(
                    CONF_API_LANGUAGE, entry.data.get(CONF_API_LANGUAGE, "de")
                ),
                configured,
            )
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")

        if not options:
            return self.async_abort(reason="no_stations_available")

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {vol.Required(CONF_STATION_CODE): vol.In(options)}
                ),
            )

        station_code = user_input[CONF_STATION_CODE]
        return self.async_create_entry(
            title=options[station_code],
            data={CONF_STATION_CODE: station_code},
            unique_id=station_code,
        )


class OpenDataBZMeteoOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for OPENdata BZ Meteo."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options flow."""
        entry = self._config_entry

        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=_settings_schema(
                    entry.options.get(
                        CONF_API_LANGUAGE, entry.data.get(CONF_API_LANGUAGE, "de")
                    ),
                    entry.options.get(
                        CONF_API_URL, entry.data.get(CONF_API_URL, DEFAULT_API_URL)
                    ),
                ),
            )

        options = {
            CONF_API_LANGUAGE: user_input[CONF_API_LANGUAGE],
            CONF_API_URL: user_input[CONF_API_URL].strip(),
        }
        # Saving the options triggers the update listener, which reloads the entry.
        return self.async_create_entry(title="", data=options)
