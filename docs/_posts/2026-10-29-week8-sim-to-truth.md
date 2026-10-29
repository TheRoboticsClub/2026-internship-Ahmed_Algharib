---
title: "Week 8: Closing the Sim-to-Truth Gap — Physics, Cartesian Paths, and Native Grasp Welds"
date: 2026-10-29 09:00:00 +0300
categories: [Internship]
tags: [ros2, moveit2, mujoco, cplusplus, robotics, imitation-learning]
description: "Replacing joint-space fallbacks with Cartesian trajectories, fixing MuJoCo collision physics, diagnosing an RViz/MuJoCo temporal weld mismatch, and writing a custom C++ ros2_control plugin to enforce truth at the physics step."
---

# Week 8 — Closing the Sim-to-Truth Gap: Physics, Cartesian Paths, and Native Grasp Welds
### UR5e + MuJoCo + MoveIt2 → Physically consistent imitation learning

**Author:** Ahmed  
**Internship Week:** 8  
**Project:** Digital-twin pick-and-place for scalable imitation learning (MobRT-inspired)  
**Stack:** ROS 2 (Jazzy), MoveIt2, MuJoCo (`mujoco_ros2_control`), C++, Python, HDF5

---

## TL;DR

This week was dedicated to closing the gap between what MoveIt *planned* and what MuJoCo *actually executed*. We transitioned from joint-space fallbacks to strict Cartesian trajectories, discovered that our simulation lacked actual collision geometry (objects were just visual ghosts), and diagnosed a subtle temporal mismatch between RViz and MuJoCo's grasp welds. The culmination was `vibe_version`, an isolated ROS 2 package containing a custom C++ MuJoCo plugin that enforces grasp attachments natively inside the physics step, guaranteeing that the data we record for imitation learning is physically truthful.

---

## 1. Shortening and Stabilizing the Motion Plan

The original motion planner relied on the "first IK answer" it found, which often resulted in violent elbow flips between episodes. Furthermore, transfers relied on fixed highway heights and joint-space arcs. 

**What changed:**
- **Nearest-Seed IK:** Replaced the default solver with 6 predefined seeds + current pose. We score every solution by joint-distance to the live joints and keep the closest one.
- **Cartesian Trajectories:** Moved approach, grasp, and retreat to collision-checked Cartesian trajectories using `/compute_cartesian_path` (`max_step=0.01`).
- **Unified Transfer:** Merged lift + transfer + place into one continuous Cartesian trajectory (no intermediate stops/replans).
- **Adaptive Corridor:** Replaced the fixed `Z_TRAVEL=1.1` with an adaptive corridor height computed from live obstacle tops + carried half-height + clearance.
- **Strict Path Validation:** The runner now rejects incomplete Cartesian paths (`fraction < 1.0`) instead of silently falling back to longer joint-space arcs.
- **Quality Metrics:** Added `path_length`, `joint_movement`, and `duration_s` to the HDF5 files for later curation.

**Proof:** Logs show `fraction=1.000` on every segment; transfers measure 1.09–1.21 m; retreat ≈0.096 m.

![The Shortened Path](/assets/img/The%20Shortened%20Path.png)
*Fig 1: Top-down view of a recorded transfer path. Lift → above-bin → drop executed as a single, straight Cartesian trajectory (fraction = 1.000), eliminating joint-space detours.*

---

## 2. Making the Scene Physically Real

While testing, I noticed the end-effector was passing straight through objects, and objects weren't resting reliably in the bins. 

**Diagnosis:** The MuJoCo bodies had *visual-only* geometry. There were no collision geoms and no contact pairing. 

**Fix:** Added physical collision geometry with explicit contact masks:
- Objects: `contype=2 conaffinity=3`
- Bins: `contype=4 conaffinity=2`
- Collidable table and floor.
- Bin walls converted to real box geoms so placed objects actually rest inside.

**Result:** Contacts became real, grasp proximity became physically meaningful, and placements rest correctly. The MuJoCo viewer "Contacts" counter now goes non-zero during interaction.

![The Physical Collision Mesh](/assets/img/The%20Physical%20Collision%20Mesh.png)
*Fig 2: Physical collision verification. The MuJoCo viewer shows the gripper in contact with the yellow box. The "Contacts" counter displays >0 contacts, proving that the physics engine is calculating real forces.*

---

## 3. The RViz-vs-MuJoCo Weld Mismatch, Measured

RViz showed a perfect attach (MoveIt `attach_held_object` / `detach_held_object`, ghost cleanup, allowed-collision entries). But MuJoCo still showed a rubber-band lag during the carry phase. We stopped guessing and measured it.

**Measurement Tool (`calculate_delay.py`):**
Calculated per-axis spatial offset (mean EE−obj) and temporal lag via velocity cross-shift search (0–10 steps).

**Baseline Measurement:**
- X offset: ≈ −0.98 cm
- Y offset: ≈ −0.53 cm
- Temporal lag: 0–1 recorded steps.

**Four Attempts to Kill the Delay:**

