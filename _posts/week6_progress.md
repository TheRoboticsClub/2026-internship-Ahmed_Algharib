# Week 6 — From Hardcoded Demo to a Generalized Data-Generation Pipeline
### UR5e + MuJoCo + MoveIt2 → MobRT-style Imitation Learning Dataset

**Author:** Ahmed  
**Internship Week:** 6  
**Project:** Digital-twin pick-and-place for scalable imitation learning (MobRT-inspired)  
**Stack:** ROS 2 (Jazzy), MoveIt2, MuJoCo (`mujoco_ros2_control`), Python, HDF5

---

## TL;DR

This week I turned a **hardcoded** classical pick-and-place script into a
**generalized, relative-coordinate system** that can grasp an object from *any*
randomized pose, and I wired in a **20 Hz data logger** that exports
observation/action episodes as **HDF5** files — the exact structure needed to
train diffusion-policy-style imitation learners like the baseline in the
**MobRT** paper.

Along the way I hunted down three nasty simulation bugs:

1. **Ghost coordinates** — a stale static TF transform overriding live physics.
2. **Ghost gripper** — an end-effector with no collision geometry in MoveIt.
3. **Solid-vs-hollow** — MoveIt box primitives blocking in-bin drops.

---

## 1. Context & Goal

The internship goal is to reproduce, on a **fixed-base UR5e digital twin**, the
data-generation half of the MobRT framework
(*"MobRT: A Digital Twin-Based Framework for Scalable Learning in Mobile
Manipulation"*, Mei et al., 2025):

> autonomously generate diverse, physically consistent demonstrations in
> simulation → distill them into a Transformer policy trained under the
> Diffusion Policy / Flow-Matching framework.

MobRT's pipeline has three ingredients we need to mirror:

| MobRT ingredient | Our Week-6 equivalent |
|---|---|
| Annotated assets + manipulation actions | Relative grasp/place poses from live object frames |
| Randomized environment reset | `randomize_object_position()` + ground-truth injection |
| Validated trajectory recording | 20 Hz HDF5 logger with success filtering |

---

## 2. What Changed This Week

### 2.1 Relative-coordinate planning (the core refactor)

The original script stored absolute spawn coordinates in a Python dictionary.
That couples the policy to one frozen scene. I replaced it with **live queries +
relative offsets in homogeneous coordinates**:

```python
# Live pose of the object (ground truth or TF)
T_world_obj = self.tf(WORLD, obj_name)

# Grasp pose = object frame ⊕ vertical offset
T_obj_to_grasp = np.eye(4)
T_obj_to_grasp[2, 3] = hh + TOOL_LEN + GRASP_GAP
T_world_grasp = T_world_obj @ T_obj_to_grasp
grasp_xyz = T_world_grasp[:3, 3]
```

Because the offset is applied **in the object's own frame**, the approach
direction automatically follows the object's orientation — a tilted object is
approached perpendicularly, with zero extra code. The existing motion primitives
(`go`, `cart_go`, `home`) were left untouched; they only receive `(x, y, z)`.

**Validation:** moving `yellow_box` in `scene.xml` from `(-0.55, 0.30)` to
`(-0.70, 0.40)` required **no Python changes** — the robot adapted and reported
`### yellow_box: PLACED`.

### 2.2 The `Z_TRAVEL` absolute/relative bug

`Z_TRAVEL = 1.15` is an **absolute world height** (the "highway" the robot flies
on while carrying). My first refactor treated it as a relative offset, producing
targets at `bin_z + 1.15 ≈ 1.85 m` — far beyond the UR5e's ~0.85 m reach:

```
[ERROR] [transfer0] no IK for site target [0.142 0.95 1.85]
```

**Fix:** compute the offset so the *final* height equals `Z_TRAVEL`:

```python
T_obj_to_lift[2, 3] = Z_TRAVEL - T_world_obj[2, 3]   # absolute height, relative offset
```

### 2.3 Data logger (MobRT-compatible HDF5)

A 20 Hz background timer records the proprioceptive state during each episode
and exports it on release:

```text
episode_yellow_box.hdf5
├── observations/
│   ├── qpos     (T, 6)   joint positions
│   ├── qvel     (T, 6)   joint velocities
│   ├── ee_pos   (T, 3)   end-effector position
│   └── obj_pos  (T, 3)   object position (ground truth)
└── actions      (T, 6)   next-step target joint positions
```

`actions` are produced by shifting `qpos` by one step — the standard
action representation for **position-controlled** arms; action *chunking*
(`A = [a_t … a_{t+H-1}]`, as in MobRT/ACT) is left to the training framework.

Verified output:

```text
Keys: ['actions', 'observations']
Obs Keys: ['ee_pos', 'obj_pos', 'qpos', 'qvel']
Actions shape: (81, 6)
```

### 2.4 Randomizer + ground-truth injection

MobRT stresses *randomized environment resets*. I added:

```python
new_pos = node.randomize_object_position(name)   # MuJoCo set_free_joint_state
node.current_obj_pos = new_pos                   # logger sees exact truth
ok = node.pick_place(name, manual_pos=new_pos)   # planner sees exact truth
```

**Why bypass TF here?** The tree has *two competing publishers* per object: the
static `robot_state_publisher` (from the xacro) and the dynamic MuJoCo plugin.
The static one wins, so TF reports stale poses. Injecting ground truth makes the
planner and the dataset immune to that conflict — a deliberate, professional
choice, not a workaround.

### 2.5 Collision-awareness strategy ("smart blindness")

| Element | Visible to MoveIt? | Reason |
|---|---|---|
| Main table / stand table | ✅ | Structural avoidance |
| Tabletop obstacles (e.g. green cylinder) | ✅ | Planner routes around them |
| Target bins | ❌ | MoveIt boxes are **solid**; a visible bin → `GOAL_IN_COLLISION` on drop |
| Compensation | `Z_TRAVEL = 1.30` | Transfers fly above the invisible bins |

---

## 3. Bug Hunt: Three Ghosts of ROS 2 Simulation

### 👻 Ghost #1 — Stale coordinates that survived every restart
Symptom: `tf2_echo world yellow_box` kept printing `[-0.550, 0.300, 0.800]`
no matter what `scene.xml` said; `tf2_monitor` showed a delay equal to the
node's uptime (a static transform).

Root cause chain:
1. Launch files read from **`install/`**, not `src/` → `colcon build` required.
2. `mujoco_scene.xacro` hardcoded `yellow_box_joint` as a **fixed** joint at the
   old origin → `robot_state_publisher` broadcast it forever.
3. `mujoco_plugins.yaml` had `frame_id: ""`, detaching dynamic frames from the
   tree root.

Fixes: sync the xacro origin, set `frame_id: "mujoco_scene"`, rebuild, and
finally rely on ground-truth injection at runtime.

### 👻 Ghost #2 — The gripper that wasn't there
MoveIt warned at startup:

```
Link eef has visual geometry but no collision geometry.
```

The planner therefore treated the tool as invisible and let it clip through
obstacles. Fix: give `eef` a simple collision primitive in `ur5e.xml`:

```xml
<geom type="cylinder" size="0.04 0.06" pos="0 0 0"/>
```

### 👻 Ghost #3 — Solid bins, hollow intent
Adding bins to the planning scene made drops fail: MoveIt boxes are solid
blocks, so "inside the bin" = "inside concrete". Resolution: keep bins out of
the collision map and fly above them (`Z_TRAVEL`), keeping obstacles visible.

---

## 4. Results

* ✅ Generalized pick-and-place validated at multiple randomized poses.
* ✅ HDF5 episodes recorded with correct `(T, 6)` action tensors.
* ✅ Obstacle-aware planning after collision-geometry fixes.
* ✅ Full pipeline runs end-to-end unattended:
  `randomize → grasp → transfer → drop → log → home`.

<!-- Suggested media for the blog version -->
<!-- ![Randomized grasp](assets/randomized_grasp.gif) -->
<!-- ![HDF5 inspection](assets/hdf5_check.png) -->

---

## 5. Lessons Learned

1. **`src` ≠ `install`.** Every XML/xacro/YAML edit needs
   `colcon build --packages-select <pkg>` before restart.
2. **Stale-TF fingerprints:** `At time 0.0` in `tf2_echo`, or `tf2_monitor`
   delays equal to uptime ⇒ static/cached frame, not live data.
3. **MoveIt ≠ MuJoCo.** The planning scene contains only what you explicitly
   publish to `/apply_planning_scene`.
4. **Ground truth beats gossip.** When *you* move an object, pass the pose
   directly instead of re-reading it through a contested TF tree.
5. **Absolute vs relative is a contract.** Constants like `Z_TRAVEL` must
   declare which one they are — in a comment and in the math.

---

## 6. Next Week (Week 7)

- [ ] Batch collection: 50–100 validated episodes per object
      (unique filenames via timestamps/indices).
- [ ] Extend randomization to yaw and to all four objects.
- [ ] Dynamic planning-scene updates after each randomization
      (obstacles move too).
- [ ] Add RGB/depth observations to match MobRT's multimodal encoders.
- [ ] First training run: Flow-Matching / Diffusion-Policy baseline on the
      collected HDF5 set.

---

## 7. References

1. Y. Mei et al., *MobRT: A Digital Twin-Based Framework for Scalable Learning
   in Mobile Manipulation*, arXiv:2510.04592, 2025.
2. C. Chi et al., *Diffusion Policy: Visuomotor Policy Learning via Action
   Diffusion*, IJRR, 2024.
3. T. Z. Zhao et al., *Learning Fine-Grained Bimanual Manipulation with
   Low-Cost Hardware* (ACT / action chunking), 2023.
4. `mujoco_ros2_control` documentation (free-joint state publishing &
   `set_free_joint_state` service).

---

*Code, scene files and full change rationale: see `REFACTOR_NOTES.md` in this
repository.*
