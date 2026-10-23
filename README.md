# Home Assistant - Open Data BZ Meteo

This integration provides weather station data provided by _Provincia autonoma di Bolzano - Informatica Alto Adige SPA_ to Home Assistant. The API documentation can be found [here](https://data.civis.bz.it/dataset/misure-meteo-e-idrografiche).

## Installation

Install as a custom repository, or copy `custom_components/ha_open_data_bz_meteo` into your Home Assistant `custom_components` folder, then restart Home Assistant.

## Configuration

The integration is set up through the UI and uses a **single config entry** that holds the shared settings. Weather stations are added to it as sub-entries.

1. Go to **Settings > Devices & services > Add integration** and search for _OPENdata BZ - Meteo_.
2. Choose the **language** (German, Italian or Ladin) used for station names and sensor descriptions, and the **API URL**. The default is `https://geoservices.buergernetz.bz.it/services/meteo/v1`. The URL is checked by fetching the station list.
3. On the integration page choose **Add station** and select a station. Repeat for every station you want. Stations that are already added are not offered again.

To change the language or API URL, open the integration's **Configure** dialog. The change applies to all stations at once, and the station sub-entries are renamed to the new language. Remove a station by deleting its sub-entry.

### Upgrading from earlier versions

Earlier versions created one config entry per station. On the first start after updating, these are merged automatically into one entry with one sub-entry per station. The language and API URL of the first entry are kept. Devices and entities keep their IDs and history.

Requires Home Assistant 2026.8.0 or newer.

## Development

### Dependencies

This integration depends on the [_OPENdata BZ Meteo_ Python client](https://github.com/dvdvnl/open_data_bz_meteo) to fetch station and sensor data from the OPENdata API provided by the Provincia autonoma di Bolzano.

### Devcontainer

Provide the name of the SSH key file to the Docker devcontainer via `SSH_KEYFILE`.

### Tests

Run tests with `pytest --cov`.
