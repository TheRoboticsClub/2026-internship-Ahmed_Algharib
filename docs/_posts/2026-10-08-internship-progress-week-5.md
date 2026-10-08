---
title: Internship Progress Week 5
date: 2026-10-08
categories: [Internship, Robotics, Imitation Learning]
tags: [JdeRobot, MoveIt2, MuJoCo, UR5e, ROS2, Pick-and-Place, Imitation Learning, Reinforcement Learning]
---

# Internship Progress Week 5

This week focused on completing the **classical UR5e pick-and-place baseline**, resolving major MoveIt2–MuJoCo integration problems, and preparing the system for the next stage: **learning pick-and-place from demonstrations using Imitation Learning / Reinforcement Learning**.

## 1. Classical UR5e Pick-and-Place

The main milestone was completing a full classical pick-and-place task in the custom **UR5e + MuJoCo + ROS 2 + MoveIt2** environment.

The robot successfully executed:

```text
HOME → Pre-grasp → Grasp → Attach/Hold → Transfer → Release → Retreat → HOME
```

for four objects:

- Yellow box → yellow target
- Red box → red target
- Blue ball → blue target
- Green cylinder → green target

The robot returned to the home configuration after each completed operation.

### Final result

The classical controller now provides a working expert/reference policy for the next learning stage. The next step is to use this controller to generate demonstration trajectories rather than immediately replacing it with RL.

### Pick-and-Place Video

**YouTube:** https://youtu.be/vWS9V-gGSoY

> Add the final repository video here once the local copy is available.

<!--
<video controls width="100%">
  <source src="/2026-internship-Ahmed_Algharib/assets/videos/ur5e-pick-and-place.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>
-->

---

## 2. Key Technical Challenges and Solutions

The most significant part of this week was resolving integration problems between the **MuJoCo model, URDF, MoveIt2, TF, ros2_control, and the custom end effector**.

### 2.1 End-Effector Integration — Major Hurdle

#### Problem

The custom end effector was initially missing from the complete MoveIt/RViz robot model. This caused a long debugging cycle because the robot could move and plan, while the actual tool geometry, tool frame, collision model, and MuJoCo geometry were not initially represented consistently.

#### Challenge 1 — Scale mismatch

The MuJoCo tool mesh used a scale of approximately:

```text
0.12479
```

while the URDF representation initially used an inconsistent scale.

This produced a significant geometric mismatch, including an approximately **13 cm offset** between the expected and rendered tool geometry.

#### Challenge 2 — Collision list

After correcting the geometry, MoveIt's collision matrix still required explicit handling of the relationships between the custom tool and wrist links.

The SRDF collision matrix therefore needed appropriate:

```xml
<disable_collisions ... />
```

entries.

#### Solution

The final solution was to:

1. Add the custom end effector to the URDF/Xacro.
2. Match the MuJoCo mesh scale.
3. Reproduce the MuJoCo mounting transform.
4. Add visual and collision geometry.
5. Create the EEF frame/site.
6. Update the MoveIt collision matrix.
7. Rebuild and validate the TF chain.

The final conceptual chain is:

```text
wrist_3_link
      ↓
  eef_mount
      ↓
     eef
      ↓
  eef_site
```

### Evidence image

Add the actual screenshot here:

```text
assets/images/week-5-eef-integration.png
```

```markdown
![End-effector integration and scale mismatch](assets/images/week-5-eef-integration.png)
```

---

### 2.2 TF / Joint-State Synchronization

#### Problem

At one stage, `/joint_states` contained empty or incomplete arrays, preventing MoveIt from reliably tracking the current robot state.

#### Solution

The controller configuration explicitly listed the six UR5e joints in `ros2_controllers.yaml`:

```text
shoulder_pan_joint
shoulder_lift_joint
elbow_joint
wrist_1_joint
wrist_2_joint
wrist_3_joint
```

This established a stable joint-state pipeline:

```text
MuJoCo
   ↓
mujoco_ros2_control
   ↓
ros2_control
   ↓
joint_state_broadcaster
   ↓
/joint_states
   ↓
MoveIt2
```

