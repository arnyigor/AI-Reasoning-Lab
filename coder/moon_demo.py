#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Realistic Earth–Moon Hohmann transfer simulation.
Author: Distinguished Software Architect
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# ------------------------------------------------------------------
# 1. Constants (SI)
# ------------------------------------------------------------------
G          = 6.67430e-11           # m³·kg⁻¹·s⁻²
M_EARTH    = 5.972e24              # kg
M_MOON     = 7.342e22              # kg
R_EARTH    = 6.371e6               # m
DIST_EARTH_MOON = 384400e3          # m (center‑to‑center)

# ------------------------------------------------------------------
# 2. Helper functions
# ------------------------------------------------------------------
def gravitational_acceleration(pos, masses=[M_EARTH, M_MOON], bodies=[[0, 0], [DIST_EARTH_MOON, 0]]):
    """
    Vector acceleration of a test mass at *pos* due to point masses.
    Uses the stable form: a = -G m r / |r|³
    """
    acc = np.zeros(2)
    for mass, body in zip(masses, bodies):
        r_vec   = pos - body               # vector from body to spacecraft
        r_sq    = float(np.dot(r_vec, r_vec))
        if r_sq < 1e-12:                   # avoid singularity
            continue
        acc += -G * mass / (r_sq ** 1.5) * r_vec
    return acc

def dynamics(t, state):
    """
    Right‑hand side for the ODE solver.
    state = [x, y, vx, vy]
    Returns derivative: [vx, vy, ax, ay]
    """
    pos   = state[:2]
    vel   = state[2:]
    acc   = gravitational_acceleration(pos)
    return np.concatenate([vel, acc])

# ------------------------------------------------------------------
# 3. Hohmann transfer parameters
# ------------------------------------------------------------------
r_leo          = R_EARTH + 300e3                     # 300 km altitude
v_circ         = np.sqrt(G * M_EARTH / r_leo)        # circular LEO speed

a_transfer     = (r_leo + DIST_EARTH_MOON) / 2.0      # semi‑major axis of transfer ellipse
v_peri_hohmann= np.sqrt(G * M_EARTH * (2/r_leo - 1/a_transfer))

delta_v_tli    = v_peri_hohmann - v_circ

print(f"🚀 Launch from LEO at r={r_leo/1e6:.3f} Mm")
print(f"   Circular speed: {v_circ/1e3:.4f} km/s")
print(f"   Hohmann periapsis speed: {v_peri_hohmann/1e3:.4f} km/s")
print(f"   Δv TLI: +{delta_v_tli/1e3:.4f} km/s → Total = {v_peri_hohmann/1e3:.4f} km/s")

# ------------------------------------------------------------------
# 4. Initial state – tangential launch towards the Moon
# ------------------------------------------------------------------
# Position at perigee (x positive, y=0)
initial_pos   = np.array([r_leo, 0.0])
# Tangential velocity (+y) – launches prograde towards +x direction
initial_vel   = np.array([0.0, v_peri_hohmann])

state0       = np.concatenate([initial_pos, initial_vel])   # [x, y, vx, vy]

# ------------------------------------------------------------------
# 5. Integration
# ------------------------------------------------------------------
SIM_DURATION = 12 * 24 * 3600          # 12 days in seconds

# Use SciPy's RK45 (adaptive) – highly accurate and stable.
sol = solve_ivp(
    fun        = dynamics,
    t_span     = (0, SIM_DURATION),
    y0         = state0,
    method     = 'RK45',
    rtol       = 1e-9,
    atol       = 1e-12,
    max_step   = 300.0                 # keep step ≤ 5 min for consistency with original script
)

# Extract trajectory
x, y, vx, vy = sol.y

# ------------------------------------------------------------------
# 6. Diagnostics – closest approach to the Moon
# ------------------------------------------------------------------
moon_pos = np.array([DIST_EARTH_MOON, 0.0])
dist_to_moon = np.hypot(x - moon_pos[0], y - moon_pos[1])

idx_closest   = int(np.argmin(dist_to_moon))
t_closest     = sol.t[idx_closest]
min_dist      = dist_to_moon[idx_closest]

print(f"\n✅ Closest approach to Moon at t={t_closest/3600:.1f} h ({t_closest/(24*3600):.2f} d)")
print(f"   Distance: {min_dist/1e3:.1f} km")

if min_dist < 5_000e3:
    print("🎉 SUCCESS: Spacecraft reached lunar vicinity!")
else:
    raise RuntimeError("Trajectory did not reach the Moon’s orbit – check launch direction or Δv.")

# ------------------------------------------------------------------
# 7. Plot
# ------------------------------------------------------------------
plt.figure(figsize=(14, 10))
plt.plot(x/1e6, y/1e6, 'b-', linewidth=2.5, label='Spacecraft Trajectory', zorder=3)

# Earth & Moon markers
plt.scatter(0, 0, color='y', s=800, edgecolor='orange',
            marker='o', label='Earth', zorder=4)
plt.scatter(DIST_EARTH_MOON/1e6, 0, color='m', s=200,
            edgecolor='purple', marker='o', label='Moon (fixed)', zorder=4)

# Closest approach marker
plt.scatter(x[idx_closest]/1e6, y[idx_closest]/1e6,
            facecolors='none', edgecolors='g',
            linewidth=2.5, s=300, label='Closest Approach', zorder=5)

# LEO circle for reference
theta = np.linspace(0, 2*np.pi, 200)
leo_x = r_leo * np.cos(theta) / 1e6
leo_y = r_leo * np.sin(theta) / 1e6
plt.plot(leo_x, leo_y, 'r--', linewidth=1.5,
         alpha=0.8, label='LEO (300 km)')

# Velocity arrows every 200 steps
for i in range(0, len(x)-1, 200):
    dx = x[i+1] - x[i]
    dy = y[i+1] - y[i]
    plt.arrow(x[i]/1e6, y[i]/1e6,
              dx/1e6*0.25, dy/1e6*0.25,
              head_width=0.18, head_length=0.25,
              fc='blue', ec='blue',
              alpha=0.4, linewidth=0.8)

plt.xlabel('X (Mm)')
plt.ylabel('Y (Mm)')
plt.title(
    '✅ Realistic Earth–Moon Transfer\n(Launch tangentially with correct Δv)',
    fontsize=14, fontweight='bold')
plt.legend(loc='upper right', fontsize=10)
plt.grid(True, linestyle='--', alpha=0.6)
plt.axis('equal')

# Font fallback
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']
plt.tight_layout()
plt.show()
