#!venv/bin/python
import argparse
import logging
import sys
import threading
import time

import requests
from geographiclib.geodesic import Geodesic
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)

cardinal_arrows_map = {
    'N': '↑',
    'NE': '↗',
    'E': '→',
    'SE': '↘',
    'S': '↓',
    'SW': '↙',
    'W': '←',
    'NW': '↖'
}

aircraft_map = {}
aircraft_change = False


def get_direction_from_heading(degrees):
    direction = None
    if 0 <= degrees < 22.5:
        direction = 'N'
    elif 22.5 <= degrees < 67.5:
        direction = 'NE'
    elif 67.5 <= degrees < 112.5:
        direction = 'E'
    elif 112.5 <= degrees < 157.5:
        direction = 'SE'
    elif 157.5 <= degrees < 202.5:
        direction = 'S'
    elif 202.5 <= degrees < 247.5:
        direction = 'SW'
    elif 247.5 <= degrees < 292.5:
        direction = 'W'
    elif 292.5 <= degrees < 337.5:
        direction = 'NW'
    elif 337.5 <= degrees <= 360:
        direction = 'N'
    return direction


def get_aircraft(feeder_url):
    global aircraft_map, aircraft_change
    logger.info('Getting aircraft')
    r = requests.get(f'http://{feeder_url}/flights.json')
    # "x4a914f": ["4A914F", 59.2893, 18.1239, 305, 2275, 179, "5322", 0, "", "", 1415781759, "", "", "", 0, -640, "SCW10"]
    new_aircraft_map = r.json()
    logger.info(new_aircraft_map)
    if new_aircraft_map != aircraft_map:
        aircraft_map = new_aircraft_map
        aircraft_change = True
    else:
        aircraft_change = False


def main(args):
    device_lat = args.device_lat
    device_long = args.device_long
    feeder_url = args.fr24_feeder_host
    fonts_home = args.fonts_home

    # Configuration for the LED matrix
    options = RGBMatrixOptions()
    options.cols = 64
    options.rows = 32
    options.chain_length = 1
    options.brightness = 40
    options.pwm_dither_bits = 1
    options.pwm_lsb_nanoseconds = 50
    options.parallel = 1
    options.gpio_slowdown = 2  # reduces flicker
    #options.hardware_mapping = 'regular'  # If you have an Adafruit HAT: 'adafruit-hat'

    matrix = RGBMatrix(options=options)
    font = graphics.Font()
    font.LoadFont(f'{fonts_home}/5x7.bdf')
    font2 = graphics.Font()
    font2.LoadFont(f'{fonts_home}/6x10.bdf')

    green = graphics.Color(0, 255, 0)
    graphics.DrawText(matrix, font, 0, 7, green, 'No aircraft')
    graphics.DrawText(matrix, font, 0, 14, green, 'found')

    try:
        print('Press CTRL-C to stop.')
        while True:
            t = threading.Thread(target=get_aircraft(feeder_url))
            t.run()
            if aircraft_change:
                logger.info('Refreshing aircraft list')
                matrix.Clear()
                index = 1
                if len(aircraft_map.keys()) > 0:
                    for aircraft in aircraft_map.keys():
                        matrix.Clear()
                        aircraft_mode_s_transponder = aircraft_map.get(aircraft)[0]
                        aircraft_lat = aircraft_map.get(aircraft)[1]
                        aircraft_long = aircraft_map.get(aircraft)[2]
                        aircraft_ground_speed = aircraft_map.get(aircraft)[5]
                        aircraft_squawk = aircraft_map.get(aircraft)[6]
                        aircraft_callsign = aircraft_map.get(aircraft)[-1]

                        # Draw ADS-B Mode S transponder code
                        graphics.DrawText(matrix, font, 0, index * 7, green, f'ModeS: {aircraft_mode_s_transponder}')

                        # Draw aircraft callsign
                        if aircraft_callsign:
                            graphics.DrawText(matrix, font, 0, (index + 1) * 7, green, f'Sign:  {aircraft_callsign}')
                        else:
                            graphics.DrawText(matrix, font, 0, (index + 1) * 7, green, f'Sign: unknown')

                        if aircraft_lat and aircraft_long:
                            geodesic_dict = Geodesic.WGS84.Inverse(float(device_lat), float(device_long), aircraft_lat,
                                                                   aircraft_long)
                            azimuth = geodesic_dict['azi1']
                            distance_meters = geodesic_dict['s12']
                            distance_miles = 0.000621371 * distance_meters
                            heading = float(azimuth)
                            logger.info(f'heading: {heading:.3f}')

                            # Correct for negative headings
                            if heading < 0:
                                heading = heading + 360
                                logger.info(f'corrected heading: {heading:.3f}')

                            cardinal_direction = get_direction_from_heading(heading)
                            logger.info(f'cardinal direction: {cardinal_direction}')

                            # adjust heading from display orientation
                            display_heading = 240.0
                            adjusted_heading = 360 - display_heading + heading
                            logger.info(f'adjusted heading: {adjusted_heading:.3f}°')
                            # correct for heading over 360°
                            if adjusted_heading > 360:
                                adjusted_heading = adjusted_heading - 360
                                logger.info(f'adjusted heading (corrected): {adjusted_heading:.3f}°')
                            arrow_direction = get_direction_from_heading(adjusted_heading)

                            # Draw cardinal direction and arrow
                            graphics.DrawText(matrix, font2, 0, ((index + 2) * 7) + 1, green, cardinal_direction)
                            graphics.DrawText(matrix, font2, 0, ((index + 3) * 7) + 2, green, cardinal_arrows_map[
                                arrow_direction])
                            graphics.DrawText(matrix, font2, 22, ((index + 3) * 7) + 2, green, f'{distance_miles:.2f} mi')
                        else:
                            graphics.DrawText(matrix, font2, 0, ((index + 2) * 7) + 1, green, '?')
                            graphics.DrawText(matrix, font2, 0, ((index + 3) * 7) + 2, green, '?')
                        if aircraft_ground_speed:
                            graphics.DrawText(matrix, font2, 22, ((index + 2) * 7) + 1, green, f'{aircraft_ground_speed} kts')
                        time.sleep(10)
                else:
                    graphics.DrawText(matrix, font, 0, 7, green, "No aircraft")
                    graphics.DrawText(matrix, font, 0, 14, green, "found")

            time.sleep(60)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Display flights on LED matrix')
    parser.add_argument('--device-lat', help='device latitude (in degrees)', required=True)
    parser.add_argument('--device-long', help='device longitude (in degrees)', required=True)
    parser.add_argument('--fr24-feeder-host', help='FR24 Feeder host and port', default='localhost:8754')
    parser.add_argument('--fonts-home', help='fonts base directory')
    args = parser.parse_args()
    main(args)