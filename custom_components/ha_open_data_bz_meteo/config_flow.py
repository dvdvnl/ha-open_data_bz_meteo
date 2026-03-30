"""Config flow for the OPENdata BZ Meteo custom component.

This module defines the Home Assistant configuration flow used when the user
adds or changes the integration through UI. It guides the user through language
selection and station selection and handles connection errors.
"""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from open_data_bz_meteo import Client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Supported languages for API responses and UI labels
LANGUAGE_OPTIONS = {
    "de": "Deutsch",
    "it": "Italiano",
    "lld": "Ladin",
}


class CannotConnect(HomeAssistantError):
    """Exception raised when the config flow cannot reach the remote API."""


class OpenDataBZMeteoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OPENdata BZ Meteo.

    This class defines the Home Assistant UI flow states for configuring the
    integration (user -> station), checking for already-configured entries,
    and creating the final `config_entries.ConfigEntry`.
    """

    # TODO: kick?
    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow state.

        Default API language is German ('de'), until overridden by the user.
        """
        self.api_language = "de"

    async def async_step_user(self, user_input=None):
        """Handle the initial user step of the config flow.

        If no input is provided, show a form to let the user select `api_language`.
        Once input is provided, store language choice and continue to station step.
        """
        # When user opens the integration setup, show the language selection form.
        if user_input is None:
            form_schema = vol.Schema(
                {
                    vol.Required("api_language", default="de"): vol.In(
                        LANGUAGE_OPTIONS
                    ),
                }
            )
            return self.async_show_form(step_id="user", data_schema=form_schema)

        # Save user-selected language and move to station selection step.
        self.api_language = user_input["api_language"]
        return await self.async_step_station()

    async def async_step_station(self, user_input=None):
        """Handle the station selection step of the config flow.

        - Fetches currently configured stations from existing entry (if any).
        - Queries the API for available station options.
        - Presents a form for station selection.
        - Validates selection and creates the config entry.
        """
        # Start with no stations configured yet.
        configured_stations = []

        # Detect an existing config entry and inherit configured stations from it.
        existing_entry = next(iter(self._async_current_entries()), None)
        if existing_entry is not None:
            configured_stations = existing_entry.data.get("configured_stations", [])

        # Query station options from API, filtering out already configured ones.
        try:
            options = await self._async_fetch_station_options(
                self.api_language, configured_stations
            )
        except CannotConnect:
            # Show connection error on the station selection step.
            return self.async_show_form(
                step_id="station",
                data_schema=vol.Schema({}),
                errors={"base": "cannot_connect"},
            )

        # If no new stations are available, abort the setup flow.
        if not options:
            return self.async_abort(reason="no_stations_available")

        # If user hasn't picked a station yet, present the selection form.
        if user_input is None:
            schema = vol.Schema({vol.Required("station_code"): vol.In(options)})
            return self.async_show_form(step_id="station", data_schema=schema)

        # User submitted a station code; validate it is in the provided options.
        station_code = user_input["station_code"]

        # Create the config entry using selected station and language preference.
        return self.async_create_entry(
            title="OPENdata BZ Meteo",
            data={
                "configured_stations": [station_code],
                "api_language": self.api_language,
            },
        )

    async def _async_fetch_station_options(
        self, api_language: str, configured_stations: list[str]
    ) -> dict[str, str]:
        """Fetch station options from remote API and local config.

        Contacts the open_data_bz_meteo client(s) in a worker thread to avoid
        blocking the event loop. Excludes already configured stations and
        localizes the station names according to selected API language.

        Raises:
            CannotConnect: when station list cannot be fetched.

        Returns:
            A mapping of station_code to human-readable display string.
        """
        client = Client()

        # Execute blocking I/O in a worker to keep Home Assistant responsive.
        try:
            stations = await self.hass.async_add_executor_job(client.get_stations)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Could not fetch stations: %s", err)
            # Bubble up a config flow-specific error for UI feedback.
            raise CannotConnect from err

        items = []
        for station in stations:
            # Skip already configured station(s) to avoid duplicates.
            if station.station_code in configured_stations:
                continue

            # Choose localized name based on selected API language.
            name = {
                "de": station.name_deu,
                "it": station.name_ita,
                "lld": station.name_lld,
            }.get(api_language)
            if not name:
                # Fall back to English or German if selected language missing.
                name = station.name_eng or station.name_deu

            items.append((name, station.station_code))

        # Sort alphabetically by localized station name.
        items.sort(key=lambda item: item[0])

        # Build config flow choices in Home Assistant expected format.
        options = {
            station_code: f"{name} ({station_code})" for name, station_code in items
        }
        return options
