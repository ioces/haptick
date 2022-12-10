from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from PySide6.QtWidgets import QWidget
from ui_noisewidget import Ui_NoiseWidget
from si_prefix import si_format


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        super().__init__(Figure())
        
        # Set figure and canvas background to be transparent
        self.figure.patch.set_facecolor('None')
        self.setStyleSheet("background-color: transparent;")
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.figure.tight_layout()


class ChannelVoltage(MplCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Add some axes
        self.axes = self.figure.add_subplot(111)
        self.axes.set_ylabel("Voltage (V)")
        self.axes.set_ylim(-50e-6, 50e-6)
        self.axes.set_xlabel("Time (s)")
        self.axes.set_xlim(-4.0, 0.0)

        # Let's plot something
        self.x_data = np.linspace(-4 + 256e-6, 0.0, 15625)
        self.y_data = np.zeros((15625, 6))
        self.lines = self.axes.plot(self.x_data, self.y_data)
    
    def add_values(self, values):
        value_count = len(values)
        self.y_data = np.roll(self.y_data, -value_count, axis=0)
        self.x_data = np.roll(self.x_data, -value_count, axis=0)
        self.y_data[-value_count:, :] = values
        prev_x = self.x_data[-value_count-1]
        self.x_data[-value_count:] = np.linspace(prev_x + 256e-6, prev_x + 256e-6 + (value_count - 1) * 256e-6, value_count)
        if self.isVisible():
            for line, d in zip(self.lines, self.y_data.T):
                line.set_ydata(d)
                line.set_xdata(self.x_data)
            self.axes.set_xlim(self.x_data[0], self.x_data[-1])
            self.draw()


class ChannelPsd(MplCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Add some axes
        self.axes = self.figure.add_subplot(111)

        # Plot something
        self.axes.set_ylim(-300.0, -100.0)
        self.data = np.random.rand(1024, 6) * 1.2e-6
        for d in self.data.T:
            self.axes.psd(d, Fs=1/256e-6)
    
    def add_values(self, values):
        value_count = len(values)
        self.data = np.roll(self.data, -value_count, axis=0)
        self.data[-value_count:, :] = values
        if self.isVisible():
            self.axes.clear()
            self.axes.set_ylim(-300.0, -100.0)
            for d in self.data.T:
                self.axes.psd(d, Fs=1/256e-6)
            self.draw()


class NoiseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_NoiseWidget()
        self.ui.setupUi(self)
        self._channel_labels = [
            self.ui.channel_1,
            self.ui.channel_2,
            self.ui.channel_3,
            self.ui.channel_4,
            self.ui.channel_5,
            self.ui.channel_6
        ]

        self.data = np.zeros((4096, 6))
    
    def add_values(self, values):
        value_count = len(values)
        self.data = np.roll(self.data, -value_count, axis=0)
        self.data[-value_count:, :] = values
        if self.isVisible():
            rms = np.std(self.data, axis=0)
            for label, value in zip(self._channel_labels, rms):
                label.setText(f"{si_format(value, precision=2)}V")