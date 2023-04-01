import sys
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from ui_mainwindow import Ui_MainWindow
import time
import interface
import numpy as np


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.haptick = interface.Haptick()
    
        self.ui.serialPortCombo.addItems(self.haptick.list_ports())
        self.ui.serialConnectButton.clicked.connect(self._connect)

        self.ui.recordButton.toggled.connect(self._start_record)

        self.ui.filterCutoffSlider.valueChanged.connect(self._change_filter_cutoff)
        self._change_filter_cutoff(self.ui.filterCutoffSlider.value())

        self.ui.biasGroupBox.clicked.connect(self._change_bias_correction)
        self.ui.biasThresholdSlider.valueChanged.connect(self._change_bias_correction)
        self.ui.biasTimeSlider.valueChanged.connect(self._change_bias_correction)
        self._change_bias_correction()

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(20)
        self.update_timer.timeout.connect(self._update)

        self.__file = None
    
    def closeEvent(self, event):
        super().closeEvent(event)
        if self.__file:
            self._stop_record()
        self.update_timer.stop()
        self.haptick.disconnect()

    def _connect(self):
        self.haptick.connect(self.ui.serialPortCombo.currentText())
        self.update_timer.start()
        self.ui.serialPortCombo.setDisabled(True)
        self.ui.serialConnectButton.setText("Disconnect")
        self.ui.serialConnectButton.setIcon(QIcon(":/icons/disconnect"))
        self.ui.serialConnectButton.clicked.disconnect(self._connect)
        self.ui.serialConnectButton.clicked.connect(self._disconnect)
    
    def _disconnect(self):
        self.update_timer.stop()
        self.haptick.disconnect()
        self.ui.serialPortCombo.setDisabled(False)
        self.ui.serialConnectButton.setText("Connect")
        self.ui.serialConnectButton.setIcon(QIcon(":/icons/connect"))
        self.ui.serialConnectButton.clicked.disconnect(self._disconnect)
        self.ui.serialConnectButton.clicked.connect(self._connect)
    
    def _start_record(self):
        # Temporarily stop the update timer while we get a filename and start
        # recording. There are two reasons for this:
        #
        # 1. With the 20ms timer, some bug in Qt means the save file dialog
        #    doesn't display, as the event loop spends all its time serving the
        #    timer.
        # 2. We want to start saving data from when the record button is hit. If
        #    we stop the timer, the interprocess queue will start to buffer all
        #    samples from when the timer is stopped, which means they'll all get
        #    written to disk when the timer starts again.
        timer_active = self.update_timer.isActive()
        self.update_timer.stop()

        # Get a filename and update the button state.
        file_name, _ = QFileDialog.getSaveFileName(self, "Record File", "", "Comma Separated Values (*.csv)")

        if file_name:
            self.__file = open(file_name, 'w')
            self.ui.recordButton.toggled.disconnect(self._start_record)
            self.ui.recordButton.toggled.connect(self._stop_record)
        else:
            # Temporarily block signals, change checked state and unblock. Else
            # we get called again when we try and uncheck the button.
            self.ui.recordButton.blockSignals(True)
            self.ui.recordButton.setChecked(False)
            self.ui.recordButton.blockSignals(False)
        
        # Start the timer again.
        if timer_active:
            self.update_timer.start()
    
    def _stop_record(self):
        self.__file.close()
        self.__file = None
        self.ui.recordButton.toggled.disconnect(self._stop_record)
        self.ui.recordButton.toggled.connect(self._start_record)
        self.ui.recordButton.setIcon(QIcon(":/icons/record"))
    
    def _update(self):
        vals = self.haptick.get_vals()

        if vals is not None:
            self.ui.voltagePlot.add_values(vals)
            self.ui.psdPlot.add_values(vals)
            self.ui.noiseWidget.add_values(vals)
            self.ui.cubeControl.add_values(vals)
            
            if self.__file:
                np.savetxt(self.__file, vals, fmt="%.3e", delimiter=",")
        
        if self.ui.recordButton.isChecked():
            if time.monotonic() % 1 > 0.5:
                self.ui.recordButton.setIcon(QIcon(":/icons/blank"))
            else:
                self.ui.recordButton.setIcon(QIcon(":/icons/record"))
    
    def _change_filter_cutoff(self, value):
        if value == 99:
            self.haptick.filter_cutoff = None
            self.ui.filterCutoffValue.setText("Disabled")
        else:
            frequency = 10 ** (value * 4.29 / 98 - 1)
            self.haptick.filter_cutoff = frequency
            self.ui.filterCutoffValue.setText(f"{frequency:.1f} Hz")
    
    def _change_bias_correction(self, *_):
        time = self.ui.biasTimeSlider.value() / 99.0 * 3.0 + 1.0
        threshold = self.ui.biasThresholdSlider.value() / 99.0 * 2.0e-6
        enabled = self.ui.biasGroupBox.isChecked()

        settings = interface.BiasCorrectionSettings(enabled, threshold, time)
        self.haptick.bias_correction = settings


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())