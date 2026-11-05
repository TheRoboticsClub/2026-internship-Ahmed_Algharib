
# Week 9 — Pneumatic Suction, Spatial-Variation Testing, and Expert Algorithmic Foundations

**Internship:** JdeRobot 2026 — Ahmed Algharib
**Package:** `vibe_version` · **Platform:** UR5e MuJoCo twin · ROS 2 Jazzy · MoveIt 2
**Scope of this week:** integrate the pneumatic suction paradigm, answer the mentor's challenge (vary object, target, and robot-base positions), and ground every architectural choice in the expert literature.

## TL;DR
- **Suction paradigm integrated:** surface-normal-aligned approach + proximity-gated weld reuse; decomposed pick sequence (pre-grasp → linear descent → vacuum → linear lift).
- **Mentor's challenge executed:** systematic ablations over object poses, a 14-cell target grid, and three robot-base configurations.
- **Key finding:** a single fixed base cannot cover the 14-cell grid; two complementary base poses cover all 14 cells → this is workcell layout optimization, not an algorithmic failure.
- **Literature review completed:** classical vs learning vs hybrid approaches, mapped to our exact failure modes, with a study-milestone plan.

---

## 1. Pneumatic Suction Gripper Integration
A suction cup, unlike a parallel jaw, tolerates no tilted approach: the tool Z-axis must be collinear with the object's surface normal (top-down for boxes; apex-targeting for the ball and cylinder).

**Decomposed suction sequence (state machine):**
1. Pre-grasp 10 cm above the object along its surface normal.
2. Linear Cartesian descent until the cup face contacts the surface.
3. Vacuum engage → proximity-gated weld (reuses the Week 8 `GraspAttachmentPlugin`: ≤ 3 cm gate, body-based weld, offset captured at activation).
4. Linear Cartesian lift before any free-space motion.
5. Transfer → release on the physics step (real gravity).

This keeps the strict orientation constraint inside the planner (Cartesian paths with locked approach vector) instead of hoping joint-space motion preserves the seal.

---

## 2. The Mentor's Challenge: Systematic Spatial Variation

### 2.1 Test design
Three variation dimensions, one at a time (ablation):
- **Object positions:** randomized pickup poses in a bounded table region (seeded).
- **Target positions:** a 14-cell grid spanning the extended table, including outer-right edge cells at X ≈ 0.967 m.
- **Robot base positions/orientation:** original base (180° yaw), original base (0° yaw), shifted base (0.186, 0.122) m.

![Week 9 workcell](images/week9_workcell_14cell.png)
*Fig 1: The variation-testing workcell. MuJoCo (left): target bins aligned along the table edge forming the 14-cell grid, objects randomized on the tabletop; RViz (right): the identical scene in the MoveIt planning environment.*
<!-- Optional: ![Coverage summary](images/week9_coverage_terminal.png) -->
<!-- *Fig 2: Terminal coverage summary per base configuration.* -->

### 2.2 Results
| Test configuration | Verified placements | Key observation |
|---|---|---|
| Original base, 180° yaw | 11 / 14 | Three outer-right cells (~X = 0.967 m) rejected pre-execution. |
| Original base, 0° yaw | 11 / 14 | Same three failures: yaw rotates the workspace but does not expand radial reach. |
| Shifted base (0.186, 0.122) m | 13 / 13 eligible | Edge cells succeeded; one opposite-side cell excluded by the base-clearance rule. |

### 2.3 Finding: workcell layout optimization
The UR5e's nominal reach is 850 mm; the failing cells sit at the kinematic boundary. The two configurations are **complementary**: their union covers all 14 distinct cells, proving the software stack is capable everywhere and the limitation is purely geometric. A single static base pose cannot cover this grid without either dropping edge targets or violating base clearance — the classic fixed-base workcell trade-off, and the justification for treating base placement as an optimization variable (see §4.5).

## 3. Safety and Validation Integrity
All edge-cell failures were **pre-execution validation rejections** (IK/planner/validity checks at ~0.967 m). The robot never attempted an unreachable trajectory: the pipeline filters impossible poses before MuJoCo execution, guaranteeing zero unstable physical behavior during unattended runs.

---

## 4. Literature Review: Expert Algorithmic Approaches

### 4.1 Motion planning — sampling vs trajectory optimization
**Ours: OMPL RRT-Connect.** Probabilistically complete; benchmark evidence (MotionBenchMaker-style studies) shows RRT-Connect degrades gracefully under pose variation (e.g., 85%→76% success under shelf rotation) with consistent planning times. **Alternative: CHOMP/STOMP/TrajOpt** yield smoother industrial paths and better maintain normal alignment during approach, but are local optimizers that trap on poor seeds.

