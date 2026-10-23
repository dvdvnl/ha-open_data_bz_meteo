from types import SimpleNamespace

import pytest


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


def test_sensor_name_and_native_value_edge_cases():

    from homeassistant.const import UnitOfPressure

    from custom_components.ha_open_data_bz_meteo.sensor import OpenDataBZMeteoSensor

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
    entry = SimpleNamespace(entry_id="entry_id", options={}, data={})

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
    entry = SimpleNamespace(entry_id="entry_id", options={}, data={})

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
        def __init__(self, base_url=None):
            self.base_url = base_url

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
    entry = SimpleNamespace(
        entry_id="entry_id", options={}, data={"configured_stations": ["A1"]}
    )

    with pytest.raises(integration.ConfigEntryNotReady):
        asyncio.run(integration.async_setup_entry(hass, entry))


# --- Single config entry with station subentries ---------------------------

from types import MappingProxyType  # noqa: E402

from homeassistant.config_entries import ConfigSubentry  # noqa: E402


def _subentry(code):
    return ConfigSubentry(
        data=MappingProxyType({"station_code": code}),
        subentry_type="station",
        title=code,
        unique_id=code,
    )


def _entry(codes, data=None, options=None):
    subentries = {s.subentry_id: s for s in map(_subentry, codes)}
    return SimpleNamespace(
        entry_id="entry_id",
        data=data or {"api_language": "de", "api_url": "https://example.test/v1"},
        options=options or {},
        subentries=subentries,
    )


def _station(code, name=None):
    return SimpleNamespace(
        station_code=code,
        name_deu=name,
        name_ita=name,
        name_lld=name,
        name_eng=f"{code} eng",
    )


async def _run_in_executor(callable_, *args, **kwargs):
    return callable_(*args, **kwargs)


def _fake_client(stations, record=None, fail=False):
    class FakeClient:
        def __init__(self, base_url=None):
            if record is not None:
                record.append(base_url)

        def get_stations(self):
            if fail:
                raise RuntimeError("fail")
            return stations

        def get_station(self, station_code):
            return next((s for s in stations if s.station_code == station_code), None)

        def get_sensors(self, station):
            return [SimpleNamespace(type="LT", unit="°C", value="10")]

    return FakeClient


def test_sensor_platform_adds_entities_per_subentry():
    import asyncio

    from custom_components.ha_open_data_bz_meteo.sensor import async_setup_entry

    sensor_data = SimpleNamespace(
        type="LT",
        unit="°C",
        value="20",
        description_deu="T",
        description_ita="T",
        description_lld="T",
    )
    coordinator = SimpleNamespace(
        data={"A1": {"station": SimpleNamespace(), "sensors": [sensor_data]}},
        last_update_success=True,
    )
    entry = _entry(["A1", "MISSING"])
    hass = SimpleNamespace(
        data={"ha_open_data_bz_meteo": {"entry_id": {"coordinator": coordinator}}}
    )

    added = []

    def fake_add_entities(entities, update=False, *, config_subentry_id=None):
        assert update is True
        added.append((len(entities), config_subentry_id))

    asyncio.run(async_setup_entry(hass, entry, fake_add_entities))

    a1_id = next(
        s.subentry_id for s in entry.subentries.values() if s.unique_id == "A1"
    )
    assert added == [(1, a1_id)]


def test_fetch_station_options_and_errors():
    import asyncio

    from custom_components.ha_open_data_bz_meteo import config_flow

    calls = []
    hass = SimpleNamespace(async_add_executor_job=_run_in_executor)
    stations = [_station("B2", "Bravo"), _station("A1", "Alpha"), _station("C3")]
    config_flow.Client = _fake_client(stations, calls)

    options = asyncio.run(
        config_flow.async_fetch_station_options(hass, "https://x/v1", "de", ["B2"])
    )
    assert options == {"A1": "Alpha (A1)", "C3": "C3 eng (C3)"}
    assert calls == ["https://x/v1"]

    config_flow.Client = _fake_client([], fail=True)
    with pytest.raises(config_flow.CannotConnect):
        asyncio.run(config_flow.async_fetch_station_options(hass, "u", "de", []))


def test_config_flow_user_step_creates_entry_or_shows_error():
    import asyncio

    from custom_components.ha_open_data_bz_meteo import config_flow

    flow = config_flow.OpenDataBZMeteoConfigFlow()
    flow.hass = SimpleNamespace(async_add_executor_job=_run_in_executor)

    form = asyncio.run(flow.async_step_user())
    assert form["type"] == "form"

    user_input = {"api_language": "it", "api_url": " https://x/v1 "}

    config_flow.Client = _fake_client([], fail=True)
    failed = asyncio.run(flow.async_step_user(user_input))
    assert failed["type"] == "form"
    assert failed["errors"] == {"base": "cannot_connect"}

    config_flow.Client = _fake_client([_station("A1", "Alpha")])
    created = asyncio.run(flow.async_step_user(user_input))
    assert created["type"] == "create_entry"
    assert created["data"] == {"api_language": "it", "api_url": "https://x/v1"}
    assert flow.VERSION == 2


