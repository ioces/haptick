from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure
import numpy as np


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
        for line, d in zip(self.lines, self.y_data.T):
            line.set_ydata(d)
            line.set_xdata(self.x_data)
        self.axes.set_xlim(self.x_data[0], self.x_data[-1])
        self.draw()