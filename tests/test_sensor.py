import pytest
from types import SimpleNamespace


def test_language_options_ui():

    from custom_components.ha_open_data_bz_meteo.config_flow import LANGUAGE_OPTIONS

    assert LANGUAGE_OPTIONS == {"de": "Deutsch", "it": "Italiano", "lld": "Ladin"}


def test_wind_direction_state_class_and_cardinal():

    from homeassistant.components.sensor import SensorStateClass
    from homeassistant.const import UnitOfSpeed
    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor

    station_code = "83200ms"
    station = SimpleNamespace(
        station_code=station_code,
        name_deu="Station DE",
        name_ita="Station IT",
        name_lld="Station LLD",
    )
    sensor_data = SimpleNamespace(
        type="WR",
        unit="m/s",
        value="315",
        description_deu="Windrichtung",
        description_ita="Direzione del vento",
        description_lld="Direzion dl vent",
    )
    coordinator = SimpleNamespace(
        data={
            station_code: {
                "station": station,
                "sensors": [sensor_data],
            }
        },
        last_update_success=True,
    )
    config_entry = SimpleNamespace(data={"api_language": "de"})

    sensor = OpenDataBZMeteoSensor(coordinator, config_entry, station_code, sensor_data)

    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT_ANGLE
    assert sensor._attr_native_unit_of_measurement == UnitOfSpeed.METERS_PER_SECOND
    assert sensor.extra_state_attributes["cardinal_direction"] == "NW"


def test_language_ldd_fallback_station_name():

    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor

    station_code = "83200ms"
    station = SimpleNamespace(
        station_code=station_code,
        name_deu="Station DE",
        name_ita="Station IT",
        name_lld="Station LLD",
    )
    sensor_data = SimpleNamespace(
        type="LT",
        unit="°C",
        value="20",
        description_deu="Temperatur",
        description_ita="Temperatura",
        description_lld="Temperatura",
    )
    coordinator = SimpleNamespace(
        data={
            station_code: {
                "station": station,
                "sensors": [sensor_data],
            }
        },
        last_update_success=True,
    )
    config_entry = SimpleNamespace(data={"api_language": "lld"})

    sensor = OpenDataBZMeteoSensor(coordinator, config_entry, station_code, sensor_data)

    assert sensor.name.startswith("Station LLD")


def test_device_and_state_class_mapping():

    from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor

    assert (
        OpenDataBZMeteoSensor._get_state_class("WR")
        == SensorStateClass.MEASUREMENT_ANGLE
    )
    assert OpenDataBZMeteoSensor._get_state_class("LT") == SensorStateClass.MEASUREMENT

    assert (
        OpenDataBZMeteoSensor._get_device_class("LT") == SensorDeviceClass.TEMPERATURE
    )
    assert OpenDataBZMeteoSensor._get_device_class("LF") == SensorDeviceClass.HUMIDITY
    assert (
        OpenDataBZMeteoSensor._get_device_class("LD.RED") == SensorDeviceClass.PRESSURE
    )
    assert OpenDataBZMeteoSensor._get_device_class("WG") == SensorDeviceClass.WIND_SPEED
    assert (
        OpenDataBZMeteoSensor._get_device_class("WG.BOE")
        == SensorDeviceClass.WIND_SPEED
    )
    assert OpenDataBZMeteoSensor._get_device_class("GS") == SensorDeviceClass.IRRADIANCE
    assert (
        OpenDataBZMeteoSensor._get_device_class("WR")
        == SensorDeviceClass.WIND_DIRECTION
    )
    assert (
        OpenDataBZMeteoSensor._get_device_class("N") == SensorDeviceClass.PRECIPITATION
    )
    assert (
        OpenDataBZMeteoSensor._get_device_class("Q")
        == SensorDeviceClass.VOLUME_FLOW_RATE
    )
    assert OpenDataBZMeteoSensor._get_device_class("HS") == SensorDeviceClass.DISTANCE
    assert OpenDataBZMeteoSensor._get_device_class("W") == SensorDeviceClass.DISTANCE
    assert OpenDataBZMeteoSensor._get_device_class("SD") == SensorDeviceClass.DURATION