def test_station_subentry_flow():
    import asyncio

    from custom_components.ha_open_data_bz_meteo import config_flow

    entry = _entry(["A1"])
    flow = config_flow.StationSubentryFlowHandler()
    flow.hass = SimpleNamespace(async_add_executor_job=_run_in_executor)
    flow._get_entry = lambda: entry
    flow.context = {"source": "user"}
    flow.handler = ("entry_id", "station")

    calls = []
    config_flow.Client = _fake_client(
        [_station("A1", "Alpha"), _station("B2", "Bravo")], calls
    )

    form = asyncio.run(flow.async_step_user())
    assert form["type"] == "form"
    assert list(form["data_schema"].schema["station_code"].container) == ["B2"]
    assert calls == ["https://example.test/v1"]

    created = asyncio.run(flow.async_step_user({"station_code": "B2"}))
    assert created["type"] == "create_entry"
    assert created["data"] == {"station_code": "B2"}
    assert created["unique_id"] == "B2"
    assert created["title"] == "Bravo (B2)"

    config_flow.Client = _fake_client([_station("A1", "Alpha")])
    assert asyncio.run(flow.async_step_user())["reason"] == "no_stations_available"

    config_flow.Client = _fake_client([], fail=True)
    assert asyncio.run(flow.async_step_user())["reason"] == "cannot_connect"


def test_subentry_types_registered():
    from custom_components.ha_open_data_bz_meteo import config_flow

    types = config_flow.OpenDataBZMeteoConfigFlow.async_get_supported_subentry_types(
        _entry([])
    )
    assert types == {"station": config_flow.StationSubentryFlowHandler}


