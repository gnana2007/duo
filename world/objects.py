"""
Interactive Virtual Objects & Physics Engine
Simulates dynamic floating objects (energy orbs, bubbles) that respond to touching,
punching, kicking, waving, and pinching.
"""
import time
from typing import List, Dict, Any
import numpy as np
import cv2
from config import settings


class InteractiveObject:
    def __init__(self, x: float, y: float, radius: int, color_bgr: tuple, name="Orb"):
        self.pos = np.array([float(x), float(y)])
        self.vel = np.array([np.random.uniform(-1.5, 1.5), np.random.uniform(-1.0, 1.0)])
        self.radius = radius
        self.base_radius = radius
        self.color = color_bgr
        self.name = name
        self.is_grabbed = False
        self.grabbed_by = None
        self.burst_particles = []

    def update(self, bounds_w: int, bounds_h: int):
        # Update particles if bursting/sparking
        alive_p = []
        for p in self.burst_particles:
            p["pos"] += p["vel"]
            p["life"] -= 0.05
            if p["life"] > 0:
                alive_p.append(p)
        self.burst_particles = alive_p

        if self.is_grabbed:
            self.vel *= 0.2
            return

        # Float dynamics & slight drag
        self.pos += self.vel
        self.vel *= 0.985
        # Soft buoyancy force towards vertical center
        self.vel[1] += np.sin(time.time() * 2.0 + self.pos[0] * 0.01) * 0.15

        # Screen boundary elastic collision
        margin = self.radius + 10
        if self.pos[0] < margin:
            self.pos[0] = margin
            self.vel[0] = abs(self.vel[0]) * 0.85
        elif self.pos[0] > bounds_w - margin:
            self.pos[0] = bounds_w - margin
            self.vel[0] = -abs(self.vel[0]) * 0.85

        if self.pos[1] < margin:
            self.pos[1] = margin
            self.vel[1] = abs(self.vel[1]) * 0.85
        elif self.pos[1] > bounds_h - margin:
            self.pos[1] = bounds_h - margin
            self.vel[1] = -abs(self.vel[1]) * 0.85

    def check_interaction(self, hands: List[Dict[str, Any]], poses: List[Dict[str, Any]]):
        # 1. Hand Interactions (Touch, Pinch, Punch)
        for hand in hands:
            palm = np.array(hand["palm_center"], dtype=np.float32)
            index = np.array(hand["index_tip"], dtype=np.float32)
            dist_palm = np.linalg.norm(self.pos - palm)
            dist_index = np.linalg.norm(self.pos - index)

            # Pinch / Grab
            if hand.get("is_pinching", False) and dist_index < self.radius + 25:
                self.is_grabbed = True
                self.pos = index.copy()
                self.radius = int(self.base_radius * 1.25)
                return

            # Punch (Closed Fist with high proximity)
            if hand.get("gesture") == "Closed_Fist" and dist_palm < self.radius + 40:
                # Strong punch impulse
                punch_dir = self.pos - palm
                norm = np.linalg.norm(punch_dir)
                if norm > 0:
                    punch_dir /= norm
                else:
                    punch_dir = np.array([0.0, -1.0])
                self.vel = punch_dir * 18.0
                self._spawn_sparks(15)
                self.is_grabbed = False
                continue

            # Gentle Touch / Pointing
            if dist_index < self.radius + 15:
                touch_dir = self.pos - index
                norm = np.linalg.norm(touch_dir)
                if norm > 0:
                    touch_dir /= norm
                    self.vel += touch_dir * 4.5
                self._spawn_sparks(4)

        if not any(h.get("is_pinching", False) for h in hands):
            self.is_grabbed = False
            self.radius = self.base_radius

        # 2. Pose Interactions (Kicking / Body collision)
        for person in poses:
            keypts = person.get("keypoints", {})
            for joint_name in ["left_ankle", "right_ankle", "left_wrist", "right_wrist"]:
                if joint_name in keypts:
                    pt = np.array(keypts[joint_name], dtype=np.float32)
                    dist = np.linalg.norm(self.pos - pt)
                    if dist < self.radius + 30:
                        kick_dir = self.pos - pt
                        norm = np.linalg.norm(kick_dir)
                        if norm > 0:
                            kick_dir /= norm
                            self.vel += kick_dir * 10.0
                            self._spawn_sparks(8)

    def _spawn_sparks(self, count: int):
        for _ in range(count):
            angle = np.random.uniform(0, 2 * np.pi)
            speed = np.random.uniform(3, 8)
            self.burst_particles.append({
                "pos": self.pos.copy(),
                "vel": np.array([np.cos(angle) * speed, np.sin(angle) * speed]),
                "life": 1.0,
                "color": (np.random.randint(180, 255), 255, np.random.randint(100, 255))
            })

    def draw(self, canvas: np.ndarray):
        px, py = int(self.pos[0]), int(self.pos[1])
        h, w = canvas.shape[:2]

        # Draw spark particles
        for p in self.burst_particles:
            spx, spy = int(p["pos"][0]), int(p["pos"][1])
            if 0 <= spx < w and 0 <= spy < h:
                cv2.circle(canvas, (spx, spy), max(1, int(3 * p["life"])), p["color"], -1)

        if 0 <= px < w and 0 <= py < h:
            # Multi-layer glassmorphic bubble
            overlay = canvas.copy()
            # Outer halo
            cv2.circle(overlay, (px, py), self.radius + 8, self.color, 2)
            # Translucent core
            cv2.circle(overlay, (px, py), self.radius, self.color, -1)
            cv2.addWeighted(overlay, 0.40, canvas, 0.60, 0, canvas)

            # Specular glossy highlight
            hx, hy = px - int(self.radius * 0.35), py - int(self.radius * 0.35)
            cv2.circle(canvas, (hx, hy), max(2, int(self.radius * 0.22)), (255, 255, 255), -1)


class ObjectManager:
    def __init__(self, bounds_w=settings.CAPTURE_WIDTH, bounds_h=settings.CAPTURE_HEIGHT):
        self.bounds_w = bounds_w
        self.bounds_h = bounds_h
        self.objects: List[InteractiveObject] = []
        self._init_default_objects()

    def _init_default_objects(self):
        # 3 initial dynamic floating energy orbs
        self.objects = [
            InteractiveObject(260, 320, 38, (255, 180, 40), "Cyan Sphere"),
            InteractiveObject(640, 280, 44, (50, 230, 255), "Gold Orb"),
            InteractiveObject(1020, 340, 36, (240, 60, 220), "Plasma Bubble")
        ]

    def update_and_draw(self, canvas: np.ndarray, hands: list, poses: list):
        for obj in self.objects:
            obj.check_interaction(hands, poses)
            obj.update(self.bounds_w, self.bounds_h)
            obj.draw(canvas)