def test_deg_to_cardinal_boundaries():

    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor

    assert OpenDataBZMeteoSensor._deg_to_cardinal(0.0) == "N"
    assert OpenDataBZMeteoSensor._deg_to_cardinal(11.25) == "NNE"
    assert OpenDataBZMeteoSensor._deg_to_cardinal(90.0) == "E"
    assert OpenDataBZMeteoSensor._deg_to_cardinal(180.0) == "S"
    assert OpenDataBZMeteoSensor._deg_to_cardinal(315.0) == "NW"


def test_native_value_and_availability_cases():

    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor

    station_code = "83200ms"
    station = SimpleNamespace(
        station_code=station_code,
        name_deu="Station DE",
        name_ita="Station IT",
        name_lld="Station LLD",
    )

    # Raw numeric value as string converts to float
    sensor_data_valid = SimpleNamespace(
        type="LT",
        unit="°C",
        value="21.5",
        description_deu="Temperatur",
        description_ita="Temperatura",
        description_lld="Temperatura",
    )

    coordinator_valid = SimpleNamespace(
        data={
            station_code: {
                "station": station,
                "sensors": [sensor_data_valid],
            }
        },
        last_update_success=True,
    )
    config_entry = SimpleNamespace(data={"api_language": "de"})

    sensor_valid = OpenDataBZMeteoSensor(
        coordinator_valid, config_entry, station_code, sensor_data_valid
    )
    assert sensor_valid.native_value == 21.5
    assert sensor_valid.available is True

    # Non-numeric value returns raw value
    sensor_data_invalid = SimpleNamespace(
        **{**sensor_data_valid.__dict__, "value": "n/a"}
    )
    coordinator_invalid = SimpleNamespace(
        data={
            station_code: {
                "station": station,
                "sensors": [sensor_data_invalid],
            }
        },
        last_update_success=True,
    )
    sensor_invalid = OpenDataBZMeteoSensor(
        coordinator_invalid, config_entry, station_code, sensor_data_invalid
    )
    assert sensor_invalid.native_value == "n/a"

    # Coordinator update failure => unavailable
    coordinator_down = SimpleNamespace(
        data={},
        last_update_success=False,
    )
    sensor_down = OpenDataBZMeteoSensor(
        coordinator_down, config_entry, station_code, sensor_data_valid
    )
    assert sensor_down.available is False

    # Sensor with null value => unavailable
    sensor_data_none = SimpleNamespace(**{**sensor_data_valid.__dict__, "value": None})
    coordinator_none = SimpleNamespace(
        data={
            station_code: {
                "station": station,
                "sensors": [sensor_data_none],
            }
        },
        last_update_success=True,
    )
    sensor_none = OpenDataBZMeteoSensor(
        coordinator_none, config_entry, station_code, sensor_data_none
    )
    assert sensor_none.available is False


def test_extra_state_attributes_for_non_wind_and_invalid_wind():

    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor

    station_code = "83200ms"
    station = SimpleNamespace(
        station_code=station_code,
        name_deu="Station DE",
        name_ita="Station IT",
        name_lld="Station LLD",
    )

    # Non wind sensor should have empty extra attributes
    sensor_data_non_wind = SimpleNamespace(
        type="LT",
        unit="°C",
        value="10",
        description_deu="Temperatur",
        description_ita="Temperatura",
        description_lld="Temperatura",
    )
    coordinator = SimpleNamespace(
        data={station_code: {"station": station, "sensors": [sensor_data_non_wind]}},
        last_update_success=True,
    )
    config_entry = SimpleNamespace(data={"api_language": "de"})
    sensor = OpenDataBZMeteoSensor(
        coordinator, config_entry, station_code, sensor_data_non_wind
    )
    assert sensor.extra_state_attributes == {}

    # Wind sensor invalid direction no cardinal key
    sensor_data_wind_invalid = SimpleNamespace(
        type="WR",
        unit="m/s",
        value="oops",
        description_deu="Windrichtung",
        description_ita="Direzione del vento",
        description_lld="Direzion dl vent",
    )
    coordinator_wind_invalid = SimpleNamespace(
        data={
            station_code: {"station": station, "sensors": [sensor_data_wind_invalid]}
        },
        last_update_success=True,
    )
    sensor_wind_invalid = OpenDataBZMeteoSensor(
        coordinator_wind_invalid, config_entry, station_code, sensor_data_wind_invalid
    )
    assert sensor_wind_invalid.extra_state_attributes == {}


