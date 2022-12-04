from free_body import Haptick
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib import patheffects
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

COLOURS = plt.rcParams['axes.prop_cycle'].by_key()['color']
CM = LinearSegmentedColormap.from_list("Test", [COLOURS[0], [1.0, 1.0, 1.0], COLOURS[1]])

class Arrow3D(FancyArrowPatch):
    def __init__(self, xs, ys, zs, *args, **kwargs):
        super().__init__((0,0), (0,0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def do_3d_projection(self, renderer=None):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, self.axes.M)
        self.set_positions((xs[0],ys[0]),(xs[1],ys[1]))

        return np.min(zs)

haptick = Haptick(25e-3, np.deg2rad(25.0) *  25e-3, 25e-3, np.deg2rad(25.0) *  25e-3, 20e-3)
trusses = haptick.trusses

# Generate some force vectors.
t = np.linspace(0, 2 * np.pi, 100, endpoint=False)[1:]
force_varying = np.sin(t)
forces_varying_z = np.vstack((np.zeros_like(t), np.zeros_like(t), force_varying)).T
forces_varying_y = np.vstack((np.zeros_like(t), force_varying, np.zeros_like(t))).T
forces_varying_x = np.vstack((force_varying, np.zeros_like(t), np.zeros_like(t))).T
forces = np.vstack((forces_varying_x, forces_varying_y, forces_varying_z)) * 8e-3
forces += forces / np.linalg.norm(forces, axis=1)[:,np.newaxis] * 2e-3

# Generate some torque vectors.
torques = np.vstack((forces_varying_x, forces_varying_y, forces_varying_z)) * 8e-3
torques += torques / np.linalg.norm(torques, axis=1)[:,np.newaxis] * 0.5e-3

# Calculate forces on trusses for applied forces.
truss_forces_for_forces = haptick.truss_forces(forces, np.zeros_like(forces))[2]
max_truss_force_for_forces = np.abs(truss_forces_for_forces).max()

# Calculate forces on trusses for applied torques.
truss_forces_for_torques = haptick.truss_forces(np.zeros_like(torques), torques)[2]
max_truss_force_for_torques = np.abs(truss_forces_for_torques).max()

fig = plt.figure()
ax = plt.axes(projection='3d', computed_zorder=False)
ax.xaxis.set_ticklabels([])
ax.yaxis.set_ticklabels([])
ax.zaxis.set_ticklabels([])

truss_lines = []
for truss in trusses.transpose((1, 0, 2)):
    truss_lines.append(ax.plot(*truss,
                               color='w',
                               zorder=4,
                               linewidth=4.0,
                               solid_capstyle='round',
                               path_effects=[patheffects.Stroke(linewidth=5, foreground='k'), patheffects.Normal()])[0])

bottom_plane = Poly3DCollection([trusses[..., 1].T], alpha=0.5, linewidths=1, zorder=3)
bottom_plane.set_color('k')
bottom_plane.set_facecolor([0.5, 0.5, 0.5])
ax.add_collection3d(bottom_plane)

ax.scatter(*trusses[..., 1], c='gray', s=80, edgecolor='k', depthshade=False, zorder=5)

top_plane = Poly3DCollection([trusses[..., 0].T], alpha=0.5, linewidths=1, zorder=6)
top_plane.set_color('k')
top_plane.set_facecolor([0.5, 0.5, 0.5])
ax.add_collection3d(top_plane)

ax.scatter(*trusses[..., 0], c='gray', s=80, edgecolor='k', depthshade=False, zorder=7)

# Add a dummy points and set box aspect to ensure a nice 1:1:1 aspect ratio for the 3D plot.
ax.plot([-25e-3, 25e-3], [-25e-3, 25e-3], [0.0, 30e-3], linewidth=0.0)
ax.set_box_aspect((50e-3, 50e-3, 30e-3))

# Plot a little dot in the middle of the top platform.
ax.plot(0.0, 0.0, 20e-3, 'o', zorder=9, markeredgecolor='k', color=COLOURS[2])

# Create a force arrow.
base = np.array([0.0, 0.0, 20e-3])
force_arrow = Arrow3D(*np.vstack((base, base)).T, mutation_scale=20, arrowstyle='-|>', shrinkA=0, shrinkB=0, zorder=8, facecolor=COLOURS[2])
ax.add_artist(force_arrow)

# Create a torque ring.
torque_ring_upper = ax.plot(0.0, 0.0, 0.0, color='k', zorder=8, linewidth=1)[0]
torque_ring_lower = ax.plot(0.0, 0.0, 0.0, color='k', zorder=5.5, linewidth=1)[0]
torque_arrow = Arrow3D(*np.vstack((base, base)).T, mutation_scale=20, arrowstyle='-|>', shrinkA=0, shrinkB=0, zorder=8, facecolor=COLOURS[2])
ax.add_artist(torque_arrow)

# Set the camera angle and expand the plot a little.
ax.view_init(33, -32)
plt.tight_layout()

def update_force(num, force_arrow, truss_lines, applied_forces, truss_forces_z):
    applied_force = applied_forces[num % len(applied_forces)]
    truss_force_zs = truss_forces_z.T[num % len(applied_forces)]
    if applied_force[2] >= 0.0:
        force_arrow.set_zorder(8)
    else:
        force_arrow.set_zorder(5.5)
    force_arrow._verts3d = np.vstack((base, base + applied_force)).T
    for truss_line, truss_force_z in zip(truss_lines, truss_force_zs):
        truss_line.set_color(CM(0.5 * truss_force_z / max_truss_force_for_forces + 0.5))
    return [force_arrow] + truss_lines

def update_torque(num, torque_ring_lower, torque_ring_upper, torque_arrow,
                  truss_lines, applied_torques, truss_forces_z):
    applied_torque = applied_torques[num % len(applied_torques)]
    truss_force_zs = truss_forces_z.T[num % len(applied_torques)]
    torque_magnitude = np.linalg.norm(applied_torque)

    # Make the magnitude negative and reverse the vector to standardise where
    # the "ring" starts.
    if applied_torque[0] < 0.0 or applied_torque[1] > 0.0:
        applied_torque = -applied_torque
        torque_magnitude = -torque_magnitude

    # Calculate an coordinate system on a plane perpendicular to the applied
    # torque, assuming that the x vector falls on a plane parallel to the XY
    # world plane. Note, this falls apart for vectors aligned with the Z world
    # axis.
    x = np.cross([0, 0, 1], applied_torque)
    if np.linalg.norm(x) == 0.0:
        x = np.array([0., 1., 0.])
    y = np.cross(applied_torque, x)
    y /= np.linalg.norm(y)
    x /= np.linalg.norm(x)

    # Calculate a line on a small circle directly proportional to the torque
    # magnitude.
    t = np.arange(np.sign(torque_magnitude) * 0.075, 2 * np.pi * torque_magnitude / 0.0088, np.sign(torque_magnitude) * 0.075)
    points = np.atleast_2d(np.cos(t)).T @ np.atleast_2d(x) + np.atleast_2d(np.sin(t)).T @ np.atleast_2d(y)
    points *= 7e-3

    # Find where our arrow is.
    if points[-1, 2] >= 0.0:
        torque_arrow.set_zorder(8)
    else:
        torque_arrow.set_zorder(5.5)
    torque_arrow._verts3d = (np.vstack((points[0, :] if len(points) < 6 else points[-6, :], points[-1, :])) + base).T
    points = points[:-5, :]

    upper_points = points[points[:, 2] >= 0.0]
    lower_points = points[points[:, 2] < 0.0]

    if len(upper_points) == 0:
        a = 0

    torque_ring_upper.set_data_3d(*(upper_points + base).T)
    torque_ring_lower.set_data_3d(*(lower_points + base).T)

    for truss_line, truss_force_z in zip(truss_lines, truss_force_zs):
        truss_line.set_color(CM(0.5 * truss_force_z / max_truss_force_for_torques + 0.5))
    
    return [torque_ring_upper, torque_ring_lower, torque_arrow] + truss_lines

def update_angle(num):
    ax.view_init(33, -32 + 360 * (num / 300))
    return ()

anim = animation.FuncAnimation(fig, update_angle, frames=300, interval=50)
writer = animation.FFMpegWriter(fps=20, codec='webp', extra_args=["-loop", "0"])
anim.save('stewart-platform-geometry.webp', writer=writer)

#anim = animation.FuncAnimation(fig, update_force, fargs=(force_arrow, truss_lines, forces, truss_forces_for_forces),
#                               frames=len(forces), interval=50)
#anim.save('truss-force-from-applied-force.gif')

#fargs = (torque_ring_lower, torque_ring_upper, torque_arrow, truss_lines,
#         torques, truss_forces_for_torques)
#anim = animation.FuncAnimation(fig, update_torque, fargs=fargs,
#                               frames=len(torques), interval=50)
#anim.save('truss-force-from-applied-torque.gif')
#plt.show()