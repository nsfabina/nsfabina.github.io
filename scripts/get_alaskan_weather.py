"""
Note:  This script is disorganized, but it serves its purpose and there are no bonus points for aesthetics.
"""

import argparse
import datetime
import json
import re
import requests

import pytz


# To request data
_URL_WU_API_BASE = 'http://api.wunderground.com/api/{key}/{feature}/q/{query}.json'
_URL_MARINE_FORECAST = 'http://tgftp.nws.noaa.gov/data/raw/fz/fzak51.pafc.cwf.aer.txt'
_SEPARATOR_MARINE_FORECAST = '\$\$'

# To format API URLs for specific location
_LATLONS = {'anchor_point': '59.7775,-151.7702',
            'anchorage': '61.2167,-149.9000',
            'cooper_landing': '60.4905,-149.7944',
            'homer': '59.6425,-152.5483',
            'kachemak_bay_seldovia': '59.4394,-151.7122',
            'kenai': '60.5586,-151.2297',
            'kenai_river': '60.5439,-151.2786',
            'nanwalek': '59.3536,-151.9125',
            'ninilchik': '60.04638,-151.6672',
            'port_graham': '59.3477,-151.8333',
            'soldotna': '60.4866,-151.07527',
            'western_kenai_peninsula': '59.8861,-151.6338'
            }

# To order output
_ORDER_CURRENT_TEMPERATURE = [
    ('homer', 'Homer'),
    ('anchor_point', 'Anchor Point'),
    ('ninilchik', 'Ninilchik'),
    ('kachemak_bay_seldovia', 'Seldovia'),
    ('port_graham', 'Port Graham'),
    ('nanwalek', 'Nanwalek'),
    ('kenai', 'Kenai'),
    ('soldotna', 'Soldotna'),
    ('cooper_landing', 'Cooper Landing'),
    ('anchorage', 'Anchorage')
]
_ORDER_FORECAST = [
    ('western_kenai_peninsula', 'Western Kenai Peninsula'),
    ('anchorage', 'Anchorage')
]
_ORDER_MARINE_FORECAST = [
    'KACHEMAK BAY',
    'COOK INLET NORTH OF KALGIN ISLAND',
    'COOK INLET KALGIN ISLAND TO POINT BEDE',
    'SHELIKOF STRAIT',
    'BARREN ISLANDS EAST',
    'WEST OF BARREN ISLANDS INCLUDING KAMISHAK BAY',
    'CAPE CLEARE TO GORE POINT',
]


# To convert datetimes
_TIMEZONE_UTC = pytz.timezone('UTC')
_TIMEZONE_AK = pytz.timezone('US/Alaska')

# To access API data
_KEY_SUNRISE = 'Sunrise'
_KEY_SUNSET = 'Sunset'
_KEY_TIDE_HIGH = 'High Tide'
_KEY_TIDE_LOW = 'Low Tide'
_KEY_HOUR = 'hour'
_KEY_MINUTE = 'minute'
_KEY_TIDE_HEIGHT = 'height'

# To output information
_STRING_DAYLIGHT = """
Daylight {month:0>2d}/{day:0>2d}
  Sunrise:  {sunrise_hour:0>2d}:{sunrise_minute:0>2d}
  Sunset:   {sunset_hour:0>2d}:{sunset_minute:0>2d}
  Total:    {total_hours} hours and {total_minutes} minutes

"""

_STRING_TIDES = """
Tides
  Kachemak Bay, Seldovia
{kachemak_bay_seldovia_detail}
  Kenai River
{kenai_river_detail}
"""

_STRING_TIDES_DETAIL = """    {month:0>2d}/{day:0>2d}
      High tide:  {high_hour}:{high_minute} ({high_height})
      Low tide:   {low_hour}:{low_minute} ({low_height})
"""

_STRING_CURRENT_TEMPERATURE = """
Current temperature
{current_temperature_detail}
"""