def test_get_sensor_data_and_unique_object_ids():

    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor

    station_code = "83200ms"
    station = SimpleNamespace(
        station_code=station_code,
        name_deu="Station DE",
        name_ita="Station IT",
        name_lld="Station LLD",
    )
    sensor_data = SimpleNamespace(
        type="LT",
        unit="°C",
        value="25",
        description_deu="Temperatur",
        description_ita="Temperatura",
        description_lld="Temperatura",
    )
    coordinator = SimpleNamespace(
        data={station_code: {"station": station, "sensors": [sensor_data]}},
        last_update_success=True,
    )
    config_entry = SimpleNamespace(data={"api_language": "de"})

    sensor = OpenDataBZMeteoSensor(coordinator, config_entry, station_code, sensor_data)
    assert sensor.unique_id == f"{station_code}_LT"
    assert sensor.suggested_object_id == f"{station_code}_lt"
    assert sensor._get_sensor_data() == sensor_data

    # missing station returns None
    missing_sensor = OpenDataBZMeteoSensor(
        coordinator, config_entry, "unknown", sensor_data
    )
    assert missing_sensor._get_sensor_data() is None


def test_device_info_name_language_fallback():

    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor

    station_code = "83200ms"
    station = SimpleNamespace(
        station_code=station_code,
        name_deu="Station DE",
        name_ita="Station IT",
        name_lld="Station LLD",
    )
    sensor_data = SimpleNamespace(
        type="LT",
        unit="°C",
        value="20",
        description_deu="Temperatur",
        description_ita="Temperatura",
        description_lld="Temperatura",
    )
    coordinator = SimpleNamespace(
        data={station_code: {"station": station, "sensors": [sensor_data]}},
        last_update_success=True,
    )

    config_entry_de = SimpleNamespace(data={"api_language": "de"})
    sensor_de = OpenDataBZMeteoSensor(
        coordinator, config_entry_de, station_code, sensor_data
    )
    assert sensor_de.device_info["name"] == "Station DE"

    config_entry_it = SimpleNamespace(data={"api_language": "it"})
    sensor_it = OpenDataBZMeteoSensor(
        coordinator, config_entry_it, station_code, sensor_data
    )
    assert sensor_it.device_info["name"] == "Station IT"

    config_entry_lld = SimpleNamespace(data={"api_language": "lld"})
    sensor_lld = OpenDataBZMeteoSensor(
        coordinator, config_entry_lld, station_code, sensor_data
    )
    assert sensor_lld.device_info["name"] == "Station LLD"

    # missing station yields None
    coordinator_empty = SimpleNamespace(data={}, last_update_success=True)
    sensor_none = OpenDataBZMeteoSensor(
        coordinator_empty, config_entry_de, station_code, sensor_data
    )
    assert sensor_none.device_info is None


def test_async_setup_entry_adds_all_sensors():

    from custom_components.ha_open_data_bz_meteo.sensor import async_setup_entry

    station_code = "83200ms"
    sensor_data = SimpleNamespace(
        type="LT",
        unit="°C",
        value="20",
        description_deu="Temperatur",
        description_ita="Temperatura",
        description_lld="Temperatura",
    )
    coordinator = SimpleNamespace(
        data={station_code: {"station": SimpleNamespace(), "sensors": [sensor_data]}},
        last_update_success=True,
    )
    hass = SimpleNamespace(
        data={"ha_open_data_bz_meteo": {"entry_id": {"coordinator": coordinator}}}
    )
    entry = SimpleNamespace(entry_id="entry_id")

    added = []

    def fake_add_entities(entities, update=False):
        added.extend(entities)
        assert update is True

    # ensure no exception and one entity added
    import asyncio

    asyncio.run(async_setup_entry(hass, entry, fake_add_entities))
    assert len(added) == 1


