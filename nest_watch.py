#! /usr/bin/python
# nest_watch.py -- logs Nest Thermostat and observed weather
#                  information to an influxdb.  Note: Must be
#                  run with python 3.x+
#
# by David Hunter, dph@alumni.neu.edu
#
''' nest_watch.py program '''

import os
import os.path
import sys
import logging
import logging.handlers
import json
import urllib
import urllib.parse
import urllib.request
from configparser import SafeConfigParser
import requests
import influxdb
from influxdb import client as influxdb
import pyowm
from pyowm.utils import temputils

# Setup global consants
__title__ = "nest_logger"
__version__ = "0.1"
__author__ = "David Hunter"
__log_name__ = "nest_watch"
__nest_config__ = "./nest_track.ini"

# Define the various web pages that are constant across all procedures
AUTHORIZATION_URL = 'https://home.nest.com/login/oauth2?client_id={0}&state={1}'
ACCESS_TOKEN_URL = "https://api.home.nest.com/oauth2/access_token"
NEST_API_URL = 'https://developer-api.nest.com/devices.json?auth={0}'
NEST_API_URL = 'https://developer-api.nest.com/?auth={0}'
WORKS_WITH_NEST_URL = "https://developer-api.nest.com"
PORTAL_URL = "https://home.nest.com"
DEVELOPER_URL = "https://console.developers.nest.com"

def get_weather(api_key, location):
    ''' Connects to OpenWeatherMap API site and gets weather

    : param str api_key: OpenWeather API KeyError
    : param str location {"lat": 'xxx', "lon": 'xxxxx', "city": "city,st, cn"}

    : returns dict weather A json structure of observed weather
    '''

    LOG.info("Getting weather informatin at %f %f.", location["lat"], location["lon"])

    owm = pyowm.OWM(api_key)
    obs = owm.weather_at_coords(location["lat"], location["lon"])
    weather_x = obs.get_weather()
    weather_data = weather_x.to_JSON()
    weather = json.loads(weather_data)
    LOG.debug(json.dumps(weather, indent=4, sort_keys=True))
    return weather

def record_measurements(db_conn, data):
    """Record current weather data into the database.

    :param str database: The name of the database.
    :param int port: The port number the database is listening on.
    :param dict data: Measurement data to write

    :return: When the data has been written to the database.
    """
    LOG.debug("Writing points to database.")
    db_conn.write_points(data)

def get_configuration(config_file):
    ''' Reads the configuration file and returns its contents. '''

    if os.path.isfile(config_file) and os.access(config_file, os.R_OK):
        LOG.debug("Config file %s found and is readable.", config_file)
    else:
        LOG.critical("Either % file is missing or not readable.", config_file)
        exit(-1)

    LOG.info("Parsing configuration file %s.", config_file)
    configuration_data = SafeConfigParser()
    configuration_data.read(config_file)
    config_info = {"id":         configuration_data.get('Thermostat', 'client_id'),
                   "secret":     configuration_data.get('Thermostat', 'client_secret'),
                   "username":   configuration_data.get('Thermostat', 'username'),
                   "password":   configuration_data.get('Thermostat', 'password'),
                   "pin":        configuration_data.get('Thermostat', 'pin'),
                   "cache_file": configuration_data.get('Thermostat', 'cache_file'),
                   "db_server":  configuration_data.get('Database', 'server'),
                   "db_port":    configuration_data.get('Database', 'port'),
                   "db_user":    configuration_data.get('Database', 'user'),
                   "db_pwd":     configuration_data.get('Database', 'pwd'),
                   "db_name":    configuration_data.get('Database', 'name'),
                   "api_key":    configuration_data.get('Weather', 'api_key'),
                   "location":   configuration_data.get('Weather', 'location'),
                   "lat":        float(configuration_data.get('Weather', 'lat')),
                   "lon":        float(configuration_data.get('Weather', 'lon'))
                  }

    LOG.debug("Configuration values: %s", json.dumps(config_info))
    return config_info