_STRING_CURRENT_TEMPERATURE_DETAIL = """  {city:<{padding}s}  {temperature:.0f}
"""

_STRING_FORECAST = """
Forecast
  Western Kenai Peninsula
{western_kenai_peninsula_detail}
  Anchorage
{anchorage_detail}
"""

_STRING_FORECAST_DETAIL = """    {title}:  {forecast}
"""


def get_sunphase_and_tides():
    key_locations = ['kachemak_bay_seldovia', 'kenai_river']
    tide_string_details = {}
    for key_location in key_locations:
        raw_data_tides = _get_tide_data_from_weather_underground(key_location)
        if key_location == 'kenai_river':
            sunrise, sunset = _format_sunphase_data(raw_data_tides)
            daylight_hours, daylight_minutes = _get_total_daylight_hours_and_minutes(sunset - sunrise)
        data_tides = _format_tide_data(raw_data_tides)
        location_details = _format_tide_detail_strings(data_tides)
        tide_string_details[key_location + '_detail'] = location_details
    return _STRING_DAYLIGHT.format(
            month=sunrise.month, day=sunrise.day, sunrise_hour=sunrise.hour, sunrise_minute=sunrise.minute,
            sunset_hour=sunset.hour, sunset_minute=sunset.minute, total_hours=daylight_hours,
            total_minutes=daylight_minutes) + \
        _STRING_TIDES.format(**tide_string_details)


def _get_tide_data_from_weather_underground(key_location):
    url = _URL_WU_API_BASE.format(key=_KEY, feature='tide', query=_LATLONS[key_location])
    return json.loads(requests.get(url).text)


def _format_sunphase_data(raw_data_tides):
    sunrise_hour = 0
    sunrise_minute = 0
    sunset_hour = 0
    sunset_minute = 0
    year, month, day = _get_tomorrow_datetime_in_alaska_tz()
    for datum in raw_data_tides['tide']['tideSummary']:
        date = datum['date']
        if (int(date['year']), int(date['mon']), int(date['mday'])) != (year, month, day):
            continue
        hour = int(date['hour'])
        minute = int(date['min'])
        if datum['data']['type'] == _KEY_SUNRISE:
            sunrise_hour, sunrise_minute = (hour, minute)
        if datum['data']['type'] == _KEY_SUNSET:
            sunset_hour, sunset_minute = (hour, minute)
    sunrise = datetime.datetime(year, month, day, sunrise_hour, sunrise_minute)
    sunset = datetime.datetime(year, month, day, sunset_hour, sunset_minute)
    return sunrise, sunset


def _get_tomorrow_datetime_in_alaska_tz():
    datetime_utc = datetime.datetime.utcnow().replace(tzinfo=_TIMEZONE_UTC)
    datetime_ak = datetime_utc.astimezone(_TIMEZONE_AK)
    datetime_tomorrow = datetime_ak + datetime.timedelta(days=1)
    return datetime_tomorrow.year, datetime_tomorrow.month, datetime_tomorrow.day


def _get_total_daylight_hours_and_minutes(datetime_delta):
    daylight_raw_minutes = datetime_delta.total_seconds() / 60
    daylight_hours = int(daylight_raw_minutes / 60)
    daylight_minutes = int(daylight_raw_minutes % 60)
    return daylight_hours, daylight_minutes


def _format_tide_data(raw_data_tides):
    data_tides = {}
    for datum in raw_data_tides['tide']['tideSummary']:
        if datum['data']['type'] not in [_KEY_TIDE_HIGH, _KEY_TIDE_LOW]:
            continue
        date = datum['date']
        datetime_ak = datetime.datetime(int(date['year']), int(date['mon']), int(date['mday']))
        data_tides.setdefault(datetime_ak, {})[datum['data']['type']] = \
            {_KEY_HOUR: date['hour'],
             _KEY_MINUTE: date['min'],
             _KEY_TIDE_HEIGHT: datum['data']['height']}
    return data_tides


