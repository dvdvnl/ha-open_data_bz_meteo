from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPressure, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Open Data BZ Meteo sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for station_code, station_data in coordinator.data.items():
        for sensor_data in station_data["sensors"]:
            entities.append(
                OpenDataBZMeteoSensor(coordinator, entry, station_code, sensor_data)
            )

    async_add_entities(entities, True)


class OpenDataBZMeteoSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for OPENdata BZ Meteo data."""

    def __init__(self, coordinator, config_entry, station_code, sensor_data):
        """Initialize the sensor entity with coordinator and API sensor data."""
        super().__init__(coordinator)

        self.config_entry = config_entry
        self.sensor_type = sensor_data.type
        self.station_code = station_code
        self._attr_unique_id = f"{station_code}_{self.sensor_type}"
        self._sensor_data = sensor_data

        # Map raw API units to HA standardized units for automatic conversion.
        native_unit = (sensor_data.unit or "").strip()

        # Temperature (°C)
        if native_unit == "°C":
            native_unit = UnitOfTemperature.CELSIUS

        # Speed (m/s)
        elif native_unit == "m/s":
            native_unit = UnitOfSpeed.METERS_PER_SECOND

        # Pressure (hPa)
        elif native_unit == "hPa":
            native_unit = UnitOfPressure.HPA

        self._attr_device_class = self._get_device_class(sensor_data.type)
        self._attr_native_unit_of_measurement = native_unit
        self._attr_state_class = self._get_state_class(sensor_data.type)

    @property
    def suggested_object_id(self) -> str | None:
        """Suggest an object ID for the entity (affects initial entity_id)."""
        return self.unique_id.lower() if self.unique_id else None

    @property
    def device_info(self):
        """Return device information for the station the sensor belongs to."""
        station_data = self.coordinator.data.get(self.station_code, {}).get("station")
        if station_data is None:
            return None

        return {
            "identifiers": {(DOMAIN, self.station_code)},
            "model": station_data.station_code,
            "name": self._get_station_name(station_data),
        }

    @property
    def name(self):
        """Return a localized name for the sensor entity."""
        station_data = self.coordinator.data.get(self.station_code, {}).get("station")
        if station_data is None:
            station_name = self.station_code
        else:
            station_name = self._get_station_name(station_data)

        sensor_data = self._get_sensor_data()
        if sensor_data is None:
            sensor_label = self.sensor_type
        else:
            sensor_label = {
                "de": sensor_data.description_deu,
                "it": sensor_data.description_ita,
                "lld": sensor_data.description_lld,
            }.get(self._api_language(), sensor_data.description_deu)

        return f"{station_name} {sensor_label}"

    @property
    def native_value(self):
        """Return the native value of the sensor from the API data."""
        sensor_data = self._get_sensor_data()
        if sensor_data is None:
            return None

        try:
            return float(sensor_data.value)
        except (TypeError, ValueError):
            return sensor_data.value

    @property
    def available(self):
        """Return True if the sensor data is available and updated successfully."""
        if not self.coordinator.last_update_success:
            return False

        sensor_data = self._get_sensor_data()
        return sensor_data is not None and sensor_data.value is not None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes for the sensor entity."""
        attrs = {}

        # Provide cardinal direction for wind direction sensors
        if self.sensor_type == "WR":
            value = self.native_value
            try:
                deg = float(value)  # type: ignore
            except (TypeError, ValueError):
                deg = None

            if deg is not None:
                attrs["cardinal_direction"] = self._deg_to_cardinal(deg)
        return attrs

    @staticmethod
    def _get_state_class(sensor_type: str):
        """Return the Home Assistant state class for a given sensor type."""
        # Wind direction should use measurement_angle (not generic measurement)
        if sensor_type == "WR":
            return SensorStateClass.MEASUREMENT_ANGLE

        # Other numeric sensors are generic measurements
        return SensorStateClass.MEASUREMENT

    @staticmethod
    def _get_device_class(sensor_type: str):
        """Return the Home Assistant device class for a given sensor type."""

        # Air temperature (LT), Water temperature (WT)
        if sensor_type in ("LT", "WT"):
            return SensorDeviceClass.TEMPERATURE

        # Humidity (LF)
        if sensor_type == "LF":
            return SensorDeviceClass.HUMIDITY

        # Pressure (LD.RED)
        if sensor_type == "LD.RED":
            return SensorDeviceClass.PRESSURE

        # Wind speed (WG, WG.BOE)
        if sensor_type in ("WG", "WG.BOE"):
            return SensorDeviceClass.WIND_SPEED

        # Solar radiation (GS)
        if sensor_type == "GS":
            return SensorDeviceClass.IRRADIANCE

        # Wind direction (WR)
        if sensor_type == "WR":
            return SensorDeviceClass.WIND_DIRECTION

        # Precipitation (N)
        if sensor_type == "N":
            return SensorDeviceClass.PRECIPITATION

        # Flow rate (Q)
        if sensor_type == "Q":
            return SensorDeviceClass.VOLUME_FLOW_RATE

        # Height of snow (HS) and water level (W)
        if sensor_type in ("HS", "W"):
            return SensorDeviceClass.DISTANCE

        # Sunshine duration (SD)
        if sensor_type == "SD":
            return SensorDeviceClass.DURATION

        return None  # Unknown sensor type

    @staticmethod
    def _deg_to_cardinal(deg: float) -> str:
        """Convert degrees to a 16-point cardinal direction string."""
        directions = [
            "N",
            "NNE",
            "NE",
            "ENE",
            "E",
            "ESE",
            "SE",
            "SSE",
            "S",
            "SSW",
            "SW",
            "WSW",
            "W",
            "WNW",
            "NW",
            "NNW",
        ]
        idx = int((deg + 11.25) / 22.5) % 16
        return directions[idx]

    def _get_sensor_data(self):
        """Retrieve the latest sensor object for this entity from coordinator data."""
        station_entry = self.coordinator.data.get(self.station_code)
        if station_entry is None:
            return None

        sensors = station_entry.get("sensors", [])
        return next(
            (sensor for sensor in sensors if sensor.type == self.sensor_type), None
        )

    def _get_station_name(self, station_data) -> str:
        """Return the localized station name for the configured API language."""
        lang = self._api_language()
        return {
            "de": station_data.name_deu,
            "it": station_data.name_ita,
            "lld": station_data.name_lld,
        }.get(lang, station_data.name_deu)

    def _api_language(self) -> str:
        """Return the configured API language, preferring options over data."""
        options = getattr(self.config_entry, "options", {}) or {}
        return options.get(
            "api_language", self.config_entry.data.get("api_language", "de")
        )
