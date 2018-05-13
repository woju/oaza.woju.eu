#!/usr/bin/env python3

import argparse
import asyncio
import datetime
import itertools
import math
import os
import pathlib
import signal
import socket
import sys
import tempfile
import urllib

import aiohttp.web
import aiohttp_jinja2
import ephem
import jinja2

LOADER_PATH = str(pathlib.Path(__file__).parent.parent / 'templates')
_JINJA2_LOADER = jinja2.FileSystemLoader(LOADER_PATH)
MIME_TYPES = {
    'txt': 'text/plain',
    'html': 'text/html',
    'pdf': 'application/pdf',
}

WORKDIR = '/tmp'

class Event(object):
    def __init__(self, getter, *,
            txt, txt_compat, txt_ascii, tex):
        self.getter = getter

        # U+1F31x (those are the correct codepoints, but not widely supported
        #   and characters may be of different width)
        self.txt = txt

        # those have right glyphs, are supported widely, but have wrong names
        self.txt_compat = txt_compat

        # ASCII printable, but not that readable
        self.txt_ascii = txt_ascii

        self.tex = tex

    def __str__(self):
        return self.txt_compat

    @staticmethod
    def visit(events, observer):
        for self in events:
            date = self.getter(observer.date)
            if 0 <= date - observer.date < 1:
                return self, ephem.localtime(date)
        return (None, None)


MOON_PHASES = (
    Event(ephem.next_new_moon,
        txt='\N{NEW MOON SYMBOL}',
        txt_compat='\N{BLACK CIRCLE}',
        txt_ascii='X',
        tex='\\newmoon',
    ),
    Event(ephem.next_first_quarter_moon,
        txt='\N{FIRST QUARTER MOON SYMBOL}',
        txt_compat='\N{FIRST QUARTER MOON}',
        txt_ascii=')',
        tex='\\firstquartermoon',
    ),
    Event(ephem.next_full_moon,
        txt='\N{FULL MOON SYMBOL}',
        txt_compat='\N{WHITE CIRCLE}',
        txt_ascii='O',
        tex='\\fullmoon',
    ),
    Event(ephem.next_last_quarter_moon,
        txt='\N{LAST QUARTER MOON SYMBOL}',
        txt_compat='\N{LAST QUARTER MOON}',
        txt_ascii='(',
        tex='\\lastquartermoon',
    ),
)

SUN_EVENTS = (
    Event(ephem.next_solstice,
        txt='S',
        txt_compat='S',
        txt_ascii='S',
        tex='S',
    ),
    Event(ephem.next_equinox,
        txt='Æ',
        txt_compat='Æ',
        txt_ascii='Æ',
        tex='Æ',
    ),
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

        assert self.day_length.days == 0
        assert self.night_length.days == 0

        self.moon_phase, self.moon_t = Event.visit(MOON_PHASES, self.observer)
        self.sun_event, self.sun_t = Event.visit(SUN_EVENTS, self.observer)

    def _sun_observation(self, getter, horizon=None, *, observer=None):
        observer = observer or self.observer
        if horizon is not None:
            observer = observer.copy()
            observer.horizon = horizon
        sun = ephem.Sun()
        date = getter(observer, sun)
        return ephem.localtime(date), (sun.az * 180 / math.pi) % 360


def parse_timestamp(timestamp):
    return datetime.datetime.strptime(timestamp, '%Y-%m-%d').date()

#
# uwsgi
#

app = aiohttp.web.Application()
aiohttp_jinja2.setup(app, loader=_JINJA2_LOADER)
app['overpass_api'] = 'http://overpass-api.de/api/interpreter'

def _format_coord(coord, *, lon=False, decim=3):
    lon = int(bool(lon))
    return '{:{}.{}f}'.format(coord * 180 / math.pi, decim + 3 + lon, decim
            ).replace('.', 'NSEW'[2 * lon + int(coord < 0)])

async def handle_ephemeris(request):
    element_type = request.match_info['type']
    element_id = int(request.match_info['id'])
    fmt = request.match_info['fmt']
    if fmt == 'pdf':
        template = 'ephemeris.tex'
    else:
        template = 'ephemeris.{}'.format(request.match_info['fmt'])

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

    context = dict(
        name=name,
        lat=_format_coord(me.lat),
        lon=_format_coord(me.lon, lon=True),
        element_type=element_type,
        element_id=element_id,
        days=[Day(me, first_day + datetime.timedelta(days=i))
            for i in range(length)],
    )

    if fmt == 'pdf':
        source = aiohttp_jinja2.render_string(template, request, context)

        loop = asyncio.get_event_loop()

        print('uid {} euid {}'.format(os.getuid(), os.geteuid()))
        print('env\n{}'.format('\n'.join('{}={!r}'.format(*t)
            for t in sorted(os.environ.items()))))

        with tempfile.NamedTemporaryFile(dir=WORKDIR, suffix='.tex', delete=False) as fd_tex:
            await loop.run_in_executor(None,
                fd_tex.write, source.encode('utf-8'))
            await loop.run_in_executor(None, fd_tex.flush)

            path_pdf = pathlib.Path(fd_tex.name).with_suffix('.pdf')
            p = await asyncio.create_subprocess_exec(
#               'strace', '-f', '-o', '/tmp/bad.strace',
                'context',
                '--nonstopmode',
                '--path=/home/woju/liturgia',  # TODO merge that
                os.path.basename(fd_tex.name),
                cwd=WORKDIR)
            await asyncio.wait_for(p.communicate(), timeout=10)
            assert p.returncode == 0

            with path_pdf.open('rb') as fd_pdf:
                response = aiohttp.web.Response()
                response.body = await loop.run_in_executor(None,
                    fd_pdf.read)
    else:
        response = aiohttp_jinja2.render_template(template, request, context)

    response.content_type = MIME_TYPES[fmt]
    return response

def main_uwsgi(app):
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, sys.exit)
    loop.add_signal_handler(signal.SIGHUP, sys.exit)

    app['client'] = aiohttp.ClientSession(loop=loop)
    app.router.add_get(
        r'/ephemeris/{type:way|node|relation}/{id:\d+}.{fmt:txt|html|pdf}',
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
