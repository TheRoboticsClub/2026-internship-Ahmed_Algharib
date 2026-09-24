# JdeRobot Internship — First Two Weeks Progress

**Author:** Ahmed Algharib  
**Project:** JdeRobot / The Robotics Club Internship 2026  
**Period:** 7–21 September 2026  
**Focus:** Robotics Academy, MuJoCo, UR5 imitation learning, and reproducible simulation setup

---

## 1. Overview

During the first two weeks of the internship, the work focused on understanding the Robotics Academy environment, reproducing the relevant robot-learning setup, investigating the Docker/Academy runtime, and preparing a MuJoCo-based UR5 environment for imitation learning.

The main objective was to establish a reliable workflow before moving into the learning stage:

```text
Robotics Academy
      ↓
Environment / robot understanding
      ↓
Docker + runtime investigation
      ↓
UR5 / Pick-and-Place setup
      ↓
MuJoCo environment
      ↓
Expert demonstrations
      ↓
Behavior Cloning
      ↓
Evaluation
```

The first two weeks were therefore mainly **infrastructure, reproduction, debugging, and preparation for imitation learning**, rather than training a final policy.

---

## 2. Week 1 — Robotics Academy Setup and Initial Investigation

### 2.1 Robotics Academy setup

The first stage was to install and run the Robotics Academy environment using Docker and the official Academy workflow.

The Academy database was launched separately and the Robotics Academy image was tested against it.

The initial setup established the main components:

- Robotics Academy
- PostgreSQL Academy database
- Docker-based runtime
- ROS 2 environment
- Browser-based Academy interface
- Robot-learning exercises

### 2.2 Docker and GPU investigation

The Academy environment was tested using Docker with GPU access.

The host system has an NVIDIA GPU, but the Docker Desktop environment did not expose the expected `/dev/dri` interface. GPU launch attempts also produced a CDI-related error:

```text
failed to discover GPU vendor from CDI: no known GPU vendor found
```

A direct `/dev/dri` launch also failed because the device was not available inside the Docker environment:

```text
error gathering device information while adding custom device "/dev/dri":
no such file or directory
```

This established that the problem was not simply the Robotics Academy application itself; the Docker Desktop GPU/device configuration was also relevant.

A CPU-only launch was then used to separate the GPU problem from application-level problems.

---

## 3. Robotics Academy Image Investigation

### 3.1 Latest image investigation

The published Robotics Academy image was inspected directly instead of assuming that the problem came from the host configuration.

The tested image was:

```text
jderobot/robotics-academy:latest
```

The image contained Python 3.10.12 and the Robotics Academy source tree.

However, the Django configuration referenced the Python package:

```text
react_frontend.apps.ReactFrontendConfig
```

while the image contained the frontend static files but did not contain the expected Python package files such as:

```text
react_frontend/apps.py
react_frontend/__init__.py
react_frontend/urls.py
```

The resulting runtime error was:

```text
ModuleNotFoundError: No module named 'react_frontend.apps'
```

This showed that there was an application/image packaging mismatch in the tested `latest` image.

### 3.2 Avoiding a misleading local-volume test

A local source directory was initially mounted into the container. This introduced another mismatch because the mounted directory did not contain the generated frontend build artifacts expected by the runtime, including:

```text
react_frontend/webpack-stats.json
```

Therefore, the official image was subsequently tested without mounting the local Robotics Academy source over `/RoboticsAcademy`.

This was important for distinguishing:

```text
Host / Docker configuration
        vs.
Published Academy image
        vs.
Local Academy source
```

---

## 4. Academy Source and Version Investigation

The next step was to compare the Academy source, Robotics Applications (RI), and the published Docker image.

The Academy checkout was on:

```text
Branch: jazzy-devel
Commit: b9a58260
```

The Robotics Applications submodule was pinned to:

```text
948fabf
```

The important finding was a version mismatch between the locally pinned Robotics Applications version and the version used by the newer Docker image.

The historical Robotics Applications revision used:

```text
CustomRobots/ur5
```

while a newer branch had renamed the relevant structure to:

```text
robot_arms
```

The newer Docker image was based on a different branch/version combination, which meant that the database/runtime expectations and the robot package structure were no longer aligned.

The older Robotics Applications revision contained the expected UR5-related stack, including the UR5/Robotiq/MoveIt configuration and the Pick-and-Place Harmonic exercise.

This investigation led to a reproducibility-oriented approach rather than changing the application blindly.

---

## 5. Reproducibility Investigation

A reproducibility harness was prepared to compare the relevant Academy and Robotics Applications revisions.

The key baseline identified during the investigation was:

```text
Robotics Academy:
26fffd1fcfcc0b932d17a5000ca755692fae1d95

Robotics Applications:
948fabf01a6b7706a0203c786bfa3baeca6447e7
```

The investigation also showed that the published image and the local source were not necessarily using the same dependency state.

An additional obstacle appeared while attempting to rebuild the image: Docker's internal Git operations against public GitHub repositories failed with errors such as:

```text
could not read Username
expected flush after ref listing
```

This prevented a clean rebuild from completing through that path and reinforced the need to keep the working baseline reproducible.

---

# 6. Week 2 — UR5 and Imitation Learning Preparation

## 6.1 MuJoCo environment

In parallel with the Academy investigation, work started on reproducing the relevant robot-learning setup in MuJoCo.

The purpose was to create a controlled simulation environment that can later be used for:

- expert demonstrations
- trajectory collection
- Behavior Cloning
- evaluation
- later DAgger / reinforcement-learning experiments

The target task is based on UR5 manipulation / Pick-and-Place behavior.

The workflow was kept deliberately simple at this stage:

