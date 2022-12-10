import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow
from ui_mainwindow import Ui_MainWindow
from interface import Haptick


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.haptick = Haptick()
    
        self.ui.serialPortCombo.addItems(self.haptick.list_ports())
        self.ui.serialConnectButton.clicked.connect(self._connect)

        self.ui.filterCutoffSlider.valueChanged.connect(self._change_filter_cutoff)

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
        self.ui.serialConnectButton.clicked.disconnect(self._connect)
        self.ui.serialConnectButton.clicked.connect(self._disconnect)
    
    def _disconnect(self):
        self.timer.stop()
        self.haptick.disconnect()
        self.ui.serialPortCombo.setDisabled(False)
        self.ui.serialConnectButton.setText("Connect")
        self.ui.serialConnectButton.clicked.disconnect(self._disconnect)
        self.ui.serialConnectButton.clicked.connect(self._connect)
    
    def _update(self):
        vals = self.haptick.get_vals()
        if vals is not None:
            self.ui.voltagePlot.add_values(vals)
            self.ui.psdPlot.add_values(vals)
            self.ui.noiseWidget.add_values(vals)
    
    def _change_filter_cutoff(self, value):
        if value == 99:
            self.haptick.filter_cutoff = None
            self.ui.filterCutoffValue.setText("Disabled")
        else:
            frequency = 10 ** (value * 4.29 / 98 - 1)
            self.haptick.filter_cutoff = frequency
            self.ui.filterCutoffValue.setText(f"{frequency:.1f} Hz")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())