### Evidence image

```text
assets/images/week-5-joint-state-sync.png
```

---

### 2.3 World-Frame / Base-Orientation Mismatch

#### Problem

The MuJoCo robot base used:

```xml
quat="0 0 0 -1"
```

while the initial URDF base transform effectively used:

```xml
rpy="0 0 0"
```

These represented different orientations.

#### Solution

The URDF base transform was changed to:

```xml
<origin xyz="-0.128 0.470 0.75"
        rpy="0 0 3.141592653589793"/>
```

This mirrors the 180-degree Z rotation represented by the MuJoCo quaternion.

The important lesson is that synchronization requires both **position and orientation** to represent the same physical frame.

### Evidence image

```text
assets/images/week-5-world-frame-mismatch.png
```

---

### 2.4 Planning Failures

#### Problem

OMPL sometimes failed to find solutions when unnecessarily tight orientation constraints were imposed.

#### Solution

The planning strategy was changed to use:

- Joint-space goals where appropriate.
- Looser position/orientation tolerances.
- Free yaw where a fixed yaw is unnecessary.
- Cartesian paths for transfer motions where appropriate.
- Separate pre-grasp, grasp, transfer, release and retreat stages.

Conceptually:

```text
                 ┌── Joint-space planning
Pick/Place pose ─┤
                 └── Cartesian transfer
```

### Evidence image

```text
assets/images/week-5-planning-failure.png
```

---

## 3. Final Classical Architecture

```text
                    MoveIt2
                       │
                 Motion Planning
                       │
                Joint Trajectory
                       │
                  ros2_control
                       │
              mujoco_ros2_control
                       │
                    MuJoCo
                       │
        ┌──────────────┴──────────────┐
        │                             │
      UR5e                         Scene
        │                    ┌────────┼────────┐
      EEF                  Table    Objects   Targets
        │
     eef_site
```

This provides a common simulation environment for comparing classical planning and learned manipulation policies.

---

# 4. From Classical Planning to Robot Learning

The next stage is to use the successful classical controller as an **expert demonstrator**.

```text
Classical MoveIt2 + MuJoCo
            ↓
     Expert trajectories
            ↓
      Demonstration dataset
            ↓
      Behavior Cloning
            ↓
       Evaluation
            ↓
     DAgger / refinement
            ↓
   IL + RL fine-tuning
            ↓
     Domain randomization
            ↓
        Sim-to-Real
```

The first scientific baseline should be a reproducible **Behavior Cloning policy trained from trajectories generated by the working classical controller**.

---

# 5. Dataset to Record

For each timestep, record:

```text
State:
    q1 ... q6
    dq1 ... dq6
    end-effector pose
    object pose
    target pose
    task/object identity
```

A practical first action representation is:

```text
a_t = [q1, q2, q3, q4, q5, q6]
```

If the suction/grasp command is explicitly represented:

```text
a_t = [q1, q2, q3, q4, q5, q6, gripper/suction]
```

Also record:

```text
episode_id
timestamp
task/object
success/failure
phase
```

Suggested phases:

```text
home
pre_grasp
grasp
transfer
release
retreat
```

---

# 6. Pick-and-Place Literature Review

Create a focused literature review around:

> **Robot Pick-and-Place with Imitation Learning, Reinforcement Learning, and Learning-Based Manipulation**

The review should answer:

1. How are pick-and-place demonstrations represented?
2. What state/action spaces are commonly used?
3. How much demonstration data is required?
4. When is Behavior Cloning sufficient?
5. When is temporal action chunking useful?
6. When does diffusion-based policy learning help?
7. When is RL useful after imitation learning?
8. How are grasping and contact handled?
9. How are failures and distribution shift handled?
10. How do these methods transfer from simulation to real robots?

---

# 7. NotebookLM Literature Review

Create a NotebookLM notebook with exactly this name:

> **UR5e Pick-and-Place: Imitation Learning, Reinforcement Learning, and Learning-Based Manipulation Literature Review**

