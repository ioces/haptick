import serial
import serial.tools.list_ports
from multiprocessing import Process, Pipe
import numpy as np
import scipy.signal as ss


class SerialProcess:
    GAIN = (2.4 / 64) / 2.0 ** 24

    def __init__(self, port):
        self.port = port
        self._filter_coeff = ss.butter(4, 10.0, output='sos', fs=1/256e-6)
        self._filter_state = None
        self._bias = None
    
    def __call__(self, conn):
        with serial.Serial(self.port, timeout=0.1) as s:
            self.__sync(s)
            samples = []
            while True:
                if conn.poll():
                    message = conn.recv()
                    if message["command"] == "close":
                        return
                data = s.read(24)
                parsed = self.__parse(data)
                if parsed:
                    samples.append(parsed)
                    if len(samples) == 16:
                        result = self.__filter(samples)
                        conn.send(result)
                        samples = []
                else:
                    self.__sync(s)
    
    def __sync(self, s):
        s.read_until(b'\x05\x3f')
        s.read(22)
    
    def __parse(self, data):
        if data[:2] == b"\x05\x3f" and len(data) == 24:
            args = [iter(data[3:-3])] * 3
            return [int.from_bytes(b, byteorder="big", signed=True) * self.GAIN for b in zip(*args)]
    
    def __filter(self, samples):
        if self._filter_state is None:
            self._filter_state = np.dstack([ss.sosfilt_zi(self._filter_coeff) * x for x in samples[0]])
        result, self._filter_state = ss.sosfilt(self._filter_coeff, samples, axis=0, zi=self._filter_state)
        if self._bias is None:
            self._bias = result[-1, :]
        return result[-1, :] - self._bias


class Haptick:
    def list_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect(self, port):
        self._conn, conn = Pipe()
        proc = SerialProcess(port)
        self._proc = Process(target=proc, args=(conn, ))
        self._proc.start()
    
    def disconnect(self):
        try:
            self._conn.send({"command": "close"})
        except (EOFError, BrokenPipeError, AttributeError):
            pass
        self._proc.join()
    
    def get_vals(self):
        vals = []
        while self._conn.poll():
            vals.append(self._conn.recv())
        return vals


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    plt.ion()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    data = np.zeros((2560, 6))
    lines = ax.plot(data)
    ax.set_ylim(-50e-6, 50e-6)
    h = Haptick()
    h.connect("/dev/ttyACM0")
    while True:
        if vals := h.get_vals():
            data = np.roll(data, -len(vals), axis=0)
            data[-len(vals):, :] = vals
            for line, d in zip(lines, data.T):
                line.set_ydata(d)
        fig.canvas.flush_events()
    h.disconnect()