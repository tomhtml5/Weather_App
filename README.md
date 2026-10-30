# City Weather

A small Flask app that looks up a city and displays its current weather with a condition icon. Weather and geocoding data come from [Open-Meteo](https://open-meteo.com/); no API key is required.

## Run locally

Requires Python 3.10 or newer.

1. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies and start Flask:

   ```powershell
   pip install -r requirements.txt
   flask --app app run --debug
   ```

3. Open http://127.0.0.1:5000 and search for a city.

## Tests

Run the automated tests with:

```powershell
python -m unittest discover -s tests
```
