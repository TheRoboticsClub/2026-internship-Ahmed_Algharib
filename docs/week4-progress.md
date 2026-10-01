# Internship Progress Week 4: Robotic Manipulation Benchmarks (IL & RL)

**Author:** Ahmed Algharib  
**Date:** October 1, 2026  
**Topic:** State-of-the-Art Imitation Learning (IL) & Reinforcement Learning (RL) Benchmarks for Industrial Manipulation

---

## 📌 Executive Summary
This week focused on identifying and categorizing state-of-the-art RL and IL benchmarks for industrial robotic manipulation. To keep this actionable and concise for the mentorship team, the research has been distilled into **7 core application areas**, with a specific focus on simulation-to-real (sim-to-real) transfer and the integration of **MuJoCo** and **MoveIt2**.

---

## 🛠️ 7 Key Application Areas & Benchmarks

### 1. Bin-Picking
| Title | Year | Key Takeaway / Relevance |
| :--- | :---: | :--- |
| **Learning Synergies between Pushing and Grasping** | 2018 | Foundational RL model for uncluttering dense bins via push-and-grasp policies. |
| **Dex-Net 4.0: Learning Ambidextrous Robot Grasping** | 2019 | Standard industrial benchmark combining suction and parallel-jaw grippers. |

### 2. Assembly / Peg-in-Hole / Insertion
| Title | Year | Key Takeaway / Relevance |
| :--- | :---: | :--- |
| **IndustReal: Transferring Contact-Rich Assembly** | 2023 | Sim-to-real benchmark for tight-tolerance peg-in-hole using force-torque feedback. |
| **robosuite: Modular Simulation Framework** | 2020 | Standardized bi-manual peg-in-hole environments. **[MuJoCo]** |

### 3. Screwing / Fastening in Constrained Spaces
| Title | Year | Key Takeaway / Relevance |
| :--- | :---: | :--- |
| **RL for Threaded Fastener Insertion and Screwing** | 2021 | Contact-rich bolt-tightening policies using force and tactile feedback. |
| **Tactile-Informed RL for Threaded Assembly** | 2021 | Precision alignment and screwing in spatially constrained fixtures. |

### 4. Kitting
| Title | Year | Key Takeaway / Relevance |
| :--- | :---: | :--- |
| **AutoKit: Autonomous Robotic Kitting via RL** | 2021 | Multi-object pick, orientation alignment, and precision tray sequencing. |
| **Learning Multi-Object Kitting with Relational GNNs** | 2022 | Organizing heterogeneous industrial parts into designated spatial slots. |

### 5. Palletizing
| Title | Year | Key Takeaway / Relevance |
| :--- | :---: | :--- |
| **Deep RL for 3D Bin Packing and Palletizing** | 2021 | Constrained 3D box stacking and layer stability policies for robot arms. |
| **RL Environment for Autonomous Robotic Palletizing** | 2022 | Open-source simulation benchmark for industrial box packing. **[MuJoCo]** |

### 6. Deformable / Elastic-Part Manipulation
| Title | Year | Key Takeaway / Relevance |
| :--- | :---: | :--- |
| **SoftGym: Benchmarking Deformable Object Manipulation** | 2021 | Standardized sim benchmark for ropes, cables, and fabrics. **[MuJoCo/PyBullet]** |
| **PlasticineLab: Differentiable Physics Benchmark** | 2021 | Fine-grained elastic and deformable part shaping skills. |

### 7. Simulation Benchmarks & Platforms (MuJoCo & MoveIt2)
| Title | Year | Key Takeaway / Relevance |
| :--- | :---: | :--- |
| **MuJoCo Physics Engine** | 2012+ | The dominant, highly accurate physics engine for training RL contact-rich policies. |
| **MoveIt2 (ROS 2 Motion Planning)** | 2020+ | The standard framework for executing learned policies, trajectory planning, and collision checking on real hardware. |

---

## 🔬 What Researchers Are Actually Doing with IL & RL (Current Trends)
Based on the literature, top robotics labs are focusing on these practical strategies:
1. **Hybrid IL + RL Pipelines**: Pure RL from scratch is rare. The standard is to use **Behavior Cloning (BC)** or human teleoperation to establish a baseline policy, then use **RL (e.g., SAC, PPO)** to fine-tune and enable recovery from errors.
2. **Sim-to-Real via Domain Randomization**: Training in **MuJoCo** (or Isaac Sim) with randomized friction, mass, and latency, then deploying zero-shot or with minimal fine-tuning to hardware.
3. **Multimodal Feedback**: Pure vision fails for contact-rich tasks (screwing, insertion). Researchers are heavily integrating **force-torque (F/T) sensors** and **tactile arrays** (e.g., GelSight) into the RL observation space.

---

## 💡 Suggestions for Our Next Steps
1. **Narrow Focus**: Instead of tackling all 7 areas, I suggest we focus our immediate prototype on **Task 2 (Assembly/Insertion)** or **Task 3 (Screwing)**, as they have the most mature sim-to-real pipelines and align well with our current validation.
2. **Tooling Setup**: Formalize a **MuJoCo** environment (via `robosuite` or `Gymnasium`) for training, and ensure our hardware stack can seamlessly interface with **MoveIt2** for execution.
3. **Baseline First**: Implement a simple Behavior Cloning (BC) baseline using human-demo data before attempting complex RL reward shaping.

---

## 🎥 Implementation Demo: MoveIt2 & MuJoCo Validation

Below is a direct validation recording of the MoveIt2 and MuJoCo integration pipeline developed during this internship:

<video width="100%" controls autoplay loop muted>
  <source src="assets/videos/moveit2-mujoco-validation.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

*(Fallback link if video does not load: [moveit2-mujoco-validation.webm](assets/videos/moveit2-mujoco-validation.webm))*

> **Note on Video Path:** If this markdown file is placed inside a subfolder (e.g., `blog/` or `docs/`), update the video source path to `../assets/videos/moveit2-mujoco-validation.webm`.

---
*Report generated for Week 4 Internship Progress.*
