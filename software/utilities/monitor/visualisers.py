from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QSurfaceFormat
import moderngl
from pywavefront import Wavefront
from pyrr import Matrix44
from scipy.spatial.transform import Rotation
from PIL import Image
from ui_noisewidget import Ui_NoiseWidget
from si_prefix import si_format
from pathlib import Path

# Hackish way of importing my free body code without releasing a package
import sys
import pathlib
parent = pathlib.Path(__file__).parent.resolve()
sys.path.append(str(parent / "../force_analysis/"))
import free_body


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


class ForceTorqueDisplay(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        separation = 2 * np.pi * 25e-3 * 25.0 / 360.0
        self._haptick = free_body.Haptick(25e-3, separation, 25e-3, separation, 20e-3)
        
        format = QSurfaceFormat()
        format.setVersion(3, 3)
        format.setProfile(QSurfaceFormat.CoreProfile)
        format.setSamples(16)
        self.setFormat(format)

        self.ctx = None

        self.scene = Wavefront(Path(__file__).parent / 'assets' / 'cube.obj')

        self._translation = np.zeros(3)
        self._rotation = Rotation.from_rotvec([0.0, 0.0, 0.0])

    def add_values(self, values):
        force, torque = self._haptick.applied(np.roll(-values[-1, ...], 1))
        haptick_to_world = Rotation.from_rotvec([0.0, 0.0, np.pi / 2])
        world_to_eye = Rotation.from_euler('ZX', [3.0 * np.pi / 4.0, -np.pi / 4.0])
        self._translation += (world_to_eye * haptick_to_world).apply(force[:, 0] / 1e-4)
        self._rotation = self._rotation * Rotation.from_rotvec((world_to_eye * haptick_to_world).apply(torque[:, 0] / -1e-5))
        self.update()
    
    def paintGL(self):
        if self.ctx is None:
            self.init()
        self.render()
    
    def init(self):
        self.ctx = moderngl.create_context()
        self.prog = self.ctx.program(
            vertex_shader='''
                #version 330
                uniform mat4 Mvp;
                in vec3 in_position;
                in vec3 in_normal;
                in vec2 in_texcoord;
                out vec3 v_vert;
                out vec3 v_norm;
                out vec2 v_text;
                void main() {
                    v_vert = in_position;
                    v_norm = in_normal;
                    v_text = in_texcoord;
                    gl_Position = Mvp * vec4(in_position, 1.0);
                }
            ''',
            fragment_shader='''
                #version 330
                uniform sampler2D Texture;
                uniform vec4 Color;
                uniform vec3 Light;
                in vec3 v_vert;
                in vec3 v_norm;
                in vec2 v_text;
                out vec4 f_color;
                void main() {
                    float lum = dot(normalize(v_norm), normalize(v_vert - Light));
                    lum = acos(lum) / 3.14159265;
                    lum = clamp(lum, 0.0, 1.0);
                    lum = lum * lum;
                    lum = smoothstep(0.0, 1.0, lum);
                    lum *= smoothstep(0.0, 80.0, v_vert.z) * 0.3 + 0.7;
                    lum = lum * 0.8 + 0.2;
                    vec3 color = texture(Texture, v_text).rgb;
                    color = color * (1.0 - Color.a) + Color.rgb * Color.a;
                    f_color = vec4(color * lum, 1.0);
                }
            ''',
        )

        self.light = self.prog['Light']
        self.color = self.prog['Color']
        self.mvp = self.prog['Mvp']

        self.vbo = self.ctx.buffer(np.array(self.scene.materials['Material'].vertices, dtype=np.float32))
        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo, '2f 3f 3f', 'in_texcoord', 'in_normal', 'in_position')
            ],
        )

        with Image.open('assets/' + self.scene.materials['Material'].texture.image_name) as im:
            im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            self.texture = self.ctx.texture(im.size, 4, im.tobytes())

    def render(self):
        self.ctx.clear(1.0, 1.0, 1.0)
        self.ctx.enable(moderngl.DEPTH_TEST)

        proj = Matrix44.perspective_projection(45.0, self.width() / self.height(), 0.1, 1000.0)
        lookat = Matrix44.look_at(
            (4.0, 4.0, 4.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
        )

        translate = Matrix44.from_translation(self._translation)
        rotate = Matrix44.from_quaternion(self._rotation.as_quat())

        self.light.write(((translate * rotate) @ np.array([[4.0], [1.0], [6.0], [1.0]]))[:3].astype('f4'))
        self.color.value = (1.0, 1.0, 1.0, 0.25)
        self.mvp.write((proj * lookat * translate * rotate).astype('f4'))

        self.texture.use()
        self.vao.render()