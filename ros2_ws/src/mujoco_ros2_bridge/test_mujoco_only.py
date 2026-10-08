import mujoco
import mujoco.viewer
import time

def test_mujoco():
    xml_path = "/home/ahmed/mujoco_menagerie/universal_robots_ur5e/scene.xml"
    print(f"Attempting to load model from: {xml_path}")
    try:
        model = mujoco.MjModel.from_xml_path(xml_path)
        data = mujoco.MjData(model)
        print("Model loaded successfully!")
        
        print("Launching viewer... (Close the window to exit)")
        with mujoco.viewer.launch_passive(model, data) as viewer:
            while viewer.is_running():
                mujoco.mj_step(model, data)
                viewer.sync()
                time.sleep(0.01)
    except Exception as e:
        print(f"MuJoCo Error: {e}")

if __name__ == "__main__":
    test_mujoco()
