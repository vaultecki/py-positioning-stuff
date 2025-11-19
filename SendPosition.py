import datetime
import math
import os
import time
import pynmea2

import bert_utils.helper_udp
from gps_data_mat_play import PlayGPSMat
from bert_utils import helper_map_ned


class SendNmea:
    def __init__(self):
        filename = os.path.join(os.getcwd(), "data/AguasVivasGPSData.mat")
        self.gps_mat = PlayGPSMat(filename)
        self.gps_mat.new_gps_pos.connect(self.on_new_pos)
        # self.sock = bert_utils.helper_udp.UDPSocketClass(addr=[["172.16.79.255", 19711]], recv_port=19710)
        self.sock = bert_utils.helper_udp.UDPSocketClass(addr=[["127.0.0.1", 19711]], recv_port=19710)
        # pos = [east=36.028765528599, nord=42.6729361129556, height=0]

    def pos_mat_2_dec(self, x):
        return float(x/100000)

    def pos_dec_2_min(self, x):
        grad = math.floor(x)
        x = x - grad
        x = x * 60
        minute = math.floor(x)
        x = x - minute
        sekunde = x * 60
        # print("{}° {}' {}''".format(grad, minute, sekunde))
        return [grad, minute, sekunde]

    def on_new_pos(self, x, y):
        x_dec = self.pos_mat_2_dec(x)
        y_dec = self.pos_mat_2_dec(y)
        x_min_sec = self.pos_dec_2_min(x_dec)
        y_min_sec = self.pos_dec_2_min(y_dec)
        nmea_str = self.gen_nmea(x[0], y[0])
        self.sock.send_data(str(nmea_str))

    def gen_nmea(self, lat, lon):
        time_HHMMSS = datetime.datetime.now().strftime("%H%M%S")
        time_DDMMYY = datetime.datetime.now().strftime("%d%m%y")

        # nmea = pynmea2.GGA("$GPRMC,{time},A,{lat},N,{lon},E,{date},A*13".format(time=time_HHMMSS, lat=lat, lon=lon, date=time_DDMMYY))
        nmea = pynmea2.RMC('GP', 'RMC', (time_HHMMSS, 'A', str(lat/100)[:9], 'S', str(lon/100)[:10], 'E', time_DDMMYY))
        return nmea


if __name__ == "__main__":
    pos = SendNmea()
