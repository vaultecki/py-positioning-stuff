import copy
import datetime
import math
import os
import sys
import threading

import PIL.ImageQt

import numpy as np
import pandas as pd
import pynmea2
import pyqtgraph as pg
from matplotlib import pyplot as plt

import bert_utils.helper_maps
from bert_utils import helper_udp, helper_maps, helper_map_ned
from PyQt6 import QtWidgets, QtCore, QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


def pos_dec_2_min(x):
    x = float(x) / 1000
    grad = math.floor(x)
    x = x - grad
    x = x * 60
    return x


class ReceiveNmea(QtWidgets.QMainWindow):

    def __init__(self):
        super(ReceiveNmea, self).__init__()

        # init
        self.filename = os.path.join(os.getcwd(), "config/car_position_nmea_0183.xlsx")
        self.sock = helper_udp.UDPSocketClass(recv_port=19711)

        # widgets
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        self.graphWidget = pg.PlotWidget()
        self.speed_label = QtWidgets.QLabel("Speed: 0")
        self.map_widget = QtWidgets.QLabel()
        self.map_widget.setMaximumSize(500, 300)
        self.save_btn = QtWidgets.QPushButton("Save NMEA")
        self.save_checkbox = QtWidgets.QCheckBox("Rewrite previous file if exists")

        # layout
        layout = QtWidgets.QVBoxLayout()
        main_widget.setLayout(layout)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.map_widget)
        layout.addWidget(self.graphWidget)

        # second layout
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.addWidget(self.save_btn)
        bottom_layout.addWidget(self.save_checkbox)
        layout.addLayout(bottom_layout)

        # variables
        self.prev_sec = 0
        self.prev_deg = 0
        self.lat_list = []
        self.lon_list = []
        self.time_list = []
        self.nmea_list = []
        self.is_pixmap = False

        # graphWidget settings
        pen_1 = pg.mkPen(color=(255, 0, 0), width=5, style=QtCore.Qt.PenStyle.DotLine)
        pen_2 = pg.mkPen(color=(0, 255, 0), width=5, style=QtCore.Qt.PenStyle.DotLine)
        self.graphWidget.setTitle("GPS")
        self.graphWidget.setLabel('left', 'X: Degree')
        self.graphWidget.setLabel('bottom', 'Y: Time')
        self.graphWidget.addLegend()
        self.graphWidget.showGrid(x=True, y=True)

        ax = self.graphWidget.getAxis('bottom')  # set bottom ticks as string
        ax.setTicks([self.time_list])

        # graphWidget axisItems
        self.data_line_x = self.graphWidget.plot(self.time_list, self.lat_list, name="latitude", pen=pen_1, labels=self.time_list)
        self.data_line_y = self.graphWidget.plot(self.time_list, self.lon_list, name="longitude", pen=pen_2, labels=self.time_list)

        # connections
        self.sock.udp_recv_data.connect(self.on_receive_nmea)
        self.save_btn.clicked.connect(self.on_clicked_save_btn)

    def on_receive_nmea(self, nmea_str, addr):
        # handle with nmea
        nmea = pynmea2.parse(nmea_str)
        lat_deg_min = pos_dec_2_min(nmea.lat)
        lon_deg_min = pos_dec_2_min(nmea.lon)

        self.lat_list.append(lat_deg_min)
        self.lon_list.append(lon_deg_min)

        # getting time from NMEA
        t_hour = nmea.timestamp.hour
        t_min = nmea.timestamp.minute
        t_sec = nmea.timestamp.second
        time_str = "{}:\n{}:\n{}".format(t_hour, t_min, t_sec)
        self.time_list.append((len(self.time_list), time_str))

        act_sec = t_hour * 3600 + t_min * 60 + t_sec
        time_diff = act_sec - self.prev_sec
        self.prev_sec = act_sec

        # calculating degree and speed
        act_deg = lat_deg_min
        speed = str((self.prev_deg - act_deg) / time_diff)
        self.prev_deg = act_deg
        if speed[0] == "-":
            speed = speed[1:]
        self.speed_label.setText("Speed: {} deg/s".format(speed[:7]))

        # collecting nmea to save as file
        self.nmea_list.append([nmea, speed])

        # starting timer to plot
        threading.Timer(1, self.update_plot_data).start()

        # starting timer to show map
        if not self.is_pixmap:
            threading.Timer(0, self.update_map_image, args=[lat_deg_min, lon_deg_min]).start()

    def update_plot_data(self):
        self.data_line_x.setData(self.lat_list)
        self.data_line_y.setData(self.lon_list)
        print("new position plotted")

    def update_map_image(self, lat, lon):
        self.is_pixmap = True
        try:
            print("-----loading image-----")
            img = bert_utils.helper_maps.get_image_osm_tile(lat, lon, 0.075, 0.15, 10)
            pixmap = QtGui.QPixmap.fromImage(PIL.ImageQt.ImageQt(img))
            # pixmap = QtGui.QPixmap("config/bert.png")

            self.map_widget.setPixmap(pixmap)
            print("------image loaded------")
        except Exception as e:
            print("Error: {}".format(e))

    def on_clicked_save_btn(self):
        # self.save_btn.setDisabled(True)
        nmea_list = copy.deepcopy(self.nmea_list)   # list of nmea and speed
        time_list, lat_list, lat_dir_list, lon_list, lon_dir_list, speed_list = [], [], [], [], [], []

        for i in nmea_list:
            time_list.append("{}:{}:{}".format(i[0].timestamp.hour, i[0].timestamp.minute, i[0].timestamp.second))
            lat_list.append(pos_dec_2_min(i[0].lat))
            lat_dir_list.append(i[0].lat_dir)
            lon_list.append(pos_dec_2_min(i[0].lon))
            lon_dir_list.append(i[0].lon_dir)
            speed_list.append(i[1][:7])
        data = {'Time': time_list, 'Latitude in °': lat_list, 'Direction of latitude': lat_dir_list, 'Longitude in °': lon_list, 'Direction of longitude': lon_dir_list, 'Speed in °/s': speed_list}

        df = pd.DataFrame(data=data)

        if self.save_checkbox.isChecked():
            try:
                df_old = pd.read_excel(self.filename, engine='openpyxl')
                df = pd.concat([df_old, df], join='outer', ignore_index=True)
                df.to_excel(self.filename, index=False)
                print("Data has been rewritten")
            except Exception as e:
                print(e)
        else:
            filename = self.filename
            file_dir, extension = os.path.splitext(self.filename)
            counter = 1

            while os.path.exists(filename):
                filename = file_dir + " (" + str(counter) + ")" + extension
                counter += 1
            df.to_excel(filename)
            print("New file has been created")

        msg_box = QtWidgets.QMessageBox()
        msg_box.setText("Data saved successfully")
        msg_box.exec()

        # self.save_btn.setEnabled(True)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main = ReceiveNmea()
    main.show()
    sys.exit(app.exec())