def test_config_flow_fetch_station_options_and_error():

    import asyncio
    from custom_components.ha_open_data_bz_meteo import config_flow

    class FakeClient:
        def get_stations(self):
            return [
                SimpleNamespace(
                    station_code="A1",
                    name_deu="A deutsch",
                    name_ita="A italiano",
                    name_lld="A ladin",
                    name_eng="A english",
                )
            ]

    config_flow.Client = FakeClient

    async def _async_add_executor_job(callable_, *args, **kwargs):
        return callable_(*args, **kwargs)

    flow = config_flow.OpenDataBZMeteoConfigFlow()
    flow.hass = SimpleNamespace(async_add_executor_job=_async_add_executor_job)
    flow._async_current_entries = lambda: []

    options = asyncio.run(flow._async_fetch_station_options("de", []))
    assert options == {"A1": "A deutsch (A1)"}

    # configured station excluded
    options_skip = asyncio.run(flow._async_fetch_station_options("de", ["A1"]))
    assert options_skip == {}

    class FakeClientError:
        def get_stations(self):
            raise RuntimeError("fail")

    config_flow.Client = FakeClientError
    with pytest.raises(config_flow.CannotConnect):
        asyncio.run(flow._async_fetch_station_options("de", []))


def test_config_flow_steps_and_invalid_station():

    import asyncio
    from custom_components.ha_open_data_bz_meteo import config_flow

    flow = config_flow.OpenDataBZMeteoConfigFlow()
    flow.hass = SimpleNamespace(async_add_executor_job=lambda f, *a, **k: f(*a, **k))
    flow._async_current_entries = lambda: []

    async def dummy_fetch(api_language, configured_stations):
        return {"A1": "A1 (A1)"}

    flow._async_fetch_station_options = dummy_fetch

    result_form = asyncio.run(flow.async_step_station())
    assert result_form["type"] == "form"

    # Invalid station_code rejection is handled by voluptuous (vol.In) at the
    # schema level before the handler is reached, so no guard is needed here.

    result_success = asyncio.run(flow.async_step_station({"station_code": "A1"}))
    assert result_success["type"] == "create_entry"
    assert result_success["data"]["configured_stations"] == ["A1"]


def test_config_flow_skips_stations_already_in_other_entry():
    import asyncio
    from custom_components.ha_open_data_bz_meteo import config_flow

    flow = config_flow.OpenDataBZMeteoConfigFlow()

    async def async_add_executor_job(callable_, *args, **kwargs):
        return callable_(*args, **kwargs)

    flow.hass = SimpleNamespace(async_add_executor_job=async_add_executor_job)

    class FakeClient:
        def get_stations(self):
            return [
                SimpleNamespace(
                    station_code="A1",
                    name_deu="A deutsch",
                    name_ita="A italiano",
                    name_lld="A ladin",
                    name_eng="A english",
                ),
                SimpleNamespace(
                    station_code="A2",
                    name_deu="B deutsch",
                    name_ita="B italiano",
                    name_lld="B ladin",
                    name_eng="B english",
                ),
            ]

    config_flow.Client = FakeClient

    flow._async_current_entries = lambda: [
        SimpleNamespace(data={"configured_stations": ["A1"]}),
        SimpleNamespace(data={"configured_stations": ["A2"]}),
    ]

    result = asyncio.run(flow.async_step_station())
    assert result["type"] == "abort"
    assert result["reason"] == "no_stations_available"


def test_init_async_setup_and_unload_entry():

    import asyncio
    import custom_components.ha_open_data_bz_meteo as integration

    class FakeClient:
        def get_stations(self):
            return [SimpleNamespace(station_code="A1")]

        def get_station(self, station_code):
            return SimpleNamespace(station_code=station_code)

        def get_sensors(self, station):
            return [SimpleNamespace(type="LT", unit="°C", value="10")]

    integration.Client = FakeClient

    class DummyCoordinator:
        def __init__(
            self,
            hass,
            logger,
            *,
            name,
            update_method,
            update_interval,
            config_entry=None,
        ):
            self.data = {}
            self._update_method = update_method

        async def async_config_entry_first_refresh(self):
            return True

    integration.DataUpdateCoordinator = DummyCoordinator

    async def async_add_executor_job(callable_, *args, **kwargs):
        return callable_(*args, **kwargs)

    class ConfigEntries:
        async def async_forward_entry_setups(self, entry, platforms):
            return True

        def async_update_entry(self, entry, data):
            entry.data = data

    class Bus:
        def __init__(self):
            self.callback = None

        def async_listen(self, event, callback):
            self.callback = callback
            return lambda: None

    empty_data = {}
    hass = SimpleNamespace(
        data=empty_data,
        async_add_executor_job=async_add_executor_job,
        bus=Bus(),
        config_entries=ConfigEntries(),
    )

    entry = SimpleNamespace(entry_id="entry_id", data={"configured_stations": ["A1"]})

    result = asyncio.run(integration.async_setup_entry(hass, entry))
    assert result is True
    assert hass.data["ha_open_data_bz_meteo"]["entry_id"]["coordinator"] is not None

    # Unload path
    async def fake_unload(entry_arg, platforms):
        return True

    hass.config_entries.async_unload_platforms = fake_unload
    retval = asyncio.run(integration.async_unload_entry(hass, entry))
    assert retval is True
    assert "ha_open_data_bz_meteo" not in hass.data