def connect_to_database(server, port, user, pwd, database):
    ''' Connects to an Influx database server and verifys the database is available '''

    database_connection = influxdb.InfluxDBClient(server, port, user, pwd)
    database_list = database_connection.get_list_database()
    if database not in [str(x['name']) for x in database_list]:
        LOG.info("Database not found in influx server %s.", server)
        LOG.info("Creating new database %s on influx server %s.",
                 database, server)
        database_connection.create_database(database)
    else:
        LOG.info("Database %s exists on influx server %s",
                 database, server)

    database_connection.switch_database(database)
    LOG.info("Switching to database %s.", database)
    return 0

class Nest:
    ''' Structure used to comminucate with Nest devices '''

    def __init__(self, username, password, serial=None, index=0, units="F"):
        ''' A Nest Thermostat Class '''
        # Should not the Nest dict structures be defined here?
        # Once instantiated the read/open/write/store operations can be used?

        self.username = username
        self.password = password
        self.serial = serial
        self.units = units
        self.index = index

        LOG.info("Created a Nest Instance with username: %s, serial: %s, index: %s, units: %s.",
                 username, serial, index, units)

    def login_user_account(self):
        ''' Logs into a Nest Account and returns the Nest Structure '''

        url = "https://home.nest.com/user/login"
        browser_s = {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4"}
        login_s = {"username": self.username, "password": self.password}
        data = urllib.parse.urlencode(login_s).encode("utf-8")
        LOG.info("Attempting to log in %s with username: %s", url, self.username)
        req = urllib.request.Request(url, data, browser_s)

        if urllib.request.urlopen(req).getcode() != 200:
            LOG.critical("Unable to login into page %s.", url)
            LOG.critical("Returned status code: %s", urllib.request.urlopen(req).getcode())
            LOG.critical("Exiting program.")
            exit(-1)
        LOG.info("Succesfully logged in to the Nest account.")
        res = urllib.request.urlopen(req).read()
        LOG.info("Opened url and retrieved initial Nest information page.")

        res = json.loads(res)
        msg = (json.dumps(res, indent=4, sort_keys=True))
        LOG.debug("Dump of returned url data:")
        LOG.debug(msg)
        LOG.debug("Trasport URL is %s and user id of %s.",
                  res["urls"]["transport_url"], res["userid"])
        return res

    def login_developer_account(self, client_id, client_secret, client_pin):
        ''' Use the developer account model '''

        token_post_data = {
            'code': client_pin,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code'
            }
        token_response = requests.post(ACCESS_TOKEN_URL, data=token_post_data)
            # token_response.raise_for_status()
        access_token = token_response.json()['access_token']

        nest_response = requests.get(NEST_API_URL.format(access_token))
        # print(json.dumps(nest_response.json(), sort_keys=True, indent=4))
        return nest_response

    def get_status(self, nest_config):
        ''' Gets the current status of the thermostat '''

        req = urllib.request.Request(nest_config["urls"]["transport_url"]+
                                     "/v2/mobile/user." + nest_config["userid"],
                                     headers={"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                                              "Authorization":"Basic "+nest_config["access_token"],
                                              "X-nl-user-id": nest_config["userid"],
                                              "X-nl-protocol-version": "1"})
        res = urllib.request.urlopen(req).read()
        res = json.loads(res)
        # print(json.dumps(res["structure"], indent=4, sort_keys=True))
        return res

    def temp_farenheit_to_celcius(self, temp):
        ''' Converts F to C temperatures '''
        if self.units == "F":
            return (temp - 32.0) / 1.8
        else:
            return temp

    def temp_celcius_to_farenheit(self, temp):
        ''' Converts C to F temperatures '''
        if self.units == "F":
            return temp*1.8 + 32.0
        else:
            return temp

    def show_current_temp(self, body):
        ''' Gets the current thermostat temperature '''
        temp = body["current_temperature"]
        temp = temp_celcius_to_farenheit(temp)
        # print("%0.1f" % temp)

def _configure_logger(name):
    ''' A simple logging function that sets up logging to a file '''
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join("./", os.extsep.join([name, "log"])),
        maxBytes=2**20,
        backupCount=5)
    fmt_str_1 = "%(asctime)s %(levelname)-8s %(module)-12s "
    fmt_str = fmt_str_1 + "%(funcName)-20s %(processName)s:%(process)d %(message)-s"
    fmt = logging.Formatter(fmt=fmt_str)
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    return logger