def test_options_flow_saves_language_and_url():
    import asyncio

    from custom_components.ha_open_data_bz_meteo.config_flow import (
        OpenDataBZMeteoOptionsFlow,
    )

    entry = _entry(["A1"])
    flow = OpenDataBZMeteoOptionsFlow(entry)

    form = asyncio.run(flow.async_step_init())
    assert form["type"] == "form"

    result = asyncio.run(
        flow.async_step_init({"api_language": "it", "api_url": " https://y/v1 "})
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {"api_language": "it", "api_url": "https://y/v1"}


def _setup_integration(monkeypatch, stations, record=None, fail=False):
    import custom_components.ha_open_data_bz_meteo as integration

    monkeypatch.setattr(integration, "Client", _fake_client(stations, record, fail))

    class DummyCoordinator:
        def __init__(self, hass, logger, *, update_method, **kwargs):
            self.data = {}
            self._update_method = update_method

        async def async_config_entry_first_refresh(self):
            self.data = await self._update_method()

    monkeypatch.setattr(integration, "DataUpdateCoordinator", DummyCoordinator)

    class ConfigEntries:
        async def async_forward_entry_setups(self, entry, platforms):
            return True

        async def async_unload_platforms(self, entry, platforms):
            return True

        def async_update_subentry(self, entry, subentry, *, title):
            object.__setattr__(subentry, "title", title)

    hass = SimpleNamespace(
        data={},
        async_add_executor_job=_run_in_executor,
        config_entries=ConfigEntries(),
    )
    return integration, hass


def test_setup_and_unload_entry(monkeypatch):
    import asyncio

    calls = []
    integration, hass = _setup_integration(monkeypatch, [_station("A1")], calls)
    entry = _entry(["A1"])
    listeners = []
    entry.add_update_listener = lambda cb: cb
    entry.async_on_unload = listeners.append

    assert asyncio.run(integration.async_setup_entry(hass, entry)) is True
    assert calls == ["https://example.test/v1"]
    coordinator = hass.data["ha_open_data_bz_meteo"]["entry_id"]["coordinator"]
    assert list(coordinator.data) == ["A1"]
    assert listeners == [integration._async_update_listener]

    assert asyncio.run(integration.async_unload_entry(hass, entry)) is True
    assert "ha_open_data_bz_meteo" not in hass.data


def test_setup_options_override_url_and_station_fallback(monkeypatch):
    import asyncio

    calls = []
    integration, hass = _setup_integration(monkeypatch, [], calls)
    entry = _entry(["A1"], options={"api_url": "https://opt/v1"})
    entry.add_update_listener = lambda cb: cb
    entry.async_on_unload = lambda cb: None

    # Station absent from the list and from get_station: skipped with warning.
    asyncio.run(integration.async_setup_entry(hass, entry))
    assert calls == ["https://opt/v1"]
    coordinator = hass.data["ha_open_data_bz_meteo"]["entry_id"]["coordinator"]
    assert coordinator.data == {}


def test_setup_raises_not_ready_on_api_failure(monkeypatch):
    import asyncio

    integration, hass = _setup_integration(monkeypatch, [], fail=True)
    entry = _entry(["A1"])

    with pytest.raises(integration.ConfigEntryNotReady):
        asyncio.run(integration.async_setup_entry(hass, entry))


def test_update_listener_reloads_entry():
    import asyncio

    import custom_components.ha_open_data_bz_meteo as integration

    reloaded = []

    async def async_reload(entry_id):
        reloaded.append(entry_id)

    hass = SimpleNamespace(config_entries=SimpleNamespace(async_reload=async_reload))
    asyncio.run(integration._async_update_listener(hass, _entry([])))
    assert reloaded == ["entry_id"]


def test_migration_merges_station_entries_into_subentries():
    import asyncio
    import tempfile

    from homeassistant import config_entries as ce
    from homeassistant import loader
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import area_registry as ar
    from homeassistant.helpers import category_registry as cr
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers import floor_registry as fr
    from homeassistant.helpers import issue_registry as ir
    from homeassistant.helpers import label_registry as lr

    import custom_components.ha_open_data_bz_meteo as integration

    domain = "ha_open_data_bz_meteo"

    async def scenario():
        config_dir = tempfile.mkdtemp()
        hass = HomeAssistant(config_dir)
        hass.config.config_dir = config_dir
        hass.config_entries = ce.ConfigEntries(hass, {})
        loader.async_setup(hass)
        registries = (ar, fr, lr, cr, dr, er, ir)
        for registry in registries:
            if hasattr(registry, "async_setup"):
                registry.async_setup(hass)
        for registry in registries:
            await registry.async_load(hass)

        def legacy_entry(code, language):
            entry = ConfigEntry(
                data={"configured_stations": [code], "api_language": language},
                discovery_keys={},
                domain=domain,
                minor_version=1,
                options={},
                source="user",
                subentries_data=None,
                title="OPENdata BZ Meteo",
                unique_id=None,
                version=1,
            )
            hass.config_entries._entries[entry.entry_id] = entry
            device = dr.async_get(hass).async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(domain, code)},
                name=code,
            )
            for sensor in ("LT", "LD.RED"):
                er.async_get(hass).async_get_or_create(
                    "sensor",
                    domain,
                    f"{code}_{sensor}",
                    config_entry=entry,
                    device_id=device.id,
                )
            return entry

        legacy_entry("A1", "it")
        legacy_entry("B2", "de")
        await integration.async_setup(hass, {})
        # Running again must be a no-op.
        await integration.async_setup(hass, {})
        return hass

    hass = asyncio.run(scenario())

    (entry,) = hass.config_entries.async_entries(domain)
    assert entry.version == 2
    assert entry.data["api_language"] == "it"
    assert entry.data["api_url"].startswith("https://")
    by_code = {s.data["station_code"]: s.subentry_id for s in entry.subentries.values()}
    assert set(by_code) == {"A1", "B2"}

    entities = er.async_get(hass).entities.values()
    assert {e.unique_id for e in entities} == {
        "A1_LT",
        "A1_LD.RED",
        "B2_LT",
        "B2_LD.RED",
    }
    for e in entities:
        assert e.config_entry_id == entry.entry_id
        assert e.config_subentry_id == by_code[e.unique_id.split("_")[0]]
    for d in dr.async_get(hass).devices.values():
        assert d.config_entry_id == entry.entry_id
        assert d.config_subentry_id == by_code[d.name]


def test_subentry_titles_follow_language(monkeypatch):
    import asyncio

    station = SimpleNamespace(
        station_code="A1",
        name_deu="Alpha DE",
        name_ita="Alpha IT",
        name_lld=None,
        name_eng="Alpha EN",
    )
    integration, hass = _setup_integration(monkeypatch, [station])
    entry = _entry(["A1"])
    entry.add_update_listener = lambda cb: cb
    entry.async_on_unload = lambda cb: None
    titles = lambda: [s.title for s in entry.subentries.values()]  # noqa: E731

    asyncio.run(integration.async_setup_entry(hass, entry))
    assert titles() == ["Alpha DE (A1)"]

    entry.options = {"api_language": "it"}
    asyncio.run(integration.async_setup_entry(hass, entry))
    assert titles() == ["Alpha IT (A1)"]

    entry.options = {"api_language": "lld"}
    asyncio.run(integration.async_setup_entry(hass, entry))
    assert titles() == ["Alpha EN (A1)"]
