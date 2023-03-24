import sys
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from ui_mainwindow import Ui_MainWindow
import interface


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

        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._update)
    
    def closeEvent(self, event):
        super().closeEvent(event)
        self.timer.stop()
        self.haptick.disconnect()

    def _connect(self):
        self.haptick.connect(self.ui.serialPortCombo.currentText())
        self.timer.start()
        self.ui.serialPortCombo.setDisabled(True)
        self.ui.serialConnectButton.setText("Disconnect")
        self.ui.serialConnectButton.setIcon(QIcon("assets/plug-connected-x.svg"))
        self.ui.serialConnectButton.clicked.disconnect(self._connect)
        self.ui.serialConnectButton.clicked.connect(self._disconnect)
    
    def _disconnect(self):
        self.timer.stop()
        self.haptick.disconnect()
        self.ui.serialPortCombo.setDisabled(False)
        self.ui.serialConnectButton.setText("Connect")
        self.ui.serialConnectButton.setIcon(QIcon("assets/plug-connected.svg"))
        self.ui.serialConnectButton.clicked.disconnect(self._disconnect)
        self.ui.serialConnectButton.clicked.connect(self._connect)
    
    def _start_record(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Record File", "", "Comma Separated Values (*.csv)")
        if file_name:
            self.ui.recordButton.toggled.disconnect(self._start_record)
            self.ui.recordButton.toggled.connect(self._stop_record)
        else:
            # Temporarily block signals, change checked state and unblock. Else
            # we get called again when we try and uncheck the button.
            self.ui.recordButton.blockSignals(True)
            self.ui.recordButton.setChecked(False)
            self.ui.recordButton.blockSignals(False)
    
    def _stop_record(self):
        self.ui.recordButton.toggled.connect(self._start_record)
    
    def _update(self):
        vals = self.haptick.get_vals()
        if vals is not None:
            self.ui.voltagePlot.add_values(vals)
            self.ui.psdPlot.add_values(vals)
            self.ui.noiseWidget.add_values(vals)
            self.ui.cubeControl.add_values(vals)
    
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