Do **not** publish or include the private NotebookLM URL in this internship Markdown file.

Use the notebook as a literature-review workspace rather than as the implementation itself.

### Source groups

#### Group A — Foundational imitation learning
- Behavior Cloning
- DAgger
- Learning from Demonstration

#### Group B — Robot manipulation datasets and benchmarks
- robomimic
- offline robot manipulation datasets
- BC-RNN / sequence-based policies

#### Group C — Modern imitation learning
- Action Chunking with Transformers (ACT)
- Diffusion Policy

#### Group D — Reinforcement learning
- QT-Opt
- simulation-to-real manipulation
- domain randomization

#### Group E — Modern generalist policies
- Octo
- OpenVLA
- Open X-Embodiment

### Questions to ask NotebookLM

```text
1. Which methods are most suitable for a UR5e pick-and-place task in MuJoCo?
2. Compare Behavior Cloning, BC-RNN, ACT, Diffusion Policy, and RL.
3. What demonstration format does each method require?
4. What practical dataset size is reported?
5. Which methods work well with joint-space actions?
6. Which methods require images or visual observations?
7. Which methods can be trained entirely in simulation?
8. Which methods are easiest to reproduce on a local RTX GPU?
9. Which method is the strongest first baseline for this internship?
10. What research gap remains for classical-planner-generated demonstrations
    in a UR5e/MuJoCo pick-and-place environment?
```

---

# 8. Five Priority Papers

## 1. robomimic — Offline Robot Manipulation

**Mandlekar et al. — “What Matters in Learning from Offline Human Demonstrations for Robot Manipulation”**

Venue: Conference on Robot Learning (CoRL), 2021/2022 publication.

Why it matters:

- Directly studies learning from robot manipulation demonstrations.
- Provides reproducible datasets and benchmarks.
- Compares multiple imitation and offline RL methods.
- Gives practical lessons about dataset quality, coverage and evaluation.

For this project: the best **methodology/benchmark reference** before training the first policy.

Paper: https://arxiv.org/abs/2108.03298

---

## 2. ACT — Action Chunking with Transformers

**Zhao et al. — “Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware”**

Venue: Robotics: Science and Systems (RSS), 2023.

Why it matters:

- Introduces Action Chunking with Transformers.
- Learns sequences of actions rather than isolated single-step actions.
- Demonstrates strong manipulation performance from relatively small demonstration sets.
- Highly relevant to temporally structured manipulation.

For this project: the strongest **advanced imitation-learning candidate after the BC baseline**.

Paper: https://arxiv.org/abs/2304.13705

---

## 3. Diffusion Policy

**Chi et al. — “Diffusion Policy: Visuomotor Policy Learning via Action Diffusion”**

Venue: Robotics: Science and Systems (RSS), 2023.

Why it matters:

- Models robot actions as a conditional diffusion process.
- Handles multimodal behavior.
- Uses temporal action sequences and receding-horizon control.
- Provides a strong modern manipulation-learning baseline.

For this project: a strong candidate for a **second-stage comparison against ACT/BC**.

Paper: https://arxiv.org/abs/2303.04137

---

## 4. QT-Opt — Reinforcement Learning for Manipulation

**Kalashnikov et al. — “Scalable Deep Reinforcement Learning for Vision-Based Robotic Manipulation”**

Venue: Conference on Robot Learning (CoRL), 2018.

Why it matters:

- Demonstrates large-scale deep RL for robotic grasping.
- Uses closed-loop visual feedback.
- Shows how RL can learn manipulation behavior directly from interaction.
- Provides a useful contrast to demonstration-driven IL.

For this project: primarily an **RL reference**, not the first implementation to reproduce.

Paper: https://arxiv.org/abs/1806.10293

---

## 5. OpenVLA — Modern Vision-Language-Action Learning

**Kim et al. — “OpenVLA: An Open-Source Vision-Language-Action Model”**

2024.

Why it matters:

- Represents the modern VLA/foundation-model direction.
- Uses large-scale robot demonstration data.
- Supports fine-tuning for new robot settings.
- Shows where manipulation learning is moving beyond task-specific BC.

