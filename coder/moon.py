#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Демонстрация полёта ракеты к Луне и обратно.
Траектория – упрощённый Hohmann‑переход с одной луно‑орбитой.

Исправления:
1. Луна теперь стартует в том же направлении, что и апогея ракеты
   (добавлен фазовый сдвиг π). Это позволяет ракете «подлететь» к Луне.
2. Показаны реальные километры в метках: убрана лишняя деление на 1000.
3. Логика расчёта стартовой позиции остаётся прежней, но теперь
   анимация корректно отображает движение от Земли к Луне и обратно.
"""

import math
import sys
from typing import Tuple

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# --------------------------------------------------------------
# 1. Backend: интерактивный, если доступен – иначе Agg (GIF)
# --------------------------------------------------------------
try:
    matplotlib.use('TkAgg')          # или 'Qt5Agg', 'MacOSX'
except Exception as exc:
    print(f"⚠️  Не удалось активировать интерактивный backend: {exc}", file=sys.stderr)
    matplotlib.use('Agg')

# --------------------------------------------------------------
# 2. Константы
# --------------------------------------------------------------
MU_E = 398600.4418      # km³/s² – Земля
R_E  = 6378.137         # km – радиус Земли

MU_M = 4902.800066       # km³/s² – Луна
R_M  = 1737             # km – радиус Луны

R_L   = 384400          # km – среднее расстояние до Луны
r_LEO = R_E + 200       # km – высота LEO (≈ 200 км)

# Периодический полет: полукрупный радиус a_T = (r_LEO + r_L)/2
a_T   = (r_LEO + R_L) / 2
e     = (R_L - r_LEO) / (R_L + r_LEO)          # эксцентриситет

# Параметры анимации
FPS        = 20                 # кадра в секунду
T_TO_MIN   = 3 * 24 * 60       # ≈ 72 ч до Луны
T_BACK_MIN = T_TO_MIN           # возвращение за такой же срок
T_TOTAL_SEC= (T_TO_MIN + T_BACK_MIN) * 60

# Количество кадров ограничиваем разумно (~12 минут в кадр)
N_FRAMES   = 1200              # ~1‑минута анимации при FPS=20
times_s    = np.linspace(0, T_TOTAL_SEC, N_FRAMES)

# Масштаб: будем масштабировать только на этапе отрисовки
SCALE      = R_L / 400          # 400 ед. → Луна ≈ 400, Земля ≈ 16.0

# --------------------------------------------------------------
# 3. Вычисляем траекторию ракеты (векторная форма)
# --------------------------------------------------------------
def ellipse_pos(theta: float) -> Tuple[float, float]:
    """Положение по параметру θ на эллипсе."""
    x = a_T * (math.cos(theta) - e)
    y = a_T * math.sqrt(1 - e**2) * math.sin(theta)
    return x, y

def ellipse_speed(r: float) -> float:
    """Скорость по уравнению Кеплера."""
    return math.sqrt(MU_E * (2 / r - 1 / a_T))

# Списки координат ракеты
xs_km, ys_km, vs_mps = [], [], []

for t in times_s:
    # Фаза: outbound (0→T_TO_MIN), inbound (T_TO_MIN→T_TOTAL)
    if t <= T_TO_MIN * 60:
        theta = math.pi * t / (T_TO_MIN * 60)          # 0 → π
    else:
        theta = math.pi + math.pi * (t - T_TO_MIN*60) / (T_BACK_MIN * 60)   # π → 2π

    x, y = ellipse_pos(theta)
    r    = math.sqrt(x**2 + y**2)

    xs_km.append(x)
    ys_km.append(y)
    vs_mps.append(ellipse_speed(r) * 1000)               # m/s

xs_km = np.array(xs_km)
ys_km = np.array(ys_km)

# Луна: движение вокруг Земли (период ~27.3 дней)
moon_x_km, moon_y_km = [], []
MOON_OMEGA = 2*math.pi / (27.321582 * 24 * 3600)
for t in times_s:
    theta_moon = MOON_OMEGA * t + math.pi          # фазовый сдвиг: Луна стартует в том же направлении, что и апогея
    mx = R_L * math.cos(theta_moon)
    my = R_L * math.sin(theta_moon)
    moon_x_km.append(mx)
    moon_y_km.append(my)

# --------------------------------------------------------------
# 4. Определяем динамический предел оси
# --------------------------------------------------------------
max_coord = max(
    np.max(np.abs(xs_km)),
    np.max(np.abs(ys_km)),
    np.max(np.abs(moon_x_km)),
    np.max(np.abs(moon_y_km))
)
lim = (max_coord / SCALE) * 1.15   # небольшой «подрез» сверху

# --------------------------------------------------------------
# 5. Анимация (FuncAnimation + fallback to GIF)
# --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10,6))
ax.set_aspect('equal')
ax.set_xlim(-lim, lim)
ax.set_ylim(-lim, lim)

earth_circle = plt.Circle((0, 0), R_E / SCALE, color='k', alpha=0.4)
moon_artist  = plt.Circle((moon_x_km[0]/SCALE, moon_y_km[0]/SCALE),
                          R_M / SCALE, color='gray', alpha=0.6)

ax.add_artist(earth_circle); ax.add_artist(moon_artist)

# Треки
rocket_line, = ax.plot([], [], lw=1, color='b')
moon_track,  = ax.plot([], [], 'g--', lw=0.5)
rocket_point, = ax.plot([], [], 'o', ms=8, color='r')

# Метки
txt_time  = ax.text(0.02, 0.95, '', transform=ax.transAxes,
                    fontsize=10, verticalalignment='top')
txt_dist  = ax.text(0.02, 0.90, '', transform=ax.transAxes,
                    fontsize=10, verticalalignment='top')
txt_speed = ax.text(0.02, 0.85, '', transform=ax.transAxes,
                    fontsize=10, verticalalignment='top')

ax.legend([rocket_line, moon_track], ['Траектория ракеты', 'Путь Луны'])
plt.title('Ракета к Луне и обратно (Hohmann‑переход)')

def init():
    rocket_line.set_data([], [])
    moon_track.set_data([], [])
    rocket_point.set_data([], [])
    moon_artist.center = (moon_x_km[0]/SCALE, moon_y_km[0]/SCALE)
    txt_time.set_text('')
    txt_dist.set_text('')
    txt_speed.set_text('')
    return rocket_line, moon_track, rocket_point, moon_artist, txt_time, txt_dist, txt_speed

def update(frame):
    # Траектория ракеты
    rocket_line.set_data(xs_km[:frame+1]/SCALE, ys_km[:frame+1]/SCALE)
    rocket_point.set_data([xs_km[frame]/SCALE], [ys_km[frame]/SCALE])

    # Путь Луны (только до текущего момента)
    moon_track.set_data(np.array(moon_x_km)[:frame+1]/SCALE,
                        np.array(moon_y_km)[:frame+1]/SCALE)

    # Обновляем положение Луны
    moon_artist.center = (moon_x_km[frame]/SCALE, moon_y_km[frame]/SCALE)

    # Метки
    time_h   = times_s[frame] / 3600
    dist_km  = math.sqrt(xs_km[frame]**2 + ys_km[frame]**2)
    speed_kms= vs_mps[frame] / 1000

    txt_time.set_text(f'Время: {time_h:.1f} ч')
    txt_dist.set_text(f'Distance: {dist_km:.1f} км')
    txt_speed.set_text(f'Speed: {speed_kms:.2f} km/s')

    return rocket_line, moon_track, rocket_point, moon_artist, txt_time, txt_dist, txt_speed

interactive = matplotlib.get_backend() in ('TkAgg', 'Qt5Agg', 'MacOSX')
if interactive:
    ani = animation.FuncAnimation(fig, update, frames=N_FRAMES,
                                  init_func=init, blit=True,
                                  interval=1000/FPS)
    plt.show()
else:
    writer = animation.PillowWriter(fps=FPS, metadata=dict(artist='Demo'))
    ani = animation.FuncAnimation(fig, update, frames=N_FRAMES,
                                  init_func=init, blit=True,
                                  interval=1000/FPS)
    gif_path = 'rocket_to_moon_demo.gif'
    ani.save(gif_path, writer=writer)
    print(f'GIF сохранён: {gif_path}')