```text
UR5 simulation
      ↓
Robot control
      ↓
Expert trajectory
      ↓
Dataset
      ↓
Behavior Cloning
```

---

## 7. Robot Control and Collision Debugging

During the robot-control experiments, a physical collision was identified in the simulation.

The relevant simulation log showed:

```text
forearm_link <-> table
```

starting around step 200 and continuing afterwards.

The end-effector also stopped around:

```text
z ≈ 1.30
```

while the intended target was approximately:

```text
z = 0.94
```

The interpretation was that the robot forearm contacted the table edge while moving toward the target. The collision prevented the robot from completing the intended downward motion.

This was an important debugging result because it showed that the observed frozen end-effector was a physical simulation/collision issue rather than simply a failed inverse-kinematics target.

The next control-stage requirement is therefore to ensure that the motion/IK solution respects the table collision geometry before collecting demonstrations.

---

# 8. Imitation Learning Pipeline

The intended learning pipeline after the environment is stable is:

```text
MuJoCo UR5
    ↓
Expert controller / demonstrations
    ↓
Trajectory dataset
    ↓
Behavior Cloning (BC)
    ↓
Policy evaluation
    ↓
DAgger (if needed)
    ↓
PPO / RL fine-tuning (later)
    ↓
Domain randomization
    ↓
Sim-to-real
```

The first learning milestone is **Behavior Cloning**, not a large-scale robot foundation model.

The immediate goal is to demonstrate the complete loop:

```text
Demonstration → Dataset → Training → Policy → Evaluation
```

---

# 9. Current Technical State

## Completed / investigated

- Robotics Academy Docker setup
- Academy database setup
- Official Academy image testing
- Docker GPU/device investigation
- CPU-only runtime testing
- Published-image inspection
- Django/frontend packaging investigation
- Academy/Robotics Applications version comparison
- UR5 package/version investigation
- Reproducibility baseline identification
- MuJoCo UR5 environment preparation
- Robot control testing
- Collision debugging
- Initial imitation-learning workflow definition

## Main issues identified

### Issue 1 — Docker GPU access

Docker Desktop did not expose the expected GPU/device interface required by the official launch configuration.

### Issue 2 — Robotics Academy image packaging

The tested `latest` image referenced `react_frontend.apps.ReactFrontendConfig`, while the expected Python frontend package files were missing from the image.

### Issue 3 — Version drift

The Academy/Robotics Applications revision used by the working setup did not match the newer runtime/image dependency structure.

### Issue 4 — UR5 collision

The MuJoCo UR5 control experiment encountered a persistent forearm/table collision, preventing the end-effector from reaching the intended target.

---

# 10. Next Steps

The next stage is to stabilize the robot-learning environment and move from infrastructure work to learning experiments.

### Step 1 — Stable UR5 environment

Resolve the robot/table collision and verify that the UR5 can reliably execute the target Pick-and-Place motion.

### Step 2 — Expert demonstrations

Generate and record successful trajectories containing observations/actions suitable for imitation learning.

### Step 3 — Dataset

Create a reproducible dataset format for the demonstrations.

### Step 4 — Behavior Cloning

Train a first supervised policy from the expert demonstrations.

### Step 5 — Evaluation

Evaluate the learned policy on held-out initial states and compare it with the expert.

### Step 6 — Interactive imitation learning

If Behavior Cloning suffers from distribution shift, investigate DAgger.

### Step 7 — RL fine-tuning

Only after the IL baseline is working, investigate PPO or another RL method for policy improvement.

---

# 11. Reproducibility Notes

The important lesson from the first two weeks is that robot-learning experiments should keep the following versions synchronized:

```text
Academy commit
      +
Robotics Applications commit
      +
Docker image
      +
ROS distribution
      +
Robot package structure
      +
Simulation environment
```

A future experiment should record these values before training so that results can be reproduced.

Suggested experiment record:

```text
Date:
Academy commit:
RI commit:
Docker image/tag:
ROS distribution:
Robot:
Task:
Simulation:
Controller:
Dataset version:
Policy:
Training configuration:
Evaluation result:
Known issues:
```

---

# 12. Repository Documentation Structure

The internship repository can use the following structure:

```text
2026-internship-Ahmed_Algharib/
├── README.md
├── docs/
│   └── 2026-09-first-two-weeks.md
├── code/
├── assets/
└── experiments/
```

This document is intended as the first technical progress report. Future weekly reports can be added without changing the main project README.

---

# 13. References / Project Resources

- JdeRobot Robotics Academy: https://jderobot.github.io/RoboticsAcademy/
- Robotics Academy repository: https://github.com/JdeRobot/RoboticsAcademy
- Robotics Applications repository: https://github.com/JdeRobot/RoboticsInfrastructure
- Robotics Academy Docker image: https://hub.docker.com/r/jderobot/robotics-academy
- MuJoCo: https://mujoco.org/
- MuJoCo repository: https://github.com/google-deepmind/mujoco

---

# 14. Summary

The first two weeks established the technical foundation for the internship. The work began with Robotics Academy setup and runtime investigation, then moved into source/version analysis and reproducibility, while the parallel MuJoCo work established the UR5 simulation needed for imitation learning.

The main outcome is a clearer and reproducible path from the simulation environment to robot learning:

```text
Robotics Academy / MuJoCo
          ↓
       UR5 Task
          ↓
   Expert Demonstrations
          ↓
       Dataset
          ↓
  Behavior Cloning
          ↓
      Evaluation
          ↓
   DAgger / RL later
```

The immediate priority is to make the UR5 task reliable, collect successful demonstrations, and establish the first Behavior Cloning baseline.
