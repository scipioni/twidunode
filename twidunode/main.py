
import argparse
import sys
import time
import logging
import re
from sanic import Sanic
from sanic.response import json

import asyncio
import serial_asyncio
import uvloop
from signal import signal, SIGINT


parser = argparse.ArgumentParser()
parser.add_argument('--serial', help="serial port name",
                    default='/dev/ttyACM0')
parser.add_argument('--baud', type=int,
                    help='set baud rate, default: %(default)s', default=9600)
parser.add_argument('--poll', type=int,
                    help='poll time seconds, default: %(default)s', default=1)
parser.add_argument('--port', type=int,
                    help='http server port %(default)s', default=8000)
parser.add_argument('--debug', action='store_true',
                    help='debug', default=False)

args = parser.parse_args()


app = Sanic(__name__)


class Serial(asyncio.Protocol):
    """
    https://twidunode.com/wiki/index.php?title=Manual:Configuration_settings#comandi_informativi
    """
    def __init__(self, *args, **kwargs):
        super()
        self.dc, self.vac, self.vpoe = 0, 0, 0
        app.add_route(self.api, '/')
        app.add_route(self.reboot, '/reboot')
        app.add_route(self.off, '/off')
        app.add_route(self.on, '/on')

    async def reboot(self, request):
        self.transport.write(b'reboot\r')
        return json({'success': True})    

    async def off(self, request):
        self.transport.write(b'set poeout off\r')
        return json({'poe':'off'})

    async def on(self, request):
        self.transport.write(b'set poeout on\r')
        return json({'poe':'on'})

    async def api(self, request):
        return json({'dc': self.dc, 'vac': self.vac, 'vpoe': self.vpoe, 'poe': 'on' if self.vpoe > 0 else 'off', 'state': 'on battery' if self.vac <= 0 else '220V'})

    def connection_made(self, transport):

        self.transport = transport
        logging.info('port opened: %s' % args.serial)
        transport.serial.rts = False  # You can manipulate Serial object via transport
        asyncio.ensure_future(self.poll())
 
    async def poll(self):
        while True:
            self.transport.write(b'infopower\r')
            await asyncio.sleep(args.poll)

    def data_received(self, data):
        logging.debug("received: %s" % data)
        if data and data[:4] == b'VDC=':
            try:
                self.dc, self.vac, self.vpoe = map(float, re.findall(
                    'VDC=([0-9\.]+)V VAC=([0-9\.]+)V VPOE=([0-9\.]+)V', data.decode())[0])
                logging.info("dc={}, vac={}, vpoe={}".format(
                    self.dc, self.vac, self.vpoe))
            except:
                logging.error("data not parsed: %s" % data)

    def connection_lost(self, exc):
        logging.warn('port closed')
        self.transport.loop.stop()
        sys.exit(1)


def main():

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    asyncio.set_event_loop(uvloop.new_event_loop())

    loop = asyncio.get_event_loop()

    server_sanic = app.create_server(
        host="0.0.0.0", port=args.port, return_asyncio_server=True)
    task_sanic = asyncio.ensure_future(server_sanic)

    coro = serial_asyncio.create_serial_connection(
        loop, Serial, args.serial, baudrate=args.baud)
    task_serial = asyncio.ensure_future(coro)

    signal(SIGINT, lambda s, f: sys.exit(1))
    loop.run_forever()

main()