| Attempt | Change | Outcome |
|---|---|---|
| 1 | Ultra-stiff weld | Box jittered violently |
| 2 | Implicitfast integrator | Stable base, drift remained |
| 3 | Balanced stiffness | Smooth carry, ~0.6 cm drift |
| 4 | Predictive compensation | 0 ms lag, but high overshoot |

**Conclusion:** After researching MuJoCo grasp mechanisms (adhesion actuators, runtime `eq_active` weld toggling, `condim=6` friction locks, kinematic `qpos` overwrites), it became clear that the fix must live *inside the physics step itself*.

---

## 4. Final Resolution: The Isolated `vibe_version` Package

**Decision:** Stop patching the shared stack. Put the grasp truth in a new isolated package; classical task and shared robot/MuJoCo packages untouched.

**Implementation:**
- **`grasp_attachment_plugin.cpp` (C++ MuJoCo ros2_control plugin):** Proximity gate ≤3 cm checked on the physics thread. Switches the inactive constraint to a body-based weld in `pre_step`. Captures EEF-to-object relative pose at activation (no snap). Release happens on physics step. Exposes `/vibe_version/set_grasp` service and status topic.
- **`relative_pick_place.py`:** Live box/target poses, seeded bounded randomization with dead-zone guard, candidate-pose checks, single-trajectory Cartesian transfer, placement verification.
- **`demonstration_recorder.py`:** HDF5 with existing obs/action schema + timestamps, success/goal metadata, path metrics. Failures are discarded.
- **Testing:** `test_dataset.py` (14 tests pass).

**Proof:** 
Running `ros2 run vibe_version pick_place_relative --object yellow_box --episodes 10 --seed 27` results in **10/10 success**, `fraction=1.000` everywhere, and placements `[0.135–0.136, 0.949–0.950, 0.751]` m (≤7 mm from bin centre).

![The Successful Weld](/assets/img/The%20Successful%20Weld.png)
*Fig 3: Grasp verification. MuJoCo (left) shows the box rigidly locked to the gripper during fast transfer. RViz (right) shows the attached collision object perfectly aligned. The native C++ plugin activates the weld inside the physics step, achieving zero lag.*

---

## 5. The Grasp Weld Configuration

The weld constraint in `scene.xml` starts inactive and is controlled by the C++ plugin at runtime:

```xml
<equality>
  <!-- Starts inactive; plugin flips eq_active to 1 inside the physics step -->
  <weld site1="eef_site" site2="grasp_yellow_box" active="false" 
        solref="0.0015 1" solimp="0.97 0.99 0.001 0.5 2"/>
  <weld site1="eef_site" site2="grasp_red_box" active="false" 
        solref="0.0015 1" solimp="0.97 0.99 0.001 0.5 2"/>
  <weld site1="eef_site" site2="grasp_blue_ball" active="false" 
        solref="0.0015 1" solimp="0.97 0.99 0.001 0.5 2"/>
  <weld site1="eef_site" site2="grasp_green_cylinder" active="false" 
        solref="0.0015 1" solimp="0.97 0.99 0.001 0.5 2"/>
</equality>
 
---

## 6. Current Status

- ✅ Package builds; 14/14 tests pass.
- ✅ Pick-and-place motion verified live (10/10, seeded randomization).
- ✅ Grasp weld verified: rigid carry, zero lag, gravity release.
- ✅ Physical collision geometry verified: real contacts, stable placements.
- ✅ Motion plan verified: straight Cartesian paths, adaptive height, no fallback arcs.
- ⏳ Recording **not yet verified during a live run** (next step).

---

## 7. Next Steps

1. Run the recorder-enabled task for **one episode** and confirm an HDF5 file is written.
2. Audit the file (schema, timestamps, metrics, object-pose lock during carry).
3. Scale collection (≈100 episodes per object) and curate.
4. Train the imitation-learning policy on the curated dataset (Milestone 5).
5. Later: plugin instances for the remaining objects, tighter placement tolerance, perception for dynamic obstacles.

---

## 8. Known Limitations (documented, not blocking)

- The weld is an **idealized attachment**, not a contact/force-based suction model; sufficient for clean expert demonstrations.
- Placement acceptance tolerance is currently forgiving (7 cm XY / 8 cm Z); tighten once repeatability is confirmed.
- The grasp plugin is configured for `yellow_box`; additional objects need additional plugin instances.

---

## 9. Results Summary

| Metric | Result |
|---|---|
| Episodes completed | 10 / 10 |
| Cartesian coverage | fraction = 1.000 on all segments |
| Approach length | 0.96 – 1.08 m |
| Grasp descent | 0.10 – 0.11 m |
| Lift–transfer–place | 1.09 – 1.21 m (single trajectory) |
| Retreat | ≈ 0.096 m |
| Final placement | [0.135–0.136, 0.949–0.950, 0.751] m (≤ 7 mm from bin centre in XY) |
| Grasp mechanism | Native body-based weld, engaged/released on the physics step |

---

*Prepared 29 October 2026 — vibe_version.*

