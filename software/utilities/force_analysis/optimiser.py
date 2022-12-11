from free_body import Haptick
import numpy as np
import matplotlib.pyplot as plt
plt.ion()
import pyswarms as ps
from pyswarms.utils.functions import single_obj as fx

class EvennessError:
    def __init__(self, nominal_force, nominal_torque, height=20.0e-3, samples=50):
        self.nominal_force = nominal_force
        self.nominal_torque = nominal_torque
        self.height = height

        # Generate a bunch of forces and torques spread across the unit sphere
        uniform_sphere = self._fibonacci_sphere(samples)
        self.forces = nominal_force * uniform_sphere
        self.torques = nominal_torque * uniform_sphere
        self._null = np.zeros((samples, 3))
    
    def __call__(self, x):
        errors = []
        for p in x:
            knobby = Haptick(p[0], p[1] * p[0], p[2], p[3] * p[2], self.height)

            # Find the upward reaction force for applied forces and torques
            z_for_forces = knobby.truss_force_components(self.forces, self._null)[2, ...]
            z_for_torques = knobby.truss_force_components(self._null, self.torques)[2, ...]

            # Calculate the RMS of the reaction forces for each applied force
            # and torque
            rms = np.linalg.norm(np.vstack((z_for_forces, z_for_torques)), axis=1)

            # Our error is the variation in these.
            error = np.std(rms)
            errors.append(error)
        return errors
    
    @staticmethod
    def _fibonacci_sphere(samples):
        phi = np.pi * (3.0 - np.sqrt(5.0))
        y = np.linspace(1, -1, samples)
        r = np.sqrt(1 - y ** 2)
        t = np.arange(samples) * phi
        x = np.cos(t) * r
        z = np.sin(t) * r
        return np.vstack((x, y, z)).T

options = {'c1': 0.5, 'c2': 0.3, 'w':0.9}
bounds = ([10e-3, 0.0, 10e-3, 0.0], [25e-3, np.pi / 3.0, 25e-3, np.pi / 3.0])
optimizer = ps.single.GlobalBestPSO(n_particles=100, dimensions=4, options=options, bounds=bounds)
error_function = EvennessError(20e-3*9.81, 20e-3*9.81*30e-3, height=20e-3, samples=100)
best_cost, best_pos = optimizer.optimize(error_function, iters=1000)
haptick = Haptick(best_pos[0], best_pos[1] * best_pos[0], best_pos[2], best_pos[3] * best_pos[2], error_function.height)
trusses = haptick.trusses
ax = plt.axes(projection='3d')
ax.scatter3D(*trusses[..., 0])
ax.scatter3D(*trusses[..., 1])
for truss in trusses.transpose((1, 0, 2)):
    ax.plot3D(*truss, 'k')
ax.set_box_aspect((np.ptp(trusses[0, ...]), np.ptp(trusses[1, ...]), np.ptp(trusses[2, ...])))