#!/usr/bin/env python
import sys
import time
import datetime
import json

# NB you need to install these python libraries
import nest
import influxdb
import pyowm
from influxdb import client as influxdb
from pyowm.utils import temputils

class WeatherObj(object):
    def __init__(self, data):
	    self.__dict__ = json.loads(data)

# Replace them with your own unique values
# The w_api_key is from OpenWeatherMap.org
# NB: Move these into a configuration file to make things
#     easier to read and manage.

n_id = 'b165a15c-8ecf-4b77-97c0-e5027c7d94e2'
n_secret = 'V5Rkm5xnWpRKpjoYvJgSyMe9L'
n_cache_file = '.config/nest/token_cache'
n_pin = '6FTGREKE'

# Tahoe
n_lat = 39.293528 
n_long = -120.120746 

# Mt View
#n_lat = 37.3861
#n_long = -122.0839

db_server = 'tick-server.312woodland.ddns.net'
db_port = 8086
db_user = 'influx'
db_pwd = 'influx_pass'
db_name = 'nest'
w_api_key = 'd168bb3ff17b6e05e2b1cf267b22866e'
w_location = 'Truckee,us'

series = []

db = influxdb.InfluxDBClient(db_server, db_port, db_user, db_pwd)
db_list = db.get_list_database()
if db_name not in [str(x['name']) for x in db_list]:
    db_err = db.create_database(db_name)
db.switch_database(db_name)

napi = nest.Nest(client_id=n_id,client_secret=n_secret, access_token_cache_file=n_cache_file)
# In interactive mode, this would ask for a pin code
if napi.authorization_required:
    napi.request_token(n_pin)


''' Grab the Nest Thermstat information and store in the defined InfluxDB '''
for structure in napi.structures:
    Location = structure.name
    Home_Away = structure.away
    for device in structure.thermostats:
        json_body = {
                "measurement": "temperature",
                "tags": {
                    "location": structure.name,
                    "device": device.name,
                },
                "fields": {
                    "home_away": structure.away,
                    "online": device.online,
                    "emergency_heat": device.is_using_emergency_heat,
                    "mode": device.mode,
                    "state": device.hvac_state,
                    "current": float(device.temperature),
                    "target": float(device.target),
                    "high": float(device.eco_temperature.high),
                    "low": float(device.eco_temperature.low),
                    "humidity": float(device.humidity),
                },
            }
        series.append(json_body)

        ''' get the weather information for the specified location'''
        owm = pyowm.OWM(w_api_key)
        obs = owm.weather_at_coords(n_lat, n_long)
        wx = obs.get_weather()
        wx_data = wx.to_JSON()
        wx_obj = WeatherObj(wx_data)

        wx_json_body = {
            "measurement": "weather",
            "tags": {
                "location": structure.name,
                "device": device.name,
            },
            "fields": {
                "humidity":    float(wx_obj.humidity),
                "status":      wx_obj.detailed_status,
                "cur_temp":    float(temputils.kelvin_to_fahrenheit(wx_obj.temperature['temp'])),
                "max_temp":    float(temputils.kelvin_to_fahrenheit(wx_obj.temperature['temp_max'])),
                "min_temp":    float(temputils.kelvin_to_fahrenheit(wx_obj.temperature['temp_min'])),
                "cloud_cover": wx_obj.clouds,
                "wind_speed":  float(wx_obj.wind['speed']),
                "wind_degree": float(wx_obj.wind['deg']),
                "sunrise":     wx_obj.sunrise_time,
                "sunset":      wx_obj.sunset_time,
            },
        }
        series.append(wx_json_body)
        db.write_points(series)

db.close()
