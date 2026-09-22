"""
Interaction Detector v3.1 — Punch, Kick, Tickle, Touch + Grab & Move
─────────────────────────────────────────────────────────────────────
Detects physical interactions AND grab/drag/release gestures.
"""
import time
from typing import List, Dict, Any
import numpy as np
from interaction.memories import MemoryManager


class InteractionDetector:
    """Detects interactions between live user and frozen memories."""

    def __init__(self):
        self._prev_landmarks = {}
        self._tickle_history = {}
        self._grab_cooldown = 0.0

    def update(self, memory_mgr: MemoryManager, hands: List[Dict[str, Any]], poses: List[Dict[str, Any]]):
        now = time.time()

        # ── GRAB / DRAG / RELEASE ──
        if memory_mgr.grabbed_memory:
            # Currently grabbing — check if still holding fist
            still_fist = False
            for hand in hands:
                gesture = hand.get("gesture", "")
                if gesture == "Closed_Fist":
                    # Drag the memory
                    px, py = hand["palm_center"]
                    memory_mgr.drag(px, py)
                    still_fist = True
                    break
            if not still_fist:
                # Released — drop the memory
                memory_mgr.release()
                self._grab_cooldown = now + 1.0
        else:
            # Not grabbing — check for grab initiation
            if now > self._grab_cooldown:
                for hand in hands:
                    gesture = hand.get("gesture", "")
                    if gesture == "Closed_Fist" and hand.get("gesture_confidence", 0) > 0.6:
                        px, py = hand["palm_center"]
                        if memory_mgr.try_grab(px, py):
                            break

        # ── INTERACTION DETECTION (skip if grabbing) ──
        if memory_mgr.grabbed_memory:
            return

        active_points = []

        for i, hand in enumerate(hands):
            key = f"hand_{i}"
            px, py = hand["index_tip"]
            palm_x, palm_y = hand["palm_center"]

            vx, vy, speed = 0, 0, 0
            if key in self._prev_landmarks:
                ox, oy, ot = self._prev_landmarks[key]
                dt = now - ot
                if dt > 0.001:
                    vx = (px - ox) / dt
                    vy = (py - oy) / dt
                    speed = np.hypot(vx, vy)
            self._prev_landmarks[key] = (px, py, now)

            active_points.append({
                "type": "hand", "x": px, "y": py,
                "palm_x": palm_x, "palm_y": palm_y,
                "vx": vx, "vy": vy, "speed": speed,
                "gesture": hand.get("gesture", ""), "key": key,
            })

        for i, person in enumerate(poses):
            keypts = person.get("keypoints", {})
            for foot_name in ["left_ankle", "right_ankle"]:
                if foot_name in keypts:
                    fx, fy = keypts[foot_name]
                    key = f"foot_{i}_{foot_name}"
                    vx, vy, speed = 0, 0, 0
                    if key in self._prev_landmarks:
                        ox, oy, ot = self._prev_landmarks[key]
                        dt = now - ot
                        if dt > 0.001:
                            vx = (fx - ox) / dt
                            vy = (fy - oy) / dt
                            speed = np.hypot(vx, vy)
                    self._prev_landmarks[key] = (fx, fy, now)
                    active_points.append({
                        "type": "foot", "x": fx, "y": fy,
                        "vx": vx, "vy": vy, "speed": speed, "key": key,
                    })

        for pt in active_points:
            for memory in memory_mgr.memories:
                if memory.is_grabbed:
                    continue
                if memory.reaction_label and (now - memory.reaction_time) < 0.5:
                    continue

                dist = np.hypot(pt["x"] - memory.center_x, pt["y"] - memory.center_y)
                near_bbox = dist < max(memory.width, memory.height) * 0.6
                if not near_bbox:
                    continue

                in_bbox_x = memory.origin_x <= pt["x"] <= memory.origin_x + memory.width
                in_bbox_y = memory.origin_y <= pt["y"] <= memory.origin_y + memory.height
                dir_x = 1.0 if pt["x"] < memory.center_x else -1.0

                # PUNCH
                if pt["type"] == "hand" and pt["speed"] > 400 and dist < 150:
                    memory.apply_reaction("PUNCH!", direction_x=dir_x)
                    continue
                # KICK
                if pt["type"] == "foot" and pt["speed"] > 350 and dist < 150:
                    memory.apply_reaction("KICK!", direction_x=dir_x)
                    continue
                # TICKLE
                if pt["type"] == "hand" and dist < 120 and pt["speed"] < 300:
                    mid = memory.memory_id
                    if mid not in self._tickle_history:
                        self._tickle_history[mid] = []
                    self._tickle_history[mid].append((now, pt["x"]))
                    self._tickle_history[mid] = [(t, x) for t, x in self._tickle_history[mid] if now - t < 1.5]
                    hist = self._tickle_history[mid]
                    if len(hist) >= 6:
                        changes = sum(1 for j in range(2, len(hist))
                                      if (hist[j][1] - hist[j-1][1]) * (hist[j-1][1] - hist[j-2][1]) < 0)
                        if changes >= 3:
                            memory.apply_reaction("TICKLE!", direction_x=dir_x)
                            self._tickle_history[mid] = []
                            continue
                # TOUCH
                if pt["type"] == "hand" and pt["speed"] < 150 and dist < 100 and in_bbox_x and in_bbox_y:
                    memory.apply_reaction("TOUCH", direction_x=dir_x)

        # Clean stale entries
        stale = [k for k, (_, _, t) in self._prev_landmarks.items() if now - t > 2.0]
        for k in stale:
            del self._prev_landmarks[k]
