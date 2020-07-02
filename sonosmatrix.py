#!venv/bin/python

import argparse
import logging
import sys
import threading
import time
from pprint import pprint
from queue import Empty

from soco import SoCo
from soco.events import event_listener

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from soco.exceptions import SoCoFault

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)
sonos_controller = None




# class RunText(SampleBase):
#     def __init__(self, *args, **kwargs):
#         super(RunText, self).__init__(*args, **kwargs)
#         # self.parser.add_argument("-t", "--text", help="The text to scroll on the RGB LED panel", default="Hello world!")
#
#     def run(self):
#         offscreen_canvas = self.matrix.CreateFrameCanvas()
#         font = graphics.Font()
#         font.LoadFont(".fonts/7x13.bdf")
#         textColor = graphics.Color(255, 128, 0)
#         pos = offscreen_canvas.width
#         my_text = "Hello from Sonos"
#
#         while True:
#             offscreen_canvas.Clear()
#             len = graphics.DrawText(offscreen_canvas, font, pos, 10, textColor, my_text)
#             pos -= 1
#             if (pos + len < 0):
#                 pos = offscreen_canvas.width
#
#             time.sleep(0.05)
#             offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    # Configuration for the matrix
    options = RGBMatrixOptions()
    options.cols = 64
    options.rows = 32
    options.chain_length = 1
    options.parallel = 1
    #options.hardware_mapping = 'adafruit-hat'  # If you have an Adafruit HAT: 'adafruit-hat'
    matrix = RGBMatrix(options=options)
    offscreen_canvas = matrix.CreateFrameCanvas()

    text = None

    def __init__(self, text, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.text = text

    def run(self):
        logging.info("Thread %s: starting", self.text)
        font = graphics.Font()
        font.LoadFont("/home/pi/led/rpi-rgb-led-matrix/fonts/sonos/5x7.bdf")
        textColor = graphics.Color(255, 255, 0)
        pos = self.offscreen_canvas.width
        while True:
            self.offscreen_canvas.Clear()
            length = graphics.DrawText(self.offscreen_canvas, font, pos, 10, textColor, self.text)
            pos -= 1
            if pos + length < 0:
                pos = self.offscreen_canvas.width

            time.sleep(0.05)
            self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)
        logging.info("Thread %s: finishing", self.text)

    def stop(self):
        # self.offscreen_canvas.Clear()
        # self.matrix.Clear()
        self._stop_event.set()

    def stopped(self):
        self.offscreen_canvas.Clear()
        self.matrix.Clear()
        return self._stop_event.is_set()


def main(args):
    x = StoppableThread("test")
    x.daemon = True

    if sonos_controller:
        # print out the events as they arise
        # sub = sonos_controller.renderingControl.subscribe()
        sub2 = sonos_controller.avTransport.subscribe()

        while True:
            # try:
            #     event = sub.events.get(timeout=0.5)
            #     pprint(event.variables)
            # except Empty:
            #     pass
            try:
                event = sub2.events.get(timeout=0.5)
                pprint(event.variables)
                print(event.variables['current_track_meta_data'].title)
                if event.variables['current_track_uri'] == 'x-rincon:RINCON_949F3ED42D3F01400':
                    my_text = 'TV'
                else:
                    my_text = event.variables['current_track_meta_data'].title
                if x.is_alive():
                    x.stop()
                    x = StoppableThread(my_text)

                x.text = my_text
                # if not x.is_alive():
                x.start()
                print("running in background")
            except SoCoFault:
                print("error")
                pass
            except Empty:
                pass

            except KeyboardInterrupt:
                # sub.unsubscribe()
                sub2.unsubscribe()
                event_listener.stop()
                break

    else:
        logger.error(f'Device "${args.sonos_host}" not found!')
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sonos Matrix')
    parser.add_argument('--sonos-host', '-s', help='the Sonos controller hostname', required=True)
    args = parser.parse_args()

    sonos_host = args.sonos_host

    sonos_controller = SoCo(sonos_host)
    logger.info(f'Sonos controller at {sonos_host}: {sonos_controller.get_speaker_info()["zone_name"]} ({sonos_controller.get_speaker_info()["model_name"]})')

    main(args)