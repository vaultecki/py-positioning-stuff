import numpy as np
import math
import requests
from io import BytesIO
from PIL import Image


def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    x_tile = int((lon_deg + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return x_tile, y_tile


def num2deg(x_tile, y_tile, zoom):
    n = 2.0 ** zoom
    lon_deg = x_tile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y_tile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


def get_image_osm_tile(lat_deg, lon_deg, delta_lat, delta_long, zoom):
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"}
    osm_url = r"http://a.tile.openstreetmap.org/{0}/{1}/{2}.png"
    x_min, y_max = deg2num(lat_deg, lon_deg, zoom)
    x_max, y_min = deg2num(lat_deg + delta_lat, lon_deg + delta_long, zoom)

    img = Image.new('RGB', ((x_max - x_min + 1) * 256 - 1, (y_max - y_min + 1) * 256 - 1))
    for x_tile in range(x_min, x_max + 1):
        for y_tile in range(y_min, y_max + 1):
            try:
                img_url = osm_url.format(zoom, x_tile, y_tile)
                print("Opening: " + img_url)
                img_str = requests.get(img_url, headers=headers)
                tile = Image.open(BytesIO(img_str.content))
                img.paste(tile, box=((x_tile - x_min) * 256, (y_tile - y_min) * 255))
            except Exception as e:
                print("Couldn't download image because of {}".format(e))
    return img


if __name__ == '__main__':
    import matplotlib.pyplot as plt

    a = get_image_osm_tile(48.75, 11.35, 0.075, 0.15, 13)
    fig = plt.figure()
    fig.patch.set_facecolor('white')
    plt.imshow(np.asarray(a))
    plt.show()

    # import folium
    # lat = 48.78671681959066
    # lon = 11.383740636850185
    # map = folium.Map(location=[lat, lon], zoom_start=20, control_scale=True)
    # folium.Marker(location=[lat, lon], icon=folium.Icon(color='red', icon='')).add_to(map)
    # # map.show_in_browser()
    # # map.save()