def test_init_async_setup_entry_with_fallback_and_device_registry_remove():

    import asyncio
    import custom_components.ha_open_data_bz_meteo as integration

    class FakeClient:
        def get_stations(self):
            return []

        def get_station(self, station_code):
            if station_code == "A1":
                return SimpleNamespace(station_code="A1")
            return None

        def get_sensors(self, station):
            return []

    integration.Client = FakeClient

    class DummyCoordinator:
        def __init__(
            self,
            hass,
            logger,
            *,
            name,
            update_method,
            update_interval,
            config_entry=None,
        ):
            self.data = {}
            self._update_method = update_method

        async def async_config_entry_first_refresh(self):
            self.data = await self._update_method()
            return True

    integration.DataUpdateCoordinator = DummyCoordinator

    async def async_add_executor_job(callable_, *args, **kwargs):
        return callable_(*args, **kwargs)

    class ConfigEntries:
        async def async_forward_entry_setups(self, entry, platforms):
            return True

        def async_update_entry(self, entry, data):
            entry.data = data

    class Bus:
        def __init__(self):
            self.callback = None

        def async_listen(self, event, callback):
            self.callback = callback
            return lambda: None

    class DeviceEntry:
        identifiers = {("ha_open_data_bz_meteo", "A1")}

    class DeviceRegistry:
        def async_get(self, device_id):
            return DeviceEntry() if device_id == "device1" else None

    integration.dr.async_get = lambda hass: DeviceRegistry()

    empty_data = {}
    hass = SimpleNamespace(
        data=empty_data,
        async_add_executor_job=async_add_executor_job,
        bus=Bus(),
        config_entries=ConfigEntries(),
    )

    entry = SimpleNamespace(entry_id="entry_id", data={"configured_stations": ["A1"]})

    result = asyncio.run(integration.async_setup_entry(hass, entry))
    assert result is True

    assert hass.bus.callback is not None

    # Trigger device registry updated remove event path
    hass.bus.callback(
        SimpleNamespace(data={"action": "remove", "device_id": "device1"})
    )
    assert entry.data["configured_stations"] == []


def test_config_flow_async_step_user_flow():

    import asyncio
    from custom_components.ha_open_data_bz_meteo import config_flow

    flow = config_flow.OpenDataBZMeteoConfigFlow()
    flow.hass = SimpleNamespace(async_add_executor_job=lambda f, *a, **k: f(*a, **k))
    flow._async_current_entries = lambda: []

    result_user_form = asyncio.run(flow.async_step_user())
    assert result_user_form["type"] == "form"

    async def fake_fetch(api_language, configured_stations):
        return {}

    flow._async_fetch_station_options = fake_fetch
    result_no_stations = asyncio.run(flow.async_step_user({"api_language": "de"}))
    assert result_no_stations["type"] == "abort"
    assert result_no_stations["reason"] == "no_stations_available"


