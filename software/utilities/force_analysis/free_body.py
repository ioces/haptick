import numpy as np

class Haptick:
    TRIANGLE = np.linspace(0, 2.0 * np.pi, 3, endpoint = False)

    def __init__(self, top_radius, top_separation, bottom_radius, bottom_separation, height):
        self.top_radius = top_radius
        self.top_separation = top_separation
        self.bottom_radius = bottom_radius
        self.bottom_separation = bottom_separation
        self.height = height

        self._init_trusses()
    
    def truss_force_components(self, applied_force, applied_torque):
        magnitudes = self.truss_force_magnitudes(applied_force, applied_torque)
        return self._unit_forces[..., np.newaxis] * magnitudes[np.newaxis, ...]
    
    def truss_force_magnitudes(self, applied_force, applied_torque):
        return self._inverse_plucker @ -np.atleast_2d(np.hstack((applied_force, applied_torque))).T
    
    def applied(self, truss_force_magnitudes):
        forces_torques = -(self._plucker @ np.atleast_2d(truss_force_magnitudes).T)
        return forces_torques[:3, ...], forces_torques[3:, ...]
    
    def _init_trusses(self):
        # Create truss vectors
        top_angles = np.empty(6)
        top_angles[::2] = self.TRIANGLE - 0.5 * self.top_separation / self.top_radius
        top_angles[1::2] = self.TRIANGLE + 0.5 * self.top_separation / self.top_radius
        bottom_angles = np.empty(6)
        bottom_angles[::2] = self.TRIANGLE - np.deg2rad(60.0) - 0.5 * self.bottom_separation / self.bottom_radius
        bottom_angles[1::2] = self.TRIANGLE - np.deg2rad(60.0) + 0.5 * self.bottom_separation / self.bottom_radius
        top_joints = self._joint_positions(top_angles, self.top_radius, self.height)
        bottom_joints = self._joint_positions(bottom_angles, self.bottom_radius, 0.0)
        self.trusses = np.dstack((top_joints, np.roll(bottom_joints, -1, axis=1)))

        # Calculate unit truss forces and Plucker coordinates
        self._unit_forces = self.trusses[..., 0] - self.trusses[..., 1]
        self._unit_forces /= np.linalg.norm(self._unit_forces, axis=0)
        moments = np.cross(self.trusses[..., 0], self._unit_forces, axis=0)
        self._plucker = np.vstack((self._unit_forces, moments))
        self._inverse_plucker = np.linalg.inv(self._plucker)

    @staticmethod
    def _joint_positions(angles, radius, z):
        return np.vstack((radius * np.cos(angles),
                        radius * np.sin(angles),
                        np.ones_like(angles) * z))

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    plt.ion()
    haptick = Haptick(30e-3, 6e-3, 15e-3, 6e-3, 20e-3)
    applied_forces = np.array([[0.0, 0.0, -20e-3*9.81], [0.0, 0.0, 20e-3*9.81]])
    applied_torques = np.zeros((2, 3))
    print(haptick.truss_force_components(applied_forces, applied_torques))
    truss_force_magnitudes = haptick.truss_force_magnitudes(applied_forces, applied_torques)
    print(haptick.applied(truss_force_magnitudes.T)[0])
    print(haptick.applied(truss_force_magnitudes.T)[1])
    trusses = haptick.trusses
    ax = plt.axes(projection='3d')
    ax.scatter3D(*trusses[..., 0])
    ax.scatter3D(*trusses[..., 1])
    for truss in trusses.transpose((1, 0, 2)):
        ax.plot3D(*truss, 'k')
    ax.set_box_aspect((np.ptp(trusses[0, ...]), np.ptp(trusses[1, ...]), np.ptp(trusses[2, ...])))