### 4.2 Inverse kinematics — analytical vs numerical
**Ours: multi-seed analytical/hybrid (TRAC-IK style).** Suction demands near-zero orientation tolerance; multiple seeds reliably converge near workspace boundaries. **Alternative: pure numerical (KDL Jacobian pseudoinverse)** oscillates or times out at boundaries and wrist singularities (J5 ≈ 0°) — unacceptable at the 0.967 m edge cells.

### 4.3 Coordinate paradigms — relative vs absolute
**Ours: object-centric relative poses.** The grasp frame is computed from the live object pose, so the suction approach vector always aligns with the local surface normal under any randomization. **Alternative: absolute world-frame hardcoding** breaks the moment the cell shifts or objects move.

### 4.4 Grasp execution — proximity weld vs force-torque feedback
**Ours: state-machine proximity weld in MuJoCo** (distance gate + normal alignment + `eq_active` flip inside `pre_step`). Efficient, deterministic vacuum surrogate. **Alternative: FTS pressure-drop feedback** is the physical truth on hardware but requires fluid-level modeling to simulate faithfully.

### 4.5 Advanced strategies for positional variability (from the deep-research survey)
- **Reachability inversion:** precompute the arm's reachable workspace and invert it to sample base poses (SE(2)) from which a grasp is achievable — directly applicable to our base-pose search.
- **Policy mobilization (Mobi-π):** given a policy trained at a fixed pose, score candidate robot poses in a new scene and optimize the start pose — a data-efficient alternative to retraining.
- **Augmented Kinematic Representation (AKR / SMMP):** treat base + arm + held object as one kinematic chain and plan jointly in the augmented space; reported 90–95% success on long-horizon tasks where decoupled planning fails.
- **Hybrid TAMP:** symbolic task sequencing + sampling-based motion planning + learned skills (e.g., RL decluttering) for cluttered scenes.

### Comparison matrix
| Dimension | Implemented | Expert alternative | Why our choice |
|---|---|---|---|
| Motion planner | OMPL RRT-Connect | CHOMP / STOMP | Guaranteed path finding across the grid; TrajOpt risks local minima |
| IK solver | Multi-seed analytical | Numerical KDL | No timeout/singularity failures at edge targets |
| Coordinates | Object-centric relative | Absolute world-frame | Normal alignment survives randomization |
| Grasp execution | State machine + weld | FTS feedback loop | Efficient, deterministic vacuum surrogate in sim |
| Base placement | Manual ablation (3 poses) | Reachability inversion / Mobi-π | Next step: automate the search (§7) |

---

## 5. Study Milestones (understanding each expert approach)
- **M1 — Planners:** how sampling builds C-space graphs; why RRT-Connect is probabilistically complete; where TrajOpt's local minima come from.
- **M2 — IK:** closed-form vs Jacobian pseudoinverse; wrist-singularity geometry of the UR5e; why seeds matter under orientation locks.
- **M3 — Frames:** object-centric vs world-frame math (`T_grasp^obj`); effect on suction normal alignment.
- **M4 — Grasp physics:** weld constraints vs contact/friction vs FTS; what each can and cannot prove.
- **M5 — Synthesis:** map each approach to our measured failure modes (edge-cell IK rejections, clearance exclusions) and decide what to adopt next.

## 6. Current Status
- ✅ Suction sequence integrated and exercised across all variation runs.
- ✅ 14-cell grid tested under three base configurations; coverage JSON saved per run.
- ✅ All 14 cells covered by the union of configurations.
- ✅ Pre-execution safety filter verified (zero physical attempts at unreachable poses).
- ✅ Literature review + comparison matrix drafted (this document).
- ⏳ Automated base-pose search and placement-error quantification (next).

## 7. Next Steps
1. Base-pose micro-grid search between (0,0) and (0.186, 0.122) m (informed by reachability-inversion ideas) for a single-sweep sweet spot.
2. Quantify placement error (ε_p, ε_θ) across validated cells.
3. Large-scale dataset collection with combined pickup+target randomization (manifest CSV).
4. Continue SOTA review (BC, ACT, Diffusion Policy, Open X-Embodiment) → Week 10 blog.

## 8. Known Limitations
- Suction is idealized (proximity weld): no slip, seal-loss, or fluid dynamics.
- Single static base cannot cover the full 14-cell grid (geometric, documented).
- Base-pose selection is still manual ablation, not optimized.

## Appendix A — Figures
| File | Section | Content |
|---|---|---|
| `images/week9_workcell_14cell.png` | 2.1 | 14-cell workcell in MuJoCo + RViz |
| `images/week9_coverage_terminal.png` (optional) | 2.2 | Coverage summary per configuration |

## Appendix B — Reproduce
```bash
ros2 launch ur5e_mujoco_moveit mujoco_moveit.launch.py
ros2 run vibe_version pick_place_relative --object yellow_box --episodes 10 --seed 27
