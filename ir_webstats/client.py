#!/usr/bin/python
""" iRWebStats class. Check examples.py for example usage. """
__author__ = "Jeyson Molina & Jason Dilworth"
__email__ = "jjmc82@gmail.com"
__version__ = "1.1.7"


import urllib

try:
    import urllib.parse

    encode = urllib.parse.urlencode  # python3
except:
    encode = urllib.urlencode  # python2

from io import StringIO
import requests
from ir_webstats import constants as ct
import datetime
import csv
import time
from ir_webstats.util import *


class iRWebStats:

    """Use this class to connect to iRacing website and request some stats
    from drivers, races and series. It needs to be logged in the
    iRacing membersite so valid login crendentials (user, password)
    are required. Most  data is returned in JSON format and
    converted to python dicts."""

    def __init__(self, verbose=True):
        self.last_cookie = ""
        self.logged = False
        self.custid = 0
        self.verbose = verbose
        self.TRACKS, self.CARS, self.DIVISION, self.CARCLASS, self.CLUB = (
            {},
            {},
            {},
            {},
            {},
        )

    def __save_cookie(self):
        """Saves the current cookie to disk from a successful login to avoid
        future login procedures and save time. A cookie usually last
        at least a couple of hours"""

        pprint("Saving cookie for future use", self.verbose)
        o = open("cookie.tmp", "w")
        o.write(self.last_cookie)
        o.write("\n" + str(self.custid))
        o.close()

    def __load_cookie(self):
        """ Loads a previously saved cookie """
        try:
            o = open("cookie.tmp", "r")
            self.last_cookie, self.custid = o.read().split("\n")
            o.close()
            return True
        except:
            return False

    def login(self, username="", password=""):
        """Log in to iRacing members site. If there is a valid cookie saved
        then it tries to use it to avoid a new login request. Returns
        True is the login was succesful and stores the customer id
        (custid) of the current login in self.custid."""

        if self.logged:
            return True
        data = {
            "username": username,
            "password": password,
            "utcoffset": 300,
            "todaysdate": "",
        }
        try:
            pprint("Loggin in...", self.verbose)
            # Check if there's a previous cookie
            if self.__load_cookie() and self.__check_cookie():
                #  If previous cookie is valid
                pprint("Previous cookie valid", self.verbose)
                self.logged = True
                # Load iracing info
                self.__get_irservice_info(
                    self.__req(ct.URL_IRACING_HOME, cookie=self.last_cookie)
                )
                # TODO Should we cache this?
                return self.logged
            self.custid = ""
            r = self.__req(ct.URL_IRACING_LOGIN, grab_cookie=True)
            r = self.__req(
                ct.URL_IRACING_LOGIN2, data, cookie=self.last_cookie, grab_cookie=True
            )

            if "irsso_members" in self.last_cookie:
                ind = r.index("js_custid")
                custid = int(r[ind + 11 : r.index(";", ind)])
                self.custid = custid
                pprint(("CUSTID", self.custid), self.verbose)
                self.logged = True
                self.__get_irservice_info(r)
                self.__save_cookie()
                pprint("Log in succesful", self.verbose)
            else:
                pprint(
                    "Invalid Login (user: %s). Please check your\
                        credentials"
                    % (username),
                    self.verbose,
                )
                self.logged = False

        except Exception as e:
            pprint(("Error on Login Request", e), self.verbose)
            self.logged = False
        return self.logged

    def logout(self):
        self.logged = False  # TODO proper logout

    def __check_cookie(self):
        """ Checks the cookie by testing a request response"""

        r = parse(self.__req(ct.URL_DRIVER_COUNTS, cookie=self.last_cookie))
        if isinstance(r, dict):
            return True
        return False

    def __req(self, url, data=None, cookie=None, grab_cookie=False, useget=False):
        """ Creates and sends the HTTP requests to iRacing site """

        # Sleep/wait to avoid flooding the service with requests
        time.sleep(ct.WAIT_TIME)  # 0.3 seconds
        h = ct.HEADERS.copy()
        if cookie is not None:
            h["Cookie"] = cookie
        else:
            h["Cookie"] = self.last_cookie

        # cookies = {}
        # if cookie is not None:  # Send the cookie
        #     cookie_pairs = cookie.split("; ")
        #     #h['Cookie'] = cookie
        # elif len(self.last_cookie):
        #     cookie_pairs = self.last_cookie.split("; ")
        #     #h['Cookie'] = self.last_cookie

        # #generate cookies dict
        # for pair in cookie_pairs:
        #     parts = pair.split("=", 1)
        #     cookies[parts[0]] = parts[1]

        if (data is None) or useget:
            # resp = requests.get(url, headers=h, params=data, cookies=cookies)
            resp = requests.get(url, headers=h, params=data)
        else:
            h[
                "Content-Type"
            ] = "application/x-www-form-urlencoded;\
                    charset=UTF-8"
            resp = requests.post(url, data=data, headers=h)
        if "Set-Cookie" in resp.headers and grab_cookie:
            self.last_cookie = resp.headers["Set-Cookie"]
            # Must get irsso_members from another header
            if "cookie" in resp.request.headers:
                resp_req_cookie = resp.request.headers["cookie"]
                self.last_cookie += ";" + resp_req_cookie
        html = resp.text
        return html

    def __get_irservice_info(self, resp):
        """Gets general information from iracing service like current tracks,
        cars, series, etc. Check self.TRACKS, self.CARS, self.DIVISION
        , self.CARCLASS, self.CLUB."""

        pprint("Getting iRacing Service info (cars, tracks, etc.)", self.verbose)
        items = {
            "TRACKS": "TrackListing",
            "CARS": "CarListing",
            "CARCLASS": "CarClassListing",
            "CLUBS": "ClubListing",
            "SEASON": "SeasonListing",
            "DIVISION": "DivisionListing",
            "YEARANDQUARTER": "YearAndQuarterListing",
        }
        for i in items:
            str2find = "var " + items[i] + " = extractJSON('"
            try:
                ind1 = resp.index(str2find)
                json_o = resp[ind1 + len(str2find) : resp.index("');", ind1)].replace(
                    "+", " "
                )
                o = json.loads(json_o)
                if i not in ("SEASON", "YEARANDQUARTER"):
                    o = {ele["id"]: ele for ele in o}
                setattr(self, i, o)  # i.e self.TRACKS = o

            except Exception as e:
                pprint(("Error ocurred. Couldn't get", i), self.verbose)

    def _load_irservice_var(self, varname, resp, appear=1):
        str2find = "var " + varname + " = extractJSON('"
        ind1 = -1
        for _ in range(appear):
            ind1 = resp.index(str2find, ind1 + 1)
        json_o = resp[ind1 + len(str2find) : resp.index("');", ind1)].replace("+", " ")
        o = json.loads(json_o)
        if varname not in ("SeasonListing", "YEARANDQUARTER"):
            o = {ele["id"]: ele for ele in o}
        return o

    @logged_in
    def iratingchart(self, custid=None, category=ct.IRATING_ROAD_CHART):
        """Gets the irating data of a driver using its custom id (custid)
        that generates the chart located in the driver's profile."""

        r = self.__req(ct.URL_STATS_CHART % (custid, category), cookie=self.last_cookie)
        return parse(r)

    @logged_in
    def driver_counts(self):
        """ Gets list of connected myracers and notifications. """
        r = self.__req(ct.URL_DRIVER_COUNTS, cookie=self.last_cookie)
        return parse(r)

    @logged_in
    def career_stats(self, custid=None):
        """ Gets career stats (top5, top 10, etc.) of driver (custid)."""
        r = self.__req(ct.URL_CAREER_STATS % (custid), cookie=self.last_cookie)
        # print(r)
        return parse(r)[0]

    @logged_in
    def yearly_stats(self, custid=None):
        """ Gets yearly stats (top5, top 10, etc.) of driver (custid)."""
        r = self.__req(ct.URL_YEARLY_STATS % (custid), cookie=self.last_cookie)
        # tofile(r)
        return parse(r)

    @logged_in
    def cars_driven(self, custid=None):
        """ Gets list of cars driven by driver (custid)."""
        r = self.__req(ct.URL_CARS_DRIVEN % (custid), cookie=self.last_cookie)
        # tofile(r)
        return parse(r)

    @logged_in
    def personal_best(self, custid=None, carid=0):
        """Personal best times of driver (custid) using car
        (carid. check self.CARS) set in official events."""
        r = self.__req(ct.URL_PERSONAL_BEST % (carid, custid), cookie=self.last_cookie)
        return parse(r)

    @logged_in
    def driverdata(self, drivername):
        """Personal data of driver  using its name in the request
        (i.e drivername="Victor Beltran")."""

        r = self.__req(
            ct.URL_DRIVER_STATUS % (encode({"searchTerms": drivername})),
            cookie=self.last_cookie,
        )
        # tofile(r)
        return parse(r)

    @logged_in
    def lastrace_stats(self, custid=None):
        """ Gets stats of last races (10 max?) of driver (custid)."""
        r = self.__req(ct.URL_LASTRACE_STATS % (custid), cookie=self.last_cookie)
        return parse(r)

    @logged_in
    def driver_search(
        self,
        race_type=ct.RACE_TYPE_ROAD,
        location=ct.LOC_ALL,
        license=(ct.LIC_ROOKIE, ct.ALL),
        irating=(0, ct.ALL),
        ttrating=(0, ct.ALL),
        avg_start=(0, ct.ALL),
        avg_finish=(0, ct.ALL),
        avg_points=(0, ct.ALL),
        avg_incs=(0, ct.ALL),
        active=False,
        sort=ct.SORT_IRATING,
        page=1,
        order=ct.ORDER_DESC,
    ):
        """Search drivers using several search fields. A tuple represent a
        range (i.e irating=(1000, 2000) gets drivers with irating
        between 1000 and 2000). Use ct.ALL used in the lower or
        upperbound of a range disables that limit. Returns a tuple
        (results, total_results) so if you want all results you should
        request different pages (using page) until you gather all
        total_results. Each page has 25 (ct.NUM_ENTRIES) results max."""

        lowerbound = ct.NUM_ENTRIES * (page - 1) + 1
        upperbound = lowerbound + ct.NUM_ENTRIES - 1
        search = "null"
        friend = ct.ALL  # TODO
        studied = ct.ALL  # TODO
        recent = ct.ALL  # TODO

        active = int(active)
        # Data to POST
        data = {
            "custid": self.custid,
            "search": search,
            "friend": friend,
            "watched": studied,
            "country": location,
            "recent": recent,
            "category": race_type,
            "classlow": license[0],
            "classhigh": license[1],
            "iratinglow": irating[0],
            "iratinghigh": irating[1],
            "ttratinglow": ttrating[0],
            "ttratinghigh": ttrating[1],
            "avgstartlow": avg_start[0],
            "avgstarthigh": avg_start[1],
            "avgfinishlow": avg_finish[0],
            "avgfinishhigh": avg_finish[1],
            "avgpointslow": avg_points[0],
            "avgpointshigh": avg_points[1],
            "avgincidentslow": avg_incs[0],
            "avgincidentshigh": avg_incs[1],
            "lowerbound": lowerbound,
            "upperbound": upperbound,
            "sort": sort,
            "order": order,
            "active": active,
        }

        total_results, drivers = 0, {}

        try:
            r = self.__req(ct.URL_DRIVER_STATS, data=data, cookie=self.last_cookie)
            res = parse(r)
            total_results = res["d"]["32"]

            header = res["m"]
            f = res["d"]["r"][0]
            if int(f["29"]) == int(self.custid):  # 29 is custid
                drivers = res["d"]["r"][1:]
            else:
                drivers = res["d"]["r"]
            drivers = format_results(drivers, header)

        except Exception as e:
            pprint(("Error fetching driver search data. Error:", e), self.verbose)

        return drivers, total_results

    def test(self, a, b=2, c=3):
        return a, b, c

    @logged_in
    def results_archive(
        self,
        custid=None,
        race_type=ct.RACE_TYPE_ROAD,
        event_types=ct.ALL,
        official=ct.ALL,
        license_level=ct.ALL,
        car=ct.ALL,
        track=ct.ALL,
        series=ct.ALL,
        season=(2014, 1, ct.ALL),
        date_range=ct.ALL,
        page=1,
        sort=ct.SORT_TIME,
        order=ct.ORDER_DESC,
    ):
        """Search race results using various fields. Returns a tuple
        (results, total_results) so if you want all results you should
        request different pages (using page). Each page has 25
        (ct.NUM_ENTRIES) results max."""

        format_ = "json"
        lowerbound = ct.NUM_ENTRIES * (page - 1) + 1
        upperbound = lowerbound + ct.NUM_ENTRIES - 1
        #  TODO carclassid, seriesid in constants
        data = {
            "format": format_,
            "custid": custid,
            "seriesid": series,
            "carid": car,
            "trackid": track,
            "lowerbound": lowerbound,
            "upperbound": upperbound,
            "sort": sort,
            "order": order,
            "category": race_type,
            "showtts": 0,
            "showraces": 0,
            "showquals": 0,
            "showops": 0,
            "showofficial": 0,
            "showunofficial": 0,
            "showrookie": 0,
            "showclassa": 0,
            "showclassb": 0,
            "showclassc": 0,
            "showclassd": 0,
            "showpro": 0,
            "showprowc": 0,
        }
        # Events
        ev_vars = {
            ct.EVENT_RACE: "showraces",
            ct.EVENT_QUALY: "showquals",
            ct.EVENT_PRACTICE: "showops",
            ct.EVENT_TTRIAL: "showtts",
        }
        if event_types == ct.ALL:
            event_types = (
                ct.EVENT_RACE,
                ct.EVENT_QUALY,
                ct.EVENT_PRACTICE,
                ct.EVENT_TTRIAL,
            )

        for v in event_types:
            data[ev_vars[v]] = 1
        # Official, unofficial
        if official == ct.ALL:
            data["showofficial"] = 1
            data["showunoofficial"] = 1
        else:
            if ct.EVENT_UNOFFICIAL in official:
                data["showunofficial"] = 1
            if ct.EVENT_OFFICIAL in official:
                data["showofficial"] = 1

        # Season
        if date_range == ct.ALL:
            data["seasonyear"] = season[0]
            data["seasonquarter"] = season[1]
            if season[2] != ct.ALL:
                data["raceweek"] = season[2]
        else:
            # Date range
            tc = (
                lambda s: time.mktime(
                    datetime.datetime.strptime(s, "%Y-%m-%d").timetuple()
                )
                * 1000
            )
            data["starttime_low"] = int(tc(date_range[0]))  # multiplied by 1000
            data["starttime_high"] = int(tc(date_range[1]))

        # License levels
        lic_vars = {
            ct.LIC_ROOKIE: "showrookie",
            ct.LIC_A: "showclassa",
            ct.LIC_B: "showclassb",
            ct.LIC_C: "showclassc",
            ct.LIC_D: "showclassd",
            ct.LIC_PRO: "showpro",
            ct.LIC_PRO_WC: "showprowc",
        }

        if license_level == ct.ALL:
            license_level = (
                ct.LIC_ROOKIE,
                ct.LIC_A,
                ct.LIC_B,
                ct.LIC_C,
                ct.LIC_D,
                ct.LIC_PRO,
                ct.LIC_PRO_WC,
            )
        for v in license_level:
            data[lic_vars[v]] = 1
        r = self.__req(ct.URL_RESULTS_ARCHIVE, data=data, cookie=self.last_cookie)
        res = parse(r)
        total_results, results = 0, []
        if "d" in res and len(res["d"]):
            total_results = res["d"]["15"]
            results = res["d"]["r"]
            header = res["m"]
            results = format_results(results, header)

        return results, total_results

    @logged_in
    def all_seasons(self):
        """Get All season data available at Series Stats page"""
        pprint("Getting iRacing Seasons with Stats")
        resp = self.__req(ct.URL_SEASON_STANDINGS2)
        return self._load_irservice_var("SeasonListing", resp)

    @logged_in
    def season_standings(
        self,
        season,
        carclass,
        club=ct.ALL,
        raceweek=ct.ALL,
        division=ct.ALL,
        sort=ct.SORT_POINTS,
        order=ct.ORDER_DESC,
        page=1,
    ):
        """Search season standings using various fields. season, carclass
        and club are ids.  Returns a tuple (results, total_results) so
        if you want all results you should request different pages
        (using page)  until you gather all total_results. Each page has
        25 results max."""

        lowerbound = ct.NUM_ENTRIES * (page - 1) + 1
        upperbound = lowerbound + ct.NUM_ENTRIES - 1

        data = {
            "sort": sort,
            "order": order,
            "seasonid": season,
            "carclassid": carclass,
            "clubid": club,
            "raceweek": raceweek,
            "division": division,
            "start": lowerbound,
            "end": upperbound,
        }
        r = self.__req(ct.URL_SEASON_STANDINGS, data=data)
        res = parse(r)
        total_results = res["d"]["27"]
        results = res["d"]["r"]
        header = res["m"]
        results = format_results(results, header)

        return results, total_results

    @logged_in
    def hosted_results(
        self,
        cust_id=None,
        session_host=None,
        session_name=None,
        date_range=None,
        sort=ct.SORT_TIME,
        order=ct.ORDER_DESC,
        page=1,
    ):
        """Search hosted races results using various fields. Returns a tuple
        (results, total_results) so if you want all results you should
        request different pages (using page) until you gather all
        total_results. Each page has 25 (ct.NUM_ENTRIES) results max."""

        lowerbound = ct.NUM_ENTRIES * (page - 1) + 1
        upperbound = lowerbound + ct.NUM_ENTRIES - 1

        data = {
            "sort": sort,
            "order": order,
            "lowerbound": lowerbound,
            "upperbound": upperbound,
        }
        if cust_id is not None:
            data["participant_custid"] = cust_id
        if session_host is not None:
            data["sessionhost"] = session_host
        if session_name is not None:
            data["sessionname"] = session_name

        if date_range is not None:
            # Date range
            tc = (
                lambda s: time.mktime(
                    datetime.datetime.strptime(s, "%Y-%m-%d").timetuple()
                )
                * 1000
            )
            data["start_time_lowerbound"] = int(tc(date_range[0]))
            data["start_time_upperbound"] = int(tc(date_range[1]))

        r = self.__req(ct.URL_HOSTED_RESULTS, data=data)
        # tofile(r)
        res = parse(r)
        if not res:
            return None, None
        total_results = res["rowcount"]
        results = res["rows"]  # doesn't need format_results
        return results, total_results

    @logged_in
    def session_times(self, series_season, start, end):
        """Gets Current and future sessions (qualy, practice, race)
        of series_season"""
        r = self.__req(
            ct.URL_SESSION_TIMES,
            data={"start": start, "end": end, "season": series_season},
            useget=True,
        )
        return parse(r)

    @logged_in
    def series_raceresults(self, season, raceweek):
        """ Gets races results of all races of season in specified raceweek """

        r = self.__req(
            ct.URL_SERIES_RACERESULTS, data={"seasonid": season, "raceweek": raceweek}
        )  # TODO no bounds?
        res = parse(r)
        header = res["m"]
        results = res["d"]
        results = format_results(results, header)
        return results

    # @logged_in
    # def event_results(self, subsession, sessnum=0):
    #     """Gets the event results (table of positions, times, etc.). The
    #     event is identified by a subsession id."""

    #     r = self.__req(ct.URL_GET_EVENTRESULTS % (subsession, sessnum)).encode("utf8")
    #     data = [
    #         x
    #         for x in csv.reader(
    #             StringIO(r.decode("utf8")), delimiter=",", quotechar='"'
    #         )
    #     ]
    #     header_ev, header_res = data[0], data[3]
    #     event_info = dict(list(zip(header_ev, data[1])))
    #     results = [dict(list(zip(header_res, x))) for x in data[4:]]

    #     return event_info, results

    @logged_in
    def event_results(self, subsession, cust_id=None):
        """ Gets specific session details """
        driver_result = None

        r = self.__req(
            ct.URL_EVENT_RESULTS, data={"subsessionID": subsession, "custid": cust_id}
        )
        res = parse(r)
        if not res:
            return None, None

        driver_results = [
            x
            for x in res["rows"]
            if x["custid"] == cust_id and x["simsestypename"] == "Race"
        ]
        if driver_results:
            driver_result = driver_results[0]

        return res, driver_result


if __name__ == "__main__":
    irw = iRWebStats()
    user, passw = ("username", "password")
    irw.login(user, passw)
    print("Cars Driven", irw.cars_driven())  # example usage
