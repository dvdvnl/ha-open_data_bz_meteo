# Home Assistant - Open Data BZ Meteo

This integration provides weather station data provided by _Provincia autonoma di Bolzano - Informatica Alto Adige SPA_ to Home Assistant. The API documentation can be found [here](https://data.civis.bz.it/dataset/misure-meteo-e-idrografiche).

## Development

### Dependencies

This integration depends on the [_OPENdata BZ Meteo_ Python client](https://github.com/dvdvnl/open_data_bz_meteo) to fetch station and sensor data from the OPENdata API provided by the Provincia autonoma di Bolzano.

### Devcontainer

Provide the name of the SSH key file to the Docker devcontainer via `SSH_KEYFILE`.
