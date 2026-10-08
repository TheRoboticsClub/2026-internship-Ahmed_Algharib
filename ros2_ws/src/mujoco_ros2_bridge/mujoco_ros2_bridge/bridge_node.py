import sys
import threading
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, Int32
import mujoco
import mujoco.viewer

sys.path.insert(0, "/home/ahmed/mujoco_pick_place")
from env_utils import reset_to_home, ARM_JOINTS, solve_reach, move_to_precise

class MuJoCoBridgeNode(Node):
    def __init__(self, model, data, lock):
        super().__init__('mujoco_ros2_bridge')
        self.model = model
        self.data = data
        self.lock = lock
        self.target_ctrl = np.array([0.0, -1.57, 1.57, -1.57, -1.57, 0.0])
        self.actuator_names = ['shoulder_pan', 'shoulder_lift', 'elbow', 'wrist_1', 'wrist_2', 'wrist_3']

        # ROS 2 Interfaces
        self.sub = self.create_subscription(
            Float64MultiArray, '/joint_commands', self.on_command, 10)
        self.pos_sub = self.create_subscription(
            Float64MultiArray, '/target_position', self.on_target_pos, 10)
        self.grip_sub = self.create_subscription(
            Int32, '/gripper', self.on_gripper, 10)
        self.pub = self.create_publisher(JointState, '/joint_states', 10)
        self.create_timer(0.02, self.publish_state)

    def on_command(self, msg):
        if len(msg.data) == 6:
            with self.lock:
                self.target_ctrl = np.array(msg.data)
            self.get_logger().info(f"Target Updated: {msg.data}")

    def on_target_pos(self, msg):
        if len(msg.data) == 3:
            target_pos = msg.data
            self.get_logger().info(f"Moving to Position: {target_pos}")
            # Offload to a separate thread to avoid blocking ROS executor
            threading.Thread(target=self.execute_move, args=(target_pos,)).start()

    def on_gripper(self, msg):
        # 1 = Close (Pick), 0 = Open (Place)
        with self.lock:
            for i in range(self.model.nlweld):
                # In scene.xml, welds 64-67 are the grasp welds
                # We activate them if gripper is 1
                self.data.eq_active[i] = bool(msg.data)
        self.get_logger().info(f"Gripper {'Closed' if msg.data == 1 else 'Open'}")

    def execute_move(self, target_pos):
        # Use the precise move function with collision avoidance for table and stand
        # This updates self.target_ctrl internally via data.ctrl
        move_to_precise(self.model, self.data, target_pos, 
                         avoid_body_names=("table", "stand_table"), 
                         steps=200)
        # Sync the updated data.ctrl back to our target_ctrl for the main loop
        # We assume the actuators match the order in ARM_JOINTS
        with self.lock:
            for i, act_name in enumerate(self.actuator_names):
                act_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, act_name)
                if act_id != -1:
                    self.target_ctrl[i] = self.data.ctrl[act_id]


    def publish_state(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = ARM_JOINTS
        with self.lock:
            msg.position = [
                self.data.qpos[self.model.jnt_qposadr[
                    mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, j)]]
                for j in ARM_JOINTS
            ]
        self.pub.publish(msg)

def main():
    rclpy.init()

    # Load Model and Data
    try:
        print("Loading MuJoCo model...")
        model = mujoco.MjModel.from_xml_path("/home/ahmed/mujoco_menagerie/universal_robots_ur5e/scene.xml")
        data = mujoco.MjData(model)
        
        # Check for 'home' keyframe to avoid crash in reset_to_home
        key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "home")
        if key_id == -1:
            print("Warning: 'home' keyframe not found. Skipping reset_to_home.")
        else:
            print("Resetting to home position...")
            reset_to_home(model, data)
            
        print("Model loaded and initialized successfully.")
    except Exception as e:
        print(f"Critical Error loading MuJoCo model: {e}")
        rclpy.shutdown()
        return
    lock = threading.Lock()

    # Create Node
    node = MuJoCoBridgeNode(model, data, lock)

    # 1. Run ROS 2 Executor in a BACKGROUND Thread
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    ros_thread = threading.Thread(target=executor.spin, daemon=True)
    ros_thread.start()

    # 2. Run MuJoCo Viewer and Physics loop on the MAIN Thread
    with mujoco.viewer.launch_passive(model, data) as viewer:
        while viewer.is_running() and rclpy.ok():
            step_start = time.time()

            with lock:
                # Apply targets to actuators
                for i, act_name in enumerate(node.actuator_names):
                    act_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, act_name)
                    if act_id != -1:
                        data.ctrl[act_id] = node.target_ctrl[i]
                        
                mujoco.mj_step(model, data)

            # Sync GUI visuals on main thread
            viewer.sync()

            # Maintain physics time step (~500Hz)
            time_until_next_step = model.opt.timestep - (time.time() - step_start)
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()