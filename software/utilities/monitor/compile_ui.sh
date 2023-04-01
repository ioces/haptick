#!/bin/bash

pyside6-uic main_window.ui -o ui_mainwindow.py
pyside6-uic noise_widget.ui -o ui_noisewidget.py
pyside6-uic cube_control.ui -o ui_cubecontrol.py
pyside6-rcc resources.qrc -o resources_rc.py