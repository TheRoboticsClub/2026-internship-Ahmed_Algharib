---
title: "Week 1 — Gazebo Harmonic Environment and a Static-Scene Pipeline"
date: 2026-09-10 10:00:00 +0300
categories: [setup, gazebo]
tags: [gazebo, harmonic, ros2, environment]
---

## Goal

Set up the robotics simulation toolchain on Ubuntu 24.04, verify that Gazebo Harmonic works alongside ROS 2 Jazzy, and confirm that the end-to-end model-to-screen pipeline is functional before moving into the internship project scope.

## Getting Gazebo actually running

Three separate problems were hidden behind the same symptom: `gz sim` was not found.

1. **Wrong package source.** `gz-harmonic` is not available in Ubuntu 24.04's default archive because the release is newer than the Ubuntu package freeze. The fix was to add the OSRF repository and install from there.
2. **Binary shadowing.** Sourcing ROS 2 Jazzy can place a vendor `gz` binary earlier in `PATH`. That binary registers transport tools only, not the simulator itself. The simulator was installed the whole time; it was just hidden behind the wrong executable.
3. **Config path collision.** `GZ_CONFIG_PATH` was pointing to the vendor config-only registry. The fix was to use `alias gz='/usr/bin/gz'` and `unset GZ_CONFIG_PATH` at the end of `.bashrc` so the last setting wins.

The main lesson is simple: `type <command>` is the first real diagnostic in any shell. An identical error message can come from multiple root causes, and only the disk evidence can separate them.

## Proving the pipeline before loading real assets

Before touching any real industrial model, I verified the full pipeline with a minimal primitive box: `model.config` + `model.sdf` → `model://` URI → `GZ_SIM_RESOURCE_PATH` → render on screen.

![Static scene verification with a minimal Gazebo box]({{ '/assets/img/posts/vnc_pipeline_verification.png' | relative_url }})

Two issues showed up during this stage and were solved by validating the artifact itself before trusting the runtime.

- A truncated heredoc produced a corrupt world file. That was caught by inspecting the file with `tail` and checking the generated content before launch.
- `gz sdf -p` cannot resolve `model://` URIs because the standalone parser has no resource lookup callback. This showed that the simulator and the parser do not necessarily promise the same behavior when resource paths are involved.

## FBX → Blender → GLB → Gazebo

The conversion path needed a different workflow than older tutorials suggested.

- Blender 4.x on Ubuntu 24.04 no longer exposes Collada export in the same place as older tutorials imply. I checked the current Export menu directly instead of trusting a stale procedure. The target format became glTF Binary (`.glb`).
- A filename mismatch produced the same `Error Code 14` that appears when a model is missing. That was a separate cause of the same error code, which made the debugging process more subtle than expected.
- The first render was pitch black. After inspecting the glTF JSON directly, the materials were missing a `metallicFactor`, and the glTF spec defaults that value to `1.0`, meaning fully mirror-like metal. With no environment lighting, the result looked black. Changing the metallic factor to `0` fixed the issue.

![Gazebo black render before material correction]({{ '/assets/img/posts/gz_ogre1_black_screen.png' | relative_url }})

This is a good reminder that the most dangerous value in a file is often the one that is implicitly missing. Defaults can quietly produce misleading behavior.

## In progress

The source cell is now being decomposed into per-part models: arm, table, machine, carriers, and end effector. Each part is being checked separately for unit consistency and orientation before reconstruction in simulation.

The Unity source scene and the Blender inventory were cross-validated before conversion. That already revealed a useful structure: the arm has 7 links, while the machine geometry includes 11,951 objects. Those audits matter before any scene is exported to Gazebo.

## Lessons

1. Read the error text, run the evidence command, and only then form a theory.
2. Verify every artifact after writing it before using it in a simulation.
3. The most dangerous value in a file is the one that is not explicitly present.
4. Environment problems often masquerade as tool problems; check `type`, `PATH`, and config variables first.

## Takeaway

The most important result from Week 1 was not just “Gazebo installed,” but “the model-to-screen pipeline is trusted.” That foundation matters because the rest of the internship will depend on deterministic asset import and predictable simulation behavior, not only on a working toolchain.

![Gazebo terminal evidence during startup and debugging]({{ '/assets/img/posts/gz_ogre1_terminal_log.png' | relative_url }})
