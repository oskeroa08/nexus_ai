"""Премиум AI-сфера — визуализатор голосового ассистента."""

import math
import random

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from gui.theme import COLOR_CORE, COLOR_GLOW, COLOR_PARTICLE, VISUALIZER_MIN_SIZE

FRAME_MS = 16
RING_COUNT = 6
PARTICLE_COUNT = 24
WAVE_COUNT = 3


class _Particle:
    """Одна световая частица на орбите."""

    __slots__ = ("angle", "radius", "speed", "size", "alpha")

    def __init__(self, angle: float, radius: float, speed: float, size: float, alpha: float):
        self.angle = angle
        self.radius = radius
        self.speed = speed
        self.size = size
        self.alpha = alpha


class AudioVisualizer(QWidget):
    """AI-сфера с кольцами, частицами и реакцией на аудио."""

    STATE_IDLE = "idle"
    STATE_LISTENING = "listening"
    STATE_SPEAKING = "speaking"
    STATE_PROCESSING = "processing"
    STATE_WAKE = "wake"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(VISUALIZER_MIN_SIZE, VISUALIZER_MIN_SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        self._state = self.STATE_IDLE
        self._audio_level = 0.0
        self._time = 0.0
        self._breath = 0.0
        self._ring_angles = [0.0] * RING_COUNT
        self._wave_phases = [0.0] * WAVE_COUNT
        self._particles = self._init_particles()

        self._color_glow = QColor(COLOR_GLOW)
        self._color_core = QColor(COLOR_CORE)
        self._color_particle = QColor(COLOR_PARTICLE)

        self._breath_anim = QVariantAnimation(self)
        self._breath_anim.setStartValue(0.0)
        self._breath_anim.setEndValue(1.0)
        self._breath_anim.setDuration(3200)
        self._breath_anim.setLoopCount(-1)
        self._breath_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._breath_anim.valueChanged.connect(self._on_breath_changed)
        self._breath_anim.start()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(FRAME_MS)

    def _init_particles(self) -> list[_Particle]:
        return [
            _Particle(
                angle=random.uniform(0, math.tau),
                radius=random.uniform(0.55, 1.15),
                speed=random.uniform(0.008, 0.025),
                size=random.uniform(1.5, 3.5),
                alpha=random.uniform(0.3, 0.9),
            )
            for _ in range(PARTICLE_COUNT)
        ]

    def _on_breath_changed(self, value: float) -> None:
        self._breath = float(value)

    def set_state(self, state: str) -> None:
        self._state = state
        if state == self.STATE_WAKE:
            self._color_glow = QColor("#FFD166")
            self._color_core = QColor("#FFD166")
            self._color_particle = QColor("#FFE599")
        else:
            self._color_glow = QColor(COLOR_GLOW)
            self._color_core = QColor(COLOR_CORE)
            self._color_particle = QColor(COLOR_PARTICLE)
        self._update_breath_speed()
        self.update()

    def set_audio_level(self, level: float) -> None:
        self._audio_level = max(0.0, min(1.0, level))

    def _update_breath_speed(self) -> None:
        speeds = {
            self.STATE_IDLE: 3200,
            self.STATE_LISTENING: 2200,
            self.STATE_SPEAKING: 1800,
            self.STATE_PROCESSING: 1400,
            self.STATE_WAKE: 1200,
        }
        self._breath_anim.stop()
        self._breath_anim.setDuration(speeds.get(self._state, 3200))
        self._breath_anim.start()

    def _state_multiplier(self) -> dict[str, float]:
        return {
            self.STATE_IDLE: {"scale": 1.0, "ring_speed": 1.0, "glow": 0.45, "core": 0.6},
            self.STATE_LISTENING: {"scale": 1.08, "ring_speed": 1.6, "glow": 0.7, "core": 0.85},
            self.STATE_SPEAKING: {"scale": 1.12, "ring_speed": 2.0, "glow": 0.85, "core": 1.0},
            self.STATE_PROCESSING: {"scale": 1.05, "ring_speed": 2.8, "glow": 1.0, "core": 0.95},
            self.STATE_WAKE: {"scale": 1.15, "ring_speed": 3.2, "glow": 1.0, "core": 1.0},
        }.get(self._state, {"scale": 1.0, "ring_speed": 1.0, "glow": 0.5, "core": 0.6})

    def _tick(self) -> None:
        mult = self._state_multiplier()
        dt = FRAME_MS / 1000.0
        self._time += dt

        for i in range(RING_COUNT):
            direction = 1 if i % 2 == 0 else -1
            speed = (0.4 + i * 0.15) * mult["ring_speed"] * direction
            self._ring_angles[i] = (self._ring_angles[i] + speed * dt) % math.tau

        for i in range(WAVE_COUNT):
            self._wave_phases[i] += (0.6 + i * 0.2) * mult["ring_speed"] * dt

        for p in self._particles:
            p.angle = (p.angle + p.speed * mult["ring_speed"]) % math.tau

        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base = min(w, h) * 0.18
        mult = self._state_multiplier()

        breath_wave = math.sin(self._breath * math.pi) * 0.5 + 0.5
        level_boost = self._audio_level * base * 0.35
        core_radius = base * mult["scale"] + breath_wave * 6 + level_boost

        self._draw_ambient_glow(painter, cx, cy, core_radius, mult["glow"])
        self._draw_radial_waves(painter, cx, cy, base, mult)
        self._draw_rings(painter, cx, cy, base, core_radius, mult)
        self._draw_particles(painter, cx, cy, base, mult)
        self._draw_core(painter, cx, cy, core_radius, mult)
        painter.end()

    def _draw_ambient_glow(self, painter: QPainter, cx: float, cy: float, radius: float, glow: float) -> None:
        gradient = QRadialGradient(cx, cy, radius * 2.8)
        color = QColor(self._color_glow)
        color.setAlpha(int(35 * glow))
        gradient.setColorAt(0.0, color)
        color.setAlpha(0)
        gradient.setColorAt(1.0, color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(QRectF(cx - radius * 2.8, cy - radius * 2.8, radius * 5.6, radius * 5.6))

    def _draw_radial_waves(self, painter: QPainter, cx: float, cy: float, base: float, mult: dict) -> None:
        for i, phase in enumerate(self._wave_phases):
            progress = (math.sin(phase) + 1) / 2
            wave_r = base * (1.4 + i * 0.22) + progress * 18 + self._audio_level * 24
            alpha = int((50 - i * 12) * mult["glow"] * (0.5 + progress * 0.5))
            color = QColor(self._color_glow)
            color.setAlpha(max(0, alpha))
            pen = QPen(color, 1.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(cx - wave_r, cy - wave_r, wave_r * 2, wave_r * 2))

    def _draw_rings(
        self, painter: QPainter, cx: float, cy: float, base: float, core_radius: float, mult: dict
    ) -> None:
        for i in range(RING_COUNT):
            ring_base = core_radius + 16 + i * 14
            tilt = math.sin(self._ring_angles[i]) * 6
            ring_r = ring_base + tilt + self._audio_level * 12

            alpha = int((90 - i * 10) * mult["glow"])
            color = QColor(self._color_glow)
            color.setAlpha(max(10, alpha))

            pen = QPen(color, max(0.8, 2.2 - i * 0.2))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            squeeze = 0.72 + abs(math.cos(self._ring_angles[i])) * 0.28
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(math.degrees(self._ring_angles[i] * 0.3))
            painter.scale(1.0, squeeze)
            painter.drawEllipse(QRectF(-ring_r, -ring_r, ring_r * 2, ring_r * 2))
            painter.restore()

    def _draw_particles(self, painter: QPainter, cx: float, cy: float, base: float, mult: dict) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self._particles:
            dist = base * p.radius + self._audio_level * 20
            px = cx + math.cos(p.angle) * dist
            py = cy + math.sin(p.angle) * dist * 0.85
            color = QColor(self._color_particle)
            color.setAlpha(int(180 * p.alpha * mult["glow"]))
            painter.setBrush(color)
            painter.drawEllipse(QRectF(px - p.size, py - p.size, p.size * 2, p.size * 2))

    def _draw_core(self, painter: QPainter, cx: float, cy: float, radius: float, mult: dict) -> None:
        gradient = QRadialGradient(cx, cy, radius)
        center = QColor(self._color_core)
        center.setAlpha(int(220 * mult["core"]))
        mid = QColor(self._color_core)
        mid.setAlpha(int(120 * mult["core"]))
        edge = QColor(self._color_core)
        edge.setAlpha(0)
        gradient.setColorAt(0.0, center)
        gradient.setColorAt(0.55, mid)
        gradient.setColorAt(1.0, edge)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

        inner_r = radius * 0.35
        inner_grad = QRadialGradient(cx, cy, inner_r)
        white = QColor(255, 255, 255)
        white.setAlpha(int(200 * mult["core"]))
        inner_grad.setColorAt(0.0, white)
        inner_grad.setColorAt(1.0, QColor(87, 232, 255, 0))
        painter.setBrush(inner_grad)
        painter.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))
