import unittest
from unittest.mock import Mock, patch

import app as weather_app


class WeatherPageTests(unittest.TestCase):
    def setUp(self):
        weather_app.app.config.update(TESTING=True)
        self.client = weather_app.app.test_client()

    @patch("app.fetch_weather")
    def test_search_displays_weather_and_icon(self, fetch_weather):
        fetch_weather.return_value = {
            "location": "Oslo, Oslo County, Norway",
            "temperature": 12,
            "feels_like": 10,
            "humidity": 60,
            "precipitation": 0,
            "wind_speed": 8,
            "condition": "Partly cloudy",
            "icon": "⛅",
        }

        response = self.client.post("/", data={"city": "Oslo"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Oslo, Oslo County, Norway", response.data)
        self.assertIn("⛅".encode(), response.data)
        self.assertIn(b"Partly cloudy", response.data)

    @patch("app.fetch_weather")
    def test_empty_city_is_rejected_without_fetching(self, fetch_weather):
        response = self.client.post("/", data={"city": "  "})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Enter a city", response.data)
        fetch_weather.assert_not_called()

    @patch("app.fetch_weather", return_value=None)
    def test_unknown_city_shows_not_found_message(self, _fetch_weather):
        response = self.client.post("/", data={"city": "No Such City"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"couldn&#39;t find", response.data)

    @patch("app.fetch_weather", side_effect=weather_app.WeatherServiceError("Weather service is down."))
    def test_service_error_is_shown(self, _fetch_weather):
        response = self.client.post("/", data={"city": "Oslo"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Weather service is down.", response.data)

    @patch("app.fetch_weather")
    def test_city_longer_than_limit_is_rejected(self, fetch_weather):
        response = self.client.post("/", data={"city": "a" * 101})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"100 characters or fewer", response.data)
        fetch_weather.assert_not_called()


class WeatherLookupTests(unittest.TestCase):
    @patch("app.requests.get")
    def test_lookup_requests_location_and_current_conditions(self, get):
        geocoding_response = Mock()
        geocoding_response.json.return_value = {
            "results": [
                {
                    "name": "Oslo",
                    "admin1": "Oslo County",
                    "country": "Norway",
                    "latitude": 59.91,
                    "longitude": 10.75,
                }
            ]
        }
        weather_response = Mock()
        weather_response.json.return_value = {
            "current": {
                "temperature_2m": 12.4,
                "apparent_temperature": 10.2,
                "relative_humidity_2m": 60,
                "precipitation": 0,
                "wind_speed_10m": 8.1,
                "weather_code": 2,
            }
        }
        get.side_effect = [geocoding_response, weather_response]

        result = weather_app.fetch_weather("Oslo")

        self.assertIsNotNone(result)
        self.assertEqual(result["condition"], "Partly cloudy")
        self.assertEqual(result["icon"], "⛅")
        self.assertEqual(result["location"], "Oslo, Oslo County, Norway")
        self.assertEqual(get.call_count, 2)
        geocoding_response.raise_for_status.assert_called_once()
        weather_response.raise_for_status.assert_called_once()

    @patch("app.requests.get")
    def test_lookup_returns_none_when_city_is_not_found(self, get):
        response = Mock()
        response.json.return_value = {"results": []}
        get.return_value = response

        self.assertIsNone(weather_app.fetch_weather("No Such City"))
        self.assertEqual(get.call_count, 1)

    @patch("app.requests.get")
    def test_provider_failure_raises_service_error(self, get):
        get.side_effect = weather_app.requests.Timeout()

        with self.assertRaises(weather_app.WeatherServiceError):
            weather_app.fetch_weather("Oslo")


if __name__ == "__main__":
    unittest.main()
