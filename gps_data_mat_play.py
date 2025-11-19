import pprint
import threading
import time

import scipy.io
import os
import PySignal


class PlayGPSMat:
    new_gps_pos = PySignal.ClassSignal()

    def __init__(self, filename, start_timeout=5, time_between_gps_pos=1):
        self.gps_data = scipy.io.loadmat(filename)
        # import pprint
        # pprint.pprint(self.gps_data)
        # self.new_gps_pos.connect(self.show_new_pos)
        self.timeout = time_between_gps_pos
        threading.Timer(start_timeout, self.start).start()

    def start(self):
        x = self.gps_data.get("Easting")
        y = self.gps_data.get("Northing")
        for i in range(len(x)):
            # print("x: {}, y: {}".format(x[i], y[i]))
            self.new_gps_pos.emit(x[i], y[i])
            time.sleep(self.timeout)

    def show_new_pos(self, x, y):
        # print("new_pos signal with data {}, {}".format(x/100000, y/100000))
        pass


if __name__ == "__main__":
    print("test")
    filename = "{}/{}".format(os.getcwd(), "data/AguasVivasGPSData.mat")
    test_gps = PlayGPSMat(filename)
