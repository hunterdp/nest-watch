#! /usr/bin/python

# nest-watch.py -- logs Nest Thermostat and observed weather
#                  information to an influxdb
#
# by David Hunter, dph@alumni.neu.edu 
#
# Usage:
#    Reads in a configuration file (nest-watch.ini).  By default it reads the
#    first thermostat found in a user account.  Use the device_index to specify
#    another one. 
#
# Acknowledgements:
#    Thanks to Scott M Baker's nest.py which this is based on 
#    for interacting with the Nest Thermostat

import urllib
import urllib2
import sys
import ConfigParser
from ConfigParser import SafeConfigParser
import pyowm
from pyowm.utils import temputils
import influxdb
import os
import os.path

try:
   import json
except ImportError:
   try:
       import simplejson as json
   except ImportError:
       print "No json library available. I recommend installing either python-json"
       print "or simpejson."
       sys.exit(-1)

class WeatherObj(object):
    def __init__(self, data):
	self.__dict__ = json.loads(data)

class Configuration(object):
    def __init__(self, config_file):
        if os.path.isfile(config_file) and os.access(config_file, os.R_OK):
            print "config file found and is readable"
        else:
            print "Either file is missing or not readable"

    def read(self):
        NestConfig = SafeConfigParser()
        NestConfig.read(self.config_file)
        return NestConfig

class Nest:
    def __init__(self, username, password, serial=None, index=0, units="F"):
        self.username = username
        self.password = password
        self.serial = serial
        self.units = units
        self.index = index

    def loads(self, res):
        if hasattr(json, "loads"):
            res = json.loads(res)
        else:
            res = json.read(res)
        return res

    def login(self):
        data = urllib.urlencode({"username": self.username, "password": self.password})

        req = urllib2.Request("https://home.nest.com/user/login",
                              data,
                              {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4"})

        res = urllib2.urlopen(req).read()

        res = self.loads(res)

        self.transport_url = res["urls"]["transport_url"]
        self.access_token = res["access_token"]
        self.userid = res["userid"]

    def get_status(self):
        req = urllib2.Request(self.transport_url + "/v2/mobile/user." + self.userid,
                              headers={"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                                       "Authorization":"Basic " + self.access_token,
                                       "X-nl-user-id": self.userid,
                                       "X-nl-protocol-version": "1"})
        res = urllib2.urlopen(req).read()
        res = self.loads(res)
        self.structure_id = res["structure"].keys()[0]
        print self.structure_id

        if (self.serial is None):
            self.device_id = res["structure"][self.structure_id]["devices"][self.index]
            self.serial = self.device_id.split(".")[1]
        self.status = res
        print json.dumps(res, indent=4, sort_keys=True)
#        print res

#    def get_info(self):

    def temp_in(self, temp):
        if (self.units == "F"):
            return (temp - 32.0) / 1.8
        else:
            return temp

    def temp_out(self, temp):
        if (self.units == "F"):
            return temp*1.8 + 32.0
        else:
            return temp

    def show_status(self):
        shared = self.status["shared"][self.serial]
        device = self.status["device"][self.serial]
        allvars = shared
        allvars.update(device)
        for k in sorted(allvars.keys()):
             print k + "."*(32-len(k)) + ":", allvars[k]

    def show_curtemp(self):
        temp = self.status["shared"][self.serial]["current_temperature"]
        temp = self.temp_out(temp)
        print "%0.1f" % temp


def main():
    Configuration("./nest_track.ini")
    NestConfig = SafeConfigParser()
    NestConfig.read("./nest_track.ini")

    n_id = NestConfig.get('Thermostat', 'username')
    n_secret = NestConfig.get('Thermostat', 'password')
    n_cache_file = NestConfig.get('Thermostat', 'cache_file')

    db_server = NestConfig.get('Database', 'server')
    db_port = NestConfig.get('Database', 'port')
    db_user = NestConfig.get('Database', 'user')
    db_pwd = NestConfig.get('Database', 'pwd')
    db_name = NestConfig.get('Database', 'name')

    w_api_key = NestConfig.get('Weather', 'api_key')
    w_location = NestConfig.get('Weather', 'location')
    n_lat = NestConfig.get('Weather', 'lat')
    n_long = NestConfig.get('Weather', 'long')


    print "..."

#
#    if opts.celsius:
#        units = "C"
#    else:
#        units = "F"

    n = Nest(n_id, n_secret)
    n.login()
    n.get_status()
    n.show_status()
    n.show_curtemp()
    print n.status["device"][n.serial]["current_humidity"]

if __name__=="__main__":
   main()

