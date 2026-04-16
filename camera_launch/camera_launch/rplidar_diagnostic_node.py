import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from diagnostic_updater import Updater, HeaderlessTopicDiagnostic, FrequencyStatusParam

class RPLIDARDiagnosticNode(Node):
    def __init__(self):
        super().__init__('rplidar_diagnostic_node')
        
        # Parameters
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('expected_hz', 10.0)
        
        scan_topic = self.get_parameter('scan_topic').value
        expected_hz = self.get_parameter('expected_hz').value
        
        # Diagnostic Updater
        self.updater = Updater(self)
        self.updater.setHardwareID("RPLIDAR_C1")
        
        # Frequency Status Parameters
        # RP Lidar C1 usually runs at 10Hz
        min_freq = expected_hz * 0.7
        max_freq = expected_hz * 1.3
        
        # FrequencyStatusParam({'min': min, 'max': max}, tolerance, window_size)
        fps_param = FrequencyStatusParam({'min': min_freq, 'max': max_freq}, 0.1, 10)
        
        # Topic Diagnostic
        self.topic_diag = HeaderlessTopicDiagnostic(
            scan_topic,
            self.updater,
            fps_param
        )
        
        # Subscriber to trigger diagnostic
        self.sub = self.create_subscription(
            LaserScan,
            scan_topic,
            self.scan_callback,
            10
        )
        
        self.get_logger().info(f"RPLIDAR Diagnostic Node started monitoring {scan_topic} at {expected_hz} Hz")

    def scan_callback(self, msg):
        self.topic_diag.tick()

def main(args=None):
    rclpy.init(args=args)
    node = RPLIDARDiagnosticNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
