import serial
import serial.tools.list_ports
from multiprocessing import Process, Pipe
from select import select
import numpy as np
import scipy.signal as ss
from dataclasses import dataclass


@dataclass(frozen=True)
class BiasCorrectionSettings:
    enabled: bool = True
    threshold: float = 0.5e-6
    time: float = 1.0


class SerialProcess:
    GAIN = (2.4 / 64) / 2.0 ** 24

    def __init__(self, port, filter_cutoff, bias_correction):
        self.port = port
        
        self._bias = None
        self._counter = 0
        self._cache = np.zeros((15625, 6))

        self.filter_cutoff = filter_cutoff
        self.bias_correction = bias_correction
    
    def __call__(self, conn):
        with serial.Serial(self.port, timeout=0.1) as s:
            self.__sync(s)
            samples_to_filter = []
            samples_to_send = []
            while True:
                # Handle incoming messages
                if conn.poll():
                    message = conn.recv()
                    if message["command"] == "close":
                        return
                    elif message["command"] == "set_filter_cutoff":
                        self.filter_cutoff = message["value"]
                    elif message["command"] == "set_bias_correction":
                        self.bias_correction = message["value"]
                
                # Read, parse and (sometimes) filter data
                data = s.read(24)
                if parsed := self.__parse(data):
                    samples_to_filter.append(parsed)
                    if len(samples_to_filter) == 64:
                        samples_to_send.append(self.__filter(samples_to_filter))
                        samples_to_filter = []
                else:
                    self.__sync(s)
                
                # Send data
                if samples_to_send and not self.__pipe_full(conn):
                    conn.send(np.vstack(samples_to_send))
                    samples_to_send = []
    
    def __pipe_full(self, conn):
        _, w, _ = select([], [conn], [], 0.0)
        return len(w) == 0
    
    def __sync(self, s):
        s.read_until(b'\x05\x3f')
        s.read(22)
    
    def __parse(self, data):
        if data[:2] == b"\x05\x3f" and len(data) == 24:
            args = [iter(data[3:-3])] * 3
            return [int.from_bytes(b, byteorder="big", signed=True) * self.GAIN for b in zip(*args)]
    
    def __filter(self, samples):
        if self._filter_coeff is not None:
            if self._filter_state is None:
                self._filter_state = np.dstack([ss.sosfilt_zi(self._filter_coeff) * x for x in samples[0]])
            result, self._filter_state = ss.sosfilt(self._filter_coeff, samples, axis=0, zi=self._filter_state)
        else:
            result = np.vstack(samples)
        
        self._cache = np.roll(self._cache, result.shape[0], axis=0)
        self._cache[:result.shape[0], ...] = result[::-1, ...]

        self._counter += result.shape[0]

        if self._counter > self._cache.shape[0]:
            if self._bias is None:
                index = int(np.round(3.0 / 256.0e-6))
                self._bias = self._cache[:index, ...].mean(axis=0)
            elif self.bias_correction.enabled:
                index = int(np.round(self.bias_correction.time / 256.0e-6))
                standard_deviations = self._cache[:index, ...].std(axis=0)
                if np.all(standard_deviations < self.bias_correction.threshold):
                    self._bias = self._cache[:index, ...].mean(axis=0)

        if self._bias is None:
            return np.full_like(result, np.nan)
        else:
            return result - self._bias
    
    @property
    def filter_cutoff(self):
        return self.__filter_cutoff

    @filter_cutoff.setter
    def filter_cutoff(self, value):
        if value is None:
            self._filter_coeff = None
        else:
            self._filter_state = None
            self._filter_coeff = ss.butter(4, value, output='sos', fs=1/256e-6)
        self.__filter_cutoff = value


class Haptick:
    def __init__(self):
        self._proc = None
        self.__filter_cutoff = None
        self.__bias_correction = BiasCorrectionSettings()
        
    def list_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect(self, port):
        self._conn, conn = Pipe()
        proc = SerialProcess(port, self.__filter_cutoff, self.__bias_correction)
        self._proc = Process(target=proc, args=(conn, ))
        self._proc.start()
    
    def disconnect(self):
        self._send_command("close")
        if self._proc:
            self._proc.join()
    
    def get_vals(self):
        vals = []
        while self._conn.poll():
            vals.append(self._conn.recv())
        return np.vstack(vals) if vals else None
    
    @property
    def bias_correction(self):
        return self.__bias_correction
    
    @bias_correction.setter
    def bias_correction(self, value):
        self.__bias_correction = value
        self._send_command("set_bias_correction", value=self.__bias_correction)
    
    @property
    def filter_cutoff(self):
        return self.__filter_cutoff
    
    @filter_cutoff.setter
    def filter_cutoff(self, value):
        self.__filter_cutoff = value
        self._send_command("set_filter_cutoff", value=self.__filter_cutoff)
    
    def _send_command(self, command, **kwargs):
        try:
            message = kwargs
            message.update({"command": command})
            self._conn.send(message)
        except (EOFError, BrokenPipeError, AttributeError):
            pass


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