import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class TestNode(Node):
    def __init__(self):
        super().__init__('test_node')
        self.pub = self.create_publisher(String, 'test_topic', 10)
        self.sub = self.create_subscription(String, 'test_topic', self.callback, 10)
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.get_logger().info("Test Node started. Publishing to 'test_topic'...")

    def timer_callback(self):
        msg = String()
        msg.data = 'Hello ROS 2!'
        self.pub.publish(msg)
        self.get_logger().info('Publishing: "Hello ROS 2!"')

    def callback(self, msg):
        self.get_logger().info(f'Received: "{msg.data}"')

def main():
    rclpy.init()
    node = TestNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
