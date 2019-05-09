#import serial
#import serial.threaded
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

app = Sanic(__name__)


parser = argparse.ArgumentParser()
parser.add_argument('--serial', help="serial port name", default='/dev/ttyACM0')
parser.add_argument('--baud', type=int, help='set baud rate, default: %(default)s', default=9600)
parser.add_argument('--poll', type=int, help='poll time seconds, default: %(default)s', default=1)
parser.add_argument('--port', type=int, help='http server port %(default)s', default=8000)
parser.add_argument('--debug', action='store_true', help='debug', default=False)

args = parser.parse_args()



class Serial(asyncio.Protocol):
    def __init__(self, *args, **kwargs):
        super()
        self.dc, self.vac, self.vpoe = 0,0,0
        app.add_route(self.api, '/')


    #@app.route('/')
    async def api(self, request):
        return json({'dc': self.dc, 'vac': self.vac, 'vpoe': self.vpoe, 'poe': 'on' if self.vpoe > 0 else 'off', 'state': 'on battery' if self.vac <= 0 else '220V'})    
    
    def connection_made(self, transport):
        
        self.transport = transport
        logging.info('port opened: %s' % args.serial)
        transport.serial.rts = False  # You can manipulate Serial object via transport
        loop = asyncio.get_running_loop()
        #loop.run_in_executor(None, self.poll)
        asyncio.ensure_future(self.poll())
        #loop.run_until_complete(self.poll())
        

    async def poll(self):
        while True:
            self.transport.write(b'infopower\r')  # Write serial data via transport
            await asyncio.sleep(args.poll)

    def data_received(self, data):
        #print('data received', repr(data))
        #if b'\n' in data:
        #    self.transport.close()
        if data and data[:4] == b'VDC=':
            try:
                self.dc, self.vac, self.vpoe = map(float, re.findall('VDC=([0-9\.]+)V VAC=([0-9\.]+)V VPOE=([0-9\.]+)V', data.decode())[0])
                logging.info("dc={}, vac={}, vpoe={}".format(self.dc, self.vac, self.vpoe))
            except:
                logging.error("data not parsed: %s" % data)
        else:
            logging.debug("skip:%s", data)



    def connection_lost(self, exc):
        logging.warn('port closed')
        self.transport.loop.stop()
        sys.exit(1)

    def pause_writing(self):
        print('pause writing')
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print('resume writing')


# class SerialToNet(serial.threaded.Protocol):
#     """serial->socket"""

#     def __init__(self):
#         pass

#     def __call__(self):
#         return self

#     def data_received(self, data):
#         if data and data[:3] == b'DC=':
#             try:
#                 dc,vac,vpoe = re.findall('DC=([0-9\.]+)V VAC=([0-9\.]+)V VPOE=([0-9\.]+)V', data.decode())[0]
#                 logging.info("dc={}, vac={}, vpoe={}".format(dc, vac, vpoe))
#             except:
#                 logging.error("data not parsed: %s" % data)
#         else:
#             logging.debug("skip:%s", data)


# @app.route('/')
# async def test(request):
#     return json({'hello': 'world'})


def main():

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    asyncio.set_event_loop(uvloop.new_event_loop())
    
    loop = asyncio.get_event_loop()

    server_sanic = app.create_server(host="0.0.0.0", port=args.port, return_asyncio_server=True)
    task_sanic = asyncio.ensure_future(server_sanic)

    coro = serial_asyncio.create_serial_connection(loop, Serial, args.serial, baudrate=args.baud)
    task_serial = asyncio.ensure_future(coro)

    signal(SIGINT, lambda s, f: sys.exit(1))
    #try:
    loop.run_forever()
    #except:
    #    loop.stop()






    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(concurrent())

    # #coro = serial_asyncio.create_serial_connection(loop, Output, args.port, baudrate=args.baud)

    # # sanicserver = app.create_server(host='0.0.0.0', port=args.port)
    # # asyncio.ensure_future(sanicserver)

    # #loop.run_until_complete(coro)

    # #loop.run_forever()
    # loop.close()

    #app.run(host='0.0.0.0', port=8000)

    # while True:
    #     ser = serial.serial_for_url(args.port, do_not_open=True)
    #     ser.baudrate = args.baud
    #     try:
    #         ser.open()
    #     except serial.SerialException as e:
    #         sys.stderr.write(
    #             'Could not open serial port {}: {}\n'.format(ser.name, e))
    #         time.sleep(args.poll)
    #         continue

    #     ser_to_net = SerialToNet()
    #     serial_worker = serial.threaded.ReaderThread(ser, ser_to_net)
    #     serial_worker.start()

    #     while True:
    #         # get a bunch of bytes and send them
    #         ser.write(b"infopower\r")

    #         time.sleep(args.poll)

    #     serial_worker.stop()


main()