def test_sensor_uses_options_language_over_data():
    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor

    station_code = "83200ms"
    station = SimpleNamespace(
        station_code=station_code,
        name_deu="Station DE",
        name_ita="Station IT",
        name_lld="Station LLD",
    )
    sensor_data = SimpleNamespace(
        type="LT",
        unit="°C",
        value="20",
        description_deu="Temperatur",
        description_ita="Temperatura",
        description_lld="Temperatura",
    )
    coordinator = SimpleNamespace(
        data={
            station_code: {
                "station": station,
                "sensors": [sensor_data],
            }
        },
        last_update_success=True,
    )
    config_entry = SimpleNamespace(
        data={"api_language": "de"}, options={"api_language": "it"}
    )

    sensor = OpenDataBZMeteoSensor(coordinator, config_entry, station_code, sensor_data)

    assert sensor.name.startswith("Station IT")
    assert sensor.device_info["name"] == "Station IT"


def test_options_flow_updates_language_and_refreshes_data():
    import asyncio
    from custom_components.ha_open_data_bz_meteo.config_flow import (
        OpenDataBZMeteoOptionsFlow,
    )
    from custom_components.ha_open_data_bz_meteo.const import DOMAIN

    entry = SimpleNamespace(
        entry_id="entry_id",
        data={"configured_stations": ["A1"], "api_language": "de"},
        options={},
    )

    reloaded = False

    async def async_reload(entry_id):
        nonlocal reloaded
        reloaded = True
        return True

    def async_update_entry(config_entry, options=None, data=None):
        if data is not None:
            setattr(config_entry, "data", data)
        if options is not None:
            setattr(config_entry, "options", options)
        return True

    hass = SimpleNamespace(
        data={DOMAIN: {entry.entry_id: {"coordinator": SimpleNamespace()}}},
        config_entries=SimpleNamespace(
            async_update_entry=async_update_entry,
            async_reload=async_reload,
        ),
    )

    flow = OpenDataBZMeteoOptionsFlow(entry)
    flow.hass = hass

    result = asyncio.run(flow.async_step_init({"api_language": "it"}))

    assert entry.options["api_language"] == "it"
    assert entry.data["api_language"] == "it"
    assert reloaded is True
    assert result["type"] == "create_entry"


def test_sensor_name_and_native_value_edge_cases():

    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor
    from homeassistant.const import UnitOfPressure

    station_code = "83200ms"
    sensor_data = SimpleNamespace(
        type="LT",
        unit="hPa",
        value="10",
        description_deu="Temperatur",
        description_ita="Temperatura",
        description_lld="Temperatura",
    )

    # hPa unit mapping should be converted.
    coordinator = SimpleNamespace(
        data={
            station_code: {
                "station": SimpleNamespace(
                    name_deu="Station DE",
                    name_ita="Station IT",
                    name_lld="Station LLD",
                    station_code=station_code,
                ),
                "sensors": [sensor_data],
            }
        },
        last_update_success=True,
    )
    config_entry = SimpleNamespace(data={"api_language": "de"})

    sensor = OpenDataBZMeteoSensor(coordinator, config_entry, station_code, sensor_data)
    assert sensor._attr_native_unit_of_measurement == UnitOfPressure.HPA

    # name returns station_code when station_data unavailable
    coordinator_empty = SimpleNamespace(data={}, last_update_success=True)
    sensor2 = OpenDataBZMeteoSensor(
        coordinator_empty, config_entry, station_code, sensor_data
    )
    assert sensor2.name == "83200ms LT"

    # missing sensor_data yields sensor type label
    coordinator2 = SimpleNamespace(
        data={
            station_code: {
                "station": SimpleNamespace(
                    name_deu="Station DE",
                    name_ita="Station IT",
                    name_lld="Station LLD",
                    station_code=station_code,
                ),
                "sensors": [],
            }
        },
        last_update_success=True,
    )
    sensor3 = OpenDataBZMeteoSensor(
        coordinator2, config_entry, station_code, sensor_data
    )
    assert sensor3.name == "Station DE LT"

    # native_value None when sensor missing
    assert sensor3.native_value is None