def main():
    ''' Initializes all data strucutres and validates configuration '''

    # Define the dictionariy structures
    nest_config = []
    observed_weather = []
    data_points = []

    # Get the configuration information.
    if os.getenv('NEST_WATCHER_INI') is None:
        config_information = get_configuration(__nest_config__)
    else:
        config_information = get_configuration(os.getenv("NEST_WATCHER_INI"))

    # Connect to the Nest thermostat specified and get the current readings
    nest_information = Nest(config_information["username"], config_information["password"])
    nest_config = nest_information.login_user_account()
    nest_information.get_status(nest_config)

    # Get the current observed weather given.
    # The location structure can either be a lat/lon pair or a city, st, cn string.
    # If both are supplied, lat/long pair us used by default.
    location = {
        "lat": config_information["lat"],
        "lon": config_information["lon"],
        "city": config_information["location"]}

    observed_weather = get_weather(config_information["api_key"], location)

    # Store the observed weather and thermostat readings in the database.
    # json_body = {
                 # "measurement": "temperature",
                 # "tags": {
                    # "location": structure.name,
                    # "device": device.name,
                # },
                 # "fields": {
                    # "home_away": structure.away,
                    # "online": device.online,
                    # "emergency_heat": device.is_using_emergency_heat,
                    # "mode": device.mode,
                    # "state": device.hvac_state,
                    # "current": float(device.temperature),
                    # "target": float(device.target),
                    # "high": float(device.eco_temperature.high),
                    # "low": float(device.eco_temperature.low),
                    # "humidity": float(device.humidity),
                # },
            # }
    # data_points.append(json_body)

    weather_json_body = {
        "measurement": "weather",
        "tags": {
            "location": "312 Woodland",
            "device": "Hallway",
            },
        "fields": {
            "humidity":    float(observed_weather["humidity"]),
            "status":      observed_weather["detailed_status"],
            "cur_temp":    float(temputils.kelvin_to_fahrenheit(observed_weather["temperature"]["temp"])),
            "max_temp":    float(temputils.kelvin_to_fahrenheit(observed_weather["temperature"]["temp_max"])),
            "min_temp":    float(temputils.kelvin_to_fahrenheit(observed_weather["temperature"]["temp_min"])),
            "cloud_cover": observed_weather["clouds"],
            "wind_speed":  float(observed_weather["wind"]["speed"]),
            "wind_degree": float(observed_weather["wind"]["deg"]),
            "sunrise":     observed_weather["sunrise_time"],
            "sunset":      observed_weather["sunset_time"]
        },
    }
    data_points.append(weather_json_body)

    # Connect to the database and write the measurements
    # NB:
    #    Three is no error checking wrt to connecting to the database server.
    nest_db = connect_to_database(config_information["db_server"],
                                  config_information["db_port"],
                                  config_information["db_user"],
                                  config_information["db_pwd"],
                                  config_information["db_name"])
    LOG.debug("Writing points to database.")
    #nest_db.write_points(data_points)
    record_measurements(nest_db, data_points)

if __name__ == "__main__":

    LOG = _configure_logger(__log_name__)
    LOG.info("Starting %s Version %s.", __title__, __version__)

    if sys.version_info.major != 3:
        LOG.critical("Need Python version 3 or greater.  Exiting...")
        exit(-1)
    main()
