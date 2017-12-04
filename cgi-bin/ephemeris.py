#!/usr/bin/env python3

import argparse
import asyncio
import datetime
import itertools
import math
import signal
import socket
import sys
import urllib

import aiohttp.web
import ephem

class MoonPhase(object):
    def __init__(self, getter, symbol):
        self.getter = getter
        self.symbol = symbol
    def __str__(self):
        return self.symbol

MOON_PHASES = (
    # those have right glyphs, are supported widely, but have wrong names
    MoonPhase(ephem.next_new_moon, '\N{BLACK CIRCLE}'),
    MoonPhase(ephem.next_first_quarter_moon, '\N{FIRST QUARTER MOON}'),
    MoonPhase(ephem.next_full_moon, '\N{WHITE CIRCLE}'),
    MoonPhase(ephem.next_last_quarter_moon, '\N{LAST QUARTER MOON}'),

    # U+1F31x (those are the correct codepoints, but not widely supported
    #   and characters may be of different width)
#   MoonPhase(ephem.next_new_moon, '\N{NEW MOON SYMBOL}'),
#   MoonPhase(ephem.next_first_quarter_moon, '\N{FIRST QUARTER MOON SYMBOL}'),
#   MoonPhase(ephem.next_full_moon, '\N{FULL MOON SYMBOL}'),
#   MoonPhase(ephem.next_last_quarter_moon, '\N{LAST QUARTER MOON SYMBOL}'),

    # ASCII printable, but not that readable
#   MoonPhase(ephem.next_new_moon, 'X'),
#   MoonPhase(ephem.next_first_quarter_moon, ')'),
#   MoonPhase(ephem.next_full_moon, 'O'),
#   MoonPhase(ephem.next_last_quarter_moon, '('),
)