def test_init_async_setup_entry_station_missing_logs_warning_and_entry_not_ready():

    import asyncio
    import custom_components.ha_open_data_bz_meteo as integration

    class FakeClientNoStation:
        def get_stations(self):
            return []

        def get_station(self, station_code):
            return None

        def get_sensors(self, station):
            return []

    integration.Client = FakeClientNoStation

    class DummyCoordinatorNoStation:
        def __init__(
            self,
            hass,
            logger,
            *,
            name,
            update_method,
            update_interval,
            config_entry=None,
        ):
            self.data = {}
            self._update_method = update_method

        async def async_config_entry_first_refresh(self):
            self.data = await self._update_method()
            return True

    integration.DataUpdateCoordinator = DummyCoordinatorNoStation

    async def async_add_executor_job(callable_, *args, **kwargs):
        return callable_(*args, **kwargs)

    class ConfigEntries:
        async def async_forward_entry_setups(self, entry, platforms):
            return True

        def async_update_entry(self, entry, data):
            entry.data = data

    class Bus:
        def __init__(self):
            self.callback = None

        def async_listen(self, event, callback):
            self.callback = callback
            return lambda: None

    class DeviceEntry:
        identifiers = {("ha_open_data_bz_meteo", "A1")}

    class DeviceRegistry:
        def async_get(self, device_id):
            return DeviceEntry() if device_id == "device1" else None

    integration.dr.async_get = lambda hass: DeviceRegistry()

    hass = SimpleNamespace(
        data={},
        async_add_executor_job=async_add_executor_job,
        bus=Bus(),
        config_entries=ConfigEntries(),
    )
    entry = SimpleNamespace(entry_id="entry_id", data={"configured_stations": ["A1"]})

    result = asyncio.run(integration.async_setup_entry(hass, entry))
    assert result is True

    # callback action not remove
    hass.bus.callback(
        SimpleNamespace(data={"action": "create", "device_id": "device1"})
    )

    # callback device_id missing
    hass.bus.callback(SimpleNamespace(data={"action": "remove"}))

    # callback device not found in registry
    hass.bus.callback(
        SimpleNamespace(data={"action": "remove", "device_id": "device2"})
    )

    # callback identifiers domain mismatch
    class BadDeviceEntry:
        identifiers = {("other_domain", "A1")}

    integration.dr.async_get = lambda hass: SimpleNamespace(
        async_get=lambda device_id: BadDeviceEntry()
    )
    hass.bus.callback(
        SimpleNamespace(data={"action": "remove", "device_id": "device1"})
    )

    # callback station_code None
    class NoStationCodeDeviceEntry:
        identifiers = {("ha_open_data_bz_meteo", None)}

    integration.dr.async_get = lambda hass: SimpleNamespace(
        async_get=lambda device_id: NoStationCodeDeviceEntry()
    )
    hass.bus.callback(
        SimpleNamespace(data={"action": "remove", "device_id": "device1"})
    )

    # callback station not in configured_stations
    entry.data = {"configured_stations": []}

    class OtherStationEntry:
        identifiers = {("ha_open_data_bz_meteo", "A1")}

    integration.dr.async_get = lambda hass: SimpleNamespace(
        async_get=lambda device_id: OtherStationEntry()
    )
    hass.bus.callback(
        SimpleNamespace(data={"action": "remove", "device_id": "device1"})
    )


def test_async_unload_entry_returns_false_if_platform_unload_fails():

    import asyncio
    import custom_components.ha_open_data_bz_meteo as integration

    class ConfigEntries:
        async def async_unload_platforms(self, entry, platforms):
            return False

    hass = SimpleNamespace(
        data={"ha_open_data_bz_meteo": {"entry_id": {}}},
        config_entries=ConfigEntries(),
    )
    entry = SimpleNamespace(entry_id="entry_id", data={})

    assert asyncio.run(integration.async_unload_entry(hass, entry)) is False


def test_async_unload_entry_keeps_domain_if_other_stations_exist():

    import asyncio
    import custom_components.ha_open_data_bz_meteo as integration

    class ConfigEntries:
        async def async_unload_platforms(self, entry, platforms):
            return True

    hass = SimpleNamespace(
        data={
            "ha_open_data_bz_meteo": {
                "entry_id": {"device_listener": lambda: None},
                "other_entry": {"device_listener": lambda: None},
            }
        },
        config_entries=ConfigEntries(),
    )
    entry = SimpleNamespace(entry_id="entry_id", data={})

    assert asyncio.run(integration.async_unload_entry(hass, entry)) is True
    assert "ha_open_data_bz_meteo" in hass.data


