import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
import mujoco
import sys
sys.path.insert(0, "/home/ahmed/mujoco_pick_place")
from env_utils import reset_to_home, ARM_JOINTS

class MuJoCoROS2Bridge(Node):
    def __init__(self):
        super().__init__('mujoco_ros2_bridge')
        self.model = mujoco.MjModel.from_xml_path(
            "/home/ahmed/mujoco_menagerie/universal_robots_ur5e/scene.xml")
        self.data = mujoco.MjData(self.model)
        reset_to_home(self.model, self.data)
        self.sub = self.create_subscription(
            Float64MultiArray, '/joint_commands', self.on_command, 10)
        self.pub = self.create_publisher(JointState, '/joint_states', 10)
        self.create_timer(0.002, self.step_physics)
        self.create_timer(0.02, self.publish_state)

    def on_command(self, msg):
        self.data.ctrl[:] = msg.data

    def step_physics(self):
        mujoco.mj_step(self.model, self.data)

    def publish_state(self):
        msg = JointState()
        msg.name = ARM_JOINTS
        msg.position = [self.data.qpos[self.model.jnt_qposadr[
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, j)]]
            for j in ARM_JOINTS]
        self.pub.publish(msg)

def main():
    rclpy.init()
    node = MuJoCoROS2Bridge()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