For this internship: a **future/generalist-policy direction**, not the immediate baseline.

Paper: https://arxiv.org/abs/2406.09246

---

# 9. Recommended Experimental Progression

The most efficient implementation order is:

```text
STEP 1
Classical MoveIt2 expert
        ↓
STEP 2
Record trajectories
        ↓
STEP 3
Train simple Behavior Cloning
        ↓
STEP 4
Evaluate BC on the same MuJoCo task
        ↓
STEP 5
Improve temporal modeling
        ↓
BC-RNN / ACT
        ↓
STEP 6
Compare with Diffusion Policy
        ↓
STEP 7
Introduce RL fine-tuning
        ↓
STEP 8
Domain randomization
        ↓
STEP 9
Sim-to-Real
```

The first scientific comparison should therefore be:

```text
                SAME TASK
                    │
          ┌─────────┴─────────┐
          │                   │
     Classical             Learned
     MoveIt2                 BC
          │                   │
          └─────────┬─────────┘
                    ↓
             Compare success
             trajectory quality
             robustness
             execution time
```

Only after this baseline is established should ACT, Diffusion Policy or RL be introduced.

---

# 10. Evaluation Metrics

| Metric | Description |
|---|---|
| Task success rate | Complete successful pick-and-place episodes |
| Pick success | Object successfully grasped |
| Placement success | Object reaches the correct target |
| Collision rate | Collisions / invalid configurations |
| Episode duration | Time for a complete episode |
| Path length | Joint-space or Cartesian trajectory length |
| Position error | Final object/EEF position error |
| Orientation error | Final EEF orientation error |
| Number of demonstrations | Training data requirement |
| Generalization | Performance on unseen object poses/configurations |
| Failure recovery | Ability to recover after perturbations |

---

# 11. Current Status

### Completed

- [x] UR5e MuJoCo environment
- [x] MoveIt2 integration
- [x] ros2_control integration
- [x] Custom end-effector integration
- [x] Correct EEF scaling and mounting
- [x] Collision configuration
- [x] Joint-state synchronization
- [x] World/base-frame synchronization
- [x] Reliable motion-planning baseline
- [x] Classical pick-and-place
- [x] Four-object color-sorting task
- [x] Demonstration source identified for the learning stage

### Next

- [ ] Record clean expert trajectories
- [ ] Define final observation/action schema
- [ ] Build demonstration dataset
- [ ] Implement first Behavior Cloning baseline
- [ ] Evaluate BC on the same MuJoCo task
- [ ] Compare against ACT / sequence-based IL
- [ ] Study Diffusion Policy
- [ ] Add RL fine-tuning after the IL baseline
- [ ] Investigate robustness and domain randomization
- [ ] Prepare for sim-to-real evaluation

---

# 12. Outcome

Week 5 completed the **classical manipulation baseline** required before starting robot learning.

```text
MoveIt2
   ↓
Classical expert policy
   ↓
UR5e + MuJoCo
   ↓
Successful four-object pick-and-place
   ↓
Trajectory recording
   ↓
Imitation Learning
   ↓
RL fine-tuning
```

The project has now moved from **simulation and motion-planning integration** into the **data-generation and robot-learning phase**.

The next major milestone is:

> **Generate a clean, reproducible demonstration dataset from the successful classical pick-and-place expert and train the first Behavior Cloning policy.**

---

## Publication Checklist

Before publishing this post:

- [ ] Add the final pick-and-place screenshot.
- [ ] Add the EEF scale/alignment challenge screenshot.
- [ ] Add the `/joint_states` synchronization screenshot.
- [ ] Add the world-frame/base-orientation screenshot.
- [ ] Add the OMPL planning-failure/success screenshot.
- [ ] Create the NotebookLM literature-review notebook with the exact title above.
- [ ] Add the five priority papers as sources.
- [ ] Record the first expert trajectory dataset.
- [ ] Keep the private NotebookLM URL out of the public Markdown.