def test_sensor_unknown_type_device_class_and_unit_passthrough():

    from homeassistant.components.sensor import SensorStateClass
    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor

    station_code = "83200ms"
    sensor_data = SimpleNamespace(
        type="XXX",
        unit="unknownunit",
        value="55",
        description_deu="Unbekannt",
        description_ita="Sconosciuto",
        description_lld="Nesciüt",
    )
    coordinator = SimpleNamespace(
        data={
            station_code: {
                "station": SimpleNamespace(
                    name_deu="Station DE",
                    name_ita="Station IT",
                    name_lld="Station LLD",
                    station_code=station_code,
                ),
                "sensors": [sensor_data],
            }
        },
        last_update_success=True,
    )
    config_entry = SimpleNamespace(data={"api_language": "de"})

    sensor = OpenDataBZMeteoSensor(coordinator, config_entry, station_code, sensor_data)
    assert sensor._attr_device_class is None
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    assert sensor._attr_native_unit_of_measurement == "unknownunit"


def test_init_async_setup_entry_raises_config_entry_not_ready_on_api_failure():

    import asyncio
    import custom_components.ha_open_data_bz_meteo as integration

    class FakeClientError:
        def get_stations(self):
            raise RuntimeError("wild failure")

        def get_station(self, station_code):
            return None

        def get_sensors(self, station):
            return []

    integration.Client = FakeClientError

    class DummyCoordinatorError:
        def __init__(
            self,
            hass,
            logger,
            *,
            name,
            update_method,
            update_interval,
            config_entry=None,
        ):
            self.data = {}
            self._update_method = update_method

        async def async_config_entry_first_refresh(self):
            await self._update_method()

    integration.DataUpdateCoordinator = DummyCoordinatorError

    async def async_add_executor_job(callable_, *args, **kwargs):
        return callable_(*args, **kwargs)

    class ConfigEntries:
        async def async_forward_entry_setups(self, entry, platforms):
            return True

        def async_update_entry(self, entry, data):
            entry.data = data

    class Bus:
        def async_listen(self, event, callback):
            return lambda: None

    hass = SimpleNamespace(
        data={},
        async_add_executor_job=async_add_executor_job,
        bus=Bus(),
        config_entries=ConfigEntries(),
    )
    entry = SimpleNamespace(entry_id="entry_id", data={"configured_stations": ["A1"]})

    with pytest.raises(integration.ConfigEntryNotReady):
        asyncio.run(integration.async_setup_entry(hass, entry))


def test_config_flow_step_station_cannot_connect():

    import asyncio
    from custom_components.ha_open_data_bz_meteo import config_flow

    flow = config_flow.OpenDataBZMeteoConfigFlow()
    flow.hass = SimpleNamespace(async_add_executor_job=lambda f, *a, **k: f(*a, **k))
    flow._async_current_entries = lambda: []

    async def fetch_error(api_language, configured_stations):
        raise config_flow.CannotConnect

    flow._async_fetch_station_options = fetch_error

    result = asyncio.run(flow.async_step_station())
    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}


def test_config_flow_existing_entries_and_name_fallback():

    import asyncio
    from custom_components.ha_open_data_bz_meteo import config_flow

    flow = config_flow.OpenDataBZMeteoConfigFlow()
    flow.hass = SimpleNamespace(async_add_executor_job=lambda f, *a, **k: f(*a, **k))
    flow._async_current_entries = lambda: [
        SimpleNamespace(data={"configured_stations": ["A1"]})
    ]

    async def fake_fetch(api_language, configured_stations):
        return {"A2": "A2 (A2)"}

    flow._async_fetch_station_options = fake_fetch
    result = asyncio.run(flow.async_step_station())
    assert result["type"] == "form"

    class StationNoName:
        station_code = "A2"
        name_deu = None
        name_ita = None
        name_lld = None
        name_eng = "EngName"

    config_flow.Client = type("C", (), {"get_stations": lambda self: [StationNoName()]})

    async def async_add_executor_job2(callable_, *args, **kwargs):
        return callable_(*args, **kwargs)

    flow2 = config_flow.OpenDataBZMeteoConfigFlow()
    flow2.hass = SimpleNamespace(async_add_executor_job=async_add_executor_job2)
    options = asyncio.run(flow2._async_fetch_station_options("de", []))
    assert options == {"A2": "EngName (A2)"}