class Day(object):
    def __init__(self, observer, day):
        self.day = day
        self.observer = observer.copy()
        self.observer.date = day

        self.midday, _ = self._sun_observation(
            ephem.Observer.next_transit)
        self.midnight, _ = self._sun_observation(
            ephem.Observer.next_antitransit)

        self.dawn, _ = self._sun_observation(
            ephem.Observer.next_rising, '-6')
        self.sunrise, self.sunrise_az = self._sun_observation(
            ephem.Observer.next_rising, '0')
        self.sunset, self.sunset_az = self._sun_observation(
            ephem.Observer.next_setting, '0')
        self.dusk, _ = self._sun_observation(
            ephem.Observer.next_setting, '-6')

        tomorrow_observer = observer.copy()
        tomorrow_observer.date = day + datetime.timedelta(days=1)
        tomorrow_dawn, _ = self._sun_observation(
            ephem.Observer.next_rising, '-6', observer=tomorrow_observer)

        self.day_length = self.dusk - self.dawn
        self.night_length = tomorrow_dawn - self.dusk

        self.moon_phase, self.moon = None, None
        for phase in MOON_PHASES:
            date = phase.getter(self.observer.date)
            if 0 <= date - self.observer.date < 1:
                self.moon_phase, self.moon = phase, ephem.localtime(date)

    def _sun_observation(self, getter, horizon=None, *, observer=None):
        observer = observer or self.observer
        if horizon is not None:
            observer = observer.copy()
            observer.horizon = horizon
        sun = ephem.Sun()
        date = getter(observer, sun)
        return ephem.localtime(date), (sun.az * 180 / math.pi) % 360

    @staticmethod
    def _format_timedelta(timedelta):
        assert timedelta.days == 0
        minutes = round(timedelta.seconds / 60)
        return '{:02d}{:02d}'.format(minutes // 60, minutes % 60)

    def __str__(self):
        return (
            '{self.day:%Y%m%d}  '
            '{self.dawn:%H%M}  '
            '{self.sunrise:%H%M} {self.sunrise_az:03.0f}  '
            '{self.midday:%H%M}  '
            '{day_length}\n'

            '  {moon_phase} {moon}  '
            '{self.dusk:%H%M}  '
            '{self.sunset:%H%M} {self.sunset_az:03.0f}  '
            '{self.midnight:%H%M}  '
            '{night_length}  '
        ).format(self=self,
            day_length=self._format_timedelta(self.day_length),
            night_length=self._format_timedelta(self.night_length),
            moon=(self.moon.strftime('%H%M')
                if self.moon is not None else '    '),
            moon_phase=(self.moon_phase or ' '),
        )

    @staticmethod
    def get_header():
        return (
            '====================================\n'

            'YYYYMMDD  '
            'DAWN  '
            'SUNRISE-  '
            'NOON  '
            'DAY-\n'

            '  -MOON-  '
            'DUSK  '
            'SUNSET--  '
            'MIDN  '
            'NGHT\n'

            '===================================='
        ).format()


def parse_timestamp(timestamp):
    return datetime.datetime.strptime(timestamp, '%Y-%m-%d').date()

#
# uwsgi
#

app = aiohttp.web.Application()
app['overpass_api'] = 'http://overpass-api.de/api/interpreter'

def _format_coord(coord, *, lon=False, decim=3):
    lon = int(bool(lon))
    return '{:{}.{}f}'.format(coord * 180 / math.pi, decim + 3 + lon, decim
            ).replace('.', 'NSEW'[2 * lon + int(coord < 0)])

async def handle_ephemeris(request):
    element_type = request.match_info['type']
    try:
        element_id = int(request.match_info['id'])
    except ValueError as e:
        raise aiohttp.web.HTTPNotFound(
            text='no such {}'.format(element_type)) from None

    try:
        first_day = parse_timestamp(request.url.query['first_day'])
        length = int(request.url.query['length'])
        assert 0 < length <= 30
    except (KeyError, ValueError, AssertionError) as e:
        print(e)
        raise aiohttp.web.HTTPForbidden(text='invalid params') from None

    async with request.app['client'].post(request.app['overpass_api'],
            data='[out:json]; {}({}); out center;'.format(
                element_type, element_id)) as resp:
        try:
            element = (await resp.json())['elements'][0]
        except IndexError:
            raise aiohttp.web.HTTPNotFound(
                text='no such {}'.format(element_type)) from None
    name = element['tags'].get('name', '')
    try:
        element = element['center']
    except KeyError:
        # node has no center, but has "lat" and "lon" directly
        pass

    me = ephem.Observer()
    me.lat, me.lon = (element[key] * math.pi / 180 for key in ('lat', 'lon'))

    return aiohttp.web.Response(text='\n'.join(map(str, itertools.chain(
        (
            '====================================\n'
            '{name}\n'
            '{lat} {lon}  {iden}'.format(
                name=name,
                lat=_format_coord(me.lat),
                lon=_format_coord(me.lon, lon=True),
                iden='{}({})'.format(element_type, element_id).rjust(20),
            ),
            Day.get_header(),
        ),
        (Day(me, first_day + datetime.timedelta(days=i))
            for i in range(length))))))

def main_uwsgi(app):
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, sys.exit)
    loop.add_signal_handler(signal.SIGHUP, sys.exit)

    app['client'] = aiohttp.ClientSession(loop=loop)
    app.router.add_get('/ephemeris/{type:way|node|relation}/{id}',
        handle_ephemeris)

    handler = app.make_handler()
    servers = []

    for fileno in uwsgi.sockets:
        print('listening on fd={}'.format(fileno))
        servers.append(loop.run_until_complete(loop.create_unix_server(handler,
            sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM,
                fileno=fileno))))

    loop.call_soon(uwsgi.accepting)
    loop.run_forever()

parser = argparse.ArgumentParser()
parser.add_argument('--latitude', '--lat',
    required=True)
parser.add_argument('--longitude', '--lon',
    required=True)
parser.add_argument('start', metavar='YYYY-MM-DD',
    type=parse_timestamp)
parser.add_argument('count',
    type=int)

def main_cli(args=None):
    args = parser.parse_args(args)
    me = ephem.Observer()
    me.lat, me.lon = args.latitude, args.longitude

    print(Day.get_header())
    for i in range(args.count):
        print(Day(me, args.start + datetime.timedelta(days=i)))

if __name__ == '__main__':
    try:
        import uwsgi
    except ImportError:
        main_cli()
    else:
        main_uwsgi(app)