def _format_tide_detail_strings(data_tides):
    tide_string_details = []
    for datetime_ak, datum in sorted(data_tides.items(), key=lambda dt: dt[0]):
        tide_high = datum.get(_KEY_TIDE_HIGH, {})
        tide_low = datum.get(_KEY_TIDE_LOW, {})
        tide_string_details.append(
            _STRING_TIDES_DETAIL.format(
                month=datetime_ak.month,
                day=datetime_ak.day,
                high_hour=tide_high.get(_KEY_HOUR, 'XX'),
                high_minute=tide_high.get(_KEY_MINUTE, 'XX'),
                high_height=tide_high.get(_KEY_TIDE_HEIGHT, 'XX'),
                low_hour=tide_low.get(_KEY_HOUR, 'XX'),
                low_minute=tide_low.get(_KEY_MINUTE, 'XX'),
                low_height=tide_low.get(_KEY_TIDE_HEIGHT, 'XX')
                ))
    return ''.join(tide_string_details)


def get_current_temperature():
    string_padding = max(len(city) for _, city in _ORDER_CURRENT_TEMPERATURE)
    string_temperature_details = []
    for key, city in _ORDER_CURRENT_TEMPERATURE:
        raw_temp = _get_current_temperature_data_from_weather_underground(key)
        city_detail = _STRING_CURRENT_TEMPERATURE_DETAIL.format(
            city=city + ':', padding=string_padding, temperature=raw_temp)
        string_temperature_details.append(city_detail)
    return _STRING_CURRENT_TEMPERATURE.format(current_temperature_detail=''.join(string_temperature_details))


def _get_current_temperature_data_from_weather_underground(key_location):
    url = _URL_WU_API_BASE.format(key=_KEY, feature='conditions', query=_LATLONS[key_location])
    return json.loads(requests.get(url).text)['current_observation']['temp_f']


def get_forecast():
    location_details = {}
    for key, name in _ORDER_FORECAST:
        raw_data_forecast = _get_forecast_data_from_weather_underground(key)
        data_forecast = _format_forecast_data(raw_data_forecast)
        location_details[key + '_detail'] = ''.join(
            _STRING_FORECAST_DETAIL.format(title=title, forecast=forecast)
            for title, forecast in data_forecast)
    return _STRING_FORECAST.format(**location_details)


def _get_forecast_data_from_weather_underground(key_location):
    url = _URL_WU_API_BASE.format(key=_KEY, feature='forecast', query=_LATLONS[key_location])
    return json.loads(requests.get(url).text)


def _format_forecast_data(raw_data_forecast):
    data_forecast = []
    for datum in raw_data_forecast['forecast']['txt_forecast']['forecastday']:
        if datum['period'] == 4:
            break
        data_forecast.append((datum['title'], datum['fcttext']))
    return data_forecast


def get_marine_forecast():
    # Get and split the raw text into forecasts for individual locations
    raw_text = requests.get(_URL_MARINE_FORECAST).text
    split_text = re.split(_SEPARATOR_MARINE_FORECAST, raw_text)
    # Sort forecasts for select locations
    ordered_forecasts = []
    for location in _ORDER_MARINE_FORECAST:
        idx_found = [bool(re.search(location, forecast))
                     for forecast in split_text].index(True)
        ordered_forecasts.append(split_text[idx_found])
    return ''.join(ordered_forecasts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('type', metavar='weather_type', type=str, choices=['daily', 'current', 'marine'],
                        help='either "daily", "current", or "marine"')
    type_ = parser.parse_args().type
    print('IMPORTANT:  DO NOT USE THIS SCRIPT MORE THAN ONCE EVERY HALF HOUR')
    output = ''
    if type_ == 'daily':
        output = get_sunphase_and_tides() + get_forecast()
    elif type_ == 'current':
        output = get_current_temperature()
    elif type_ == 'marine':
        output = get_marine_forecast()
    print(output)
