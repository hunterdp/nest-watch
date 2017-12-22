#! /usr/bin/python

import logging, logging.handlers
import urllib, urllib.parse, urllib.request
import configparser
import influxdb, pyowm
import os, os.path, json, sys

from configparser import SafeConfigParser
from pyowm.utils import temputils

__title__   = "NestLogger"
__version__ = "0.1"
__author__  = "David Hunter"
__log_name__ = "NestWatcher"

class WeatherObj(object):
    def __init__(self, data):

class Nest:
    def __init__(self, username, password, serial=None, index=0, units="F"):
        self.username = username
        self.password = password
        self.serial = serial
        self.units = units
        self.index = index
        LOG = logging.getLogger(__log_name__)
        LOG.debug("Passed in username: %s, serial: %s, index: %s, units: %s.", 
                   username, serial, index, units)

    def loads(self, res):
        if hasattr(json, "loads"):
            res = json.loads(res)
        else:
            res = json.read(res)
        return res

    def login(self):

        LOG = logging.getLogger(__log_name__)

        url = "https://home.nest.com/user/login"
        browser_s = {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4"} 
        login_s = {"username": self.username, "password": self.password}
        data = urllib.parse.urlencode(login_s).encode("utf-8")
        LOG.info("Attempting to log in %s with username: %s", url, self.username)    
 
        req = urllib.request.Request(url, data, browser_s)
        res = urllib.request.urlopen(req).read()
        LOG.info("Opened url and retrieved page.")    

        res = json.loads(res)

        msg = (json.dumps(res, indent=4, sort_keys=True))
        LOG.debug("Dump of returned url data:")
        LOG.debug(msg)

        self.transport_url = res["urls"]["transport_url"]
        self.access_token = res["access_token"]
        self.userid = res["userid"]

        LOG.debug("Transport URL is %s with an access toke of %s and user id of %s.",
                   self.transport_url, self.access_token, self.userid)


    def get_status(self):

        req = urllib.request.Request(self.transport_url + "/v2/mobile/user." + self.userid,
                              headers={"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                                       "Authorization":"Basic " + self.access_token,
                                       "X-nl-user-id": self.userid,
                                       "X-nl-protocol-version": "1"})
        res = urllib.request.urlopen(req).read()
        res = json.loads(res)
#        print (json.dumps(res["structure"], indent=4, sort_keys=True))
#        for key in res:
#            print("%key: %s      value: %s", key, res[key])

        self.structure_id = res["structure"].keys()

#        for key in res["structure"].keys():
#            print("%key: %s       value: %s", key, res["structure"].values()

#        print("self.structure_id: %s", self.structure_id)
#        print("self.structure_value: %s", res["structure"].values())


        if (self.serial is None):
            self.device_id = res["structure"][self.structure_id]["devices"][self.index]
            self.serial = self.device_id.split(".")[1]
        self.status = res
        print (json.dumps(res, indent=4, sort_keys=True))

    def temp_ftc(self, temp):
        if (self.units == "F"):
            return (temp - 32.0) / 1.8
        else:
            return temp

    def temp_ctf(self, temp):
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
             print (k + "."*(32-len(k)) + ":", allvars[k])

    def show_curtemp(self):
        temp = self.status["shared"][self.serial]["current_temperature"]
        temp = self.temp_ctf(temp)
        print ("%0.1f" % temp)

def main():
    LOG = _configure_logger(__log_name__)
    LOG.info("Starting %s Version %s.", __title__, __version__)

    if (sys.version_info.major != 3):
        LOG.critical("Need version 3 or greater of python.  Exiting program.")
        exit(-1)

    Config = Configuration("./nest_track.ini")
    Nest_s = Config.read()

    '''
    LOG.info("Logging into %s on port %s with username %s.", 
              Nest_s["db_server"], Nest_s["db_port"], Nest_s["db_user"])

    LOG.info("Storing information in the %s database.", Nest_s["db_name"])
    LOG.info("Getting observed weather at location %s (lat: %s long: %s).", Nest_s["location"], Nest_s["lat"], Nest_s["long"])
    '''

    n = Nest(Nest_s["id"], Nest_s["secret"])
    n.login()

#    n.get_status()
#    n.show_status()
#    n.show_curtemp()
#    print (n.status["device"][n.serial]["current_humidity"])

if __name__=="__main__":
   main()

