import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Quaternion
from nav_msgs.msg import Odometry
import serial
from cobs import cobs
import struct
import crc8
import math

MAX_SIZE = 512  # 最大受信可能サイズ

class SerialSenderReceiver(Node):

    def __init__(self):
        super().__init__('serial_sender_receiver')

        # パラメータの宣言
        self.declare_parameter('serial_port', '/dev/esp32_usb_serial')
        self.declare_parameter('wheel_radius', 0.0473)  # 車輪の半径 (m)
        self.declare_parameter('wheel_separation', 0.1796)  # 車輪間の距離 (m)
        self.declare_parameter('max_rpm', 200)  # モータの最大回転数

        # パラメータの取得
        serial_port = self.get_parameter('serial_port').get_parameter_value().string_value
        wheel_radius = self.get_parameter('wheel_radius').get_parameter_value().double_value
        wheel_separation = self.get_parameter('wheel_separation').get_parameter_value().double_value
        max_rpm = self.get_parameter('max_rpm').get_parameter_value().integer_value

        # シリアルポートの設定
        self.ser = serial.Serial(serial_port, 115200, timeout=1)  # 送受信用シリアルポート

        self.subscription = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10
        )
        
        self.odom_publisher = self.create_publisher(Odometry, 'odom', 10)  # Odometryのパブリッシャー
        self.timer = self.create_timer(0.1, self.read_serial_data)  # タイマー設定

        # インスタンス変数として保持
        self.wheel_radius = wheel_radius
        self.wheel_separation = wheel_separation
        self.max_rpm = max_rpm
        self.buffer = bytearray()

        # ロボットの状態
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        # 前回の時間
        self.last_time = self.get_clock().now()

    def cmd_vel_callback(self, msg):
        linear_velocity = msg.linear.x
        angular_velocity = msg.angular.z

        # 左右の車輪の回転速度を計算
        v_r = linear_velocity - (angular_velocity * self.wheel_separation / 2)
        v_l = linear_velocity + (angular_velocity * self.wheel_separation / 2)

        # 回転速度をRPMに変換
        rpm_r = int((v_r / (2 * 3.1416 * self.wheel_radius)) * 60)
        rpm_l = int((v_l / (2 * 3.1416 * self.wheel_radius)) * 60)

        # RPMを最大値に制限
        rpm_r = max(min(rpm_r, self.max_rpm), -self.max_rpm)
        rpm_l = max(min(rpm_l, self.max_rpm), -self.max_rpm)

        # データをバイナリフォーマットにパック
        data = struct.pack('<hh', rpm_l, rpm_r)

        # CRC8を計算
        crc = self.calculate_crc8(data)

        # データにCRCを追加
        data_with_crc = data + bytes([crc])

        # COBSエンコード
        encoded_data = cobs.encode(data_with_crc)

        # 終端バイトを追加
        encoded_data += b'\x00'

        # シリアルポートに送信
        self.ser.write(encoded_data)
        self.get_logger().info(f'Sent RPM values: left={rpm_l}, right={rpm_r}')

    def read_serial_data(self):
        while self.ser.in_waiting > 0:
            data = self.ser.read(1)
            if data == b'\x00':  # 終端バイトに達した場合
                self.process_packet(self.buffer)
                self.buffer.clear()
            else:
                self.buffer.append(data[0])
                if len(self.buffer) > MAX_SIZE:
                    self.get_logger().error('Buffer overflow')
                    self.buffer.clear()

    def process_packet(self, data):
        try:
            decoded_data = cobs.decode(data)
            if len(decoded_data) == 5:  # 2 * int16_t (4バイト) + CRC (1バイト)
                received_crc = decoded_data[-1]
                data_without_crc = decoded_data[:-1]
                calculated_crc = self.calculate_crc8(data_without_crc)
                if received_crc == calculated_crc:
                    # 回転数をデコードして右の回転数を反転
                    rpm_l, rpm_r = struct.unpack('<hh', data_without_crc)
                    rpm_r = -rpm_r  # 右の回転数を反転

                    self.get_logger().info(f'Received values: left={rpm_l}, right={rpm_r}')
                    self.publish_odometry(rpm_l, rpm_r)
                else:
                    self.get_logger().error('CRC mismatch')
            else:
                self.get_logger().error('Received data length is incorrect')
        except cobs.DecodeError as e:
            self.get_logger().error(f'Decode error: {e}')

    def publish_odometry(self, rpm_l, rpm_r):
        # 現在の時間を取得
        current_time = self.get_clock().now()

        # RPMをm/sに変換
        v_l = (rpm_l / 60.0) * (2 * math.pi * self.wheel_radius)
        v_r = (rpm_r / 60.0) * (2 * math.pi * self.wheel_radius)

        # ロボットの速度を計算
        linear_velocity = (v_r + v_l) / 2
        angular_velocity = (v_r - v_l) / self.wheel_separation

        # 経過時間を計算
        dt = (current_time - self.last_time).nanoseconds / 1e9

        # ロボットの位置を更新
        self.x += linear_velocity * math.cos(self.theta) * dt
        self.y += linear_velocity * math.sin(self.theta) * dt
        self.theta += angular_velocity * dt

        # Odometryメッセージを作成
        odom_msg = Odometry()
        odom_msg.header.stamp = current_time.to_msg()
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = 'base_link'

        # ポジションの設定
        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.position.z = 0.0

        # クォータニオンに変換
        odom_quat = self.yaw_to_quaternion(self.theta)
        odom_msg.pose.pose.orientation = odom_quat

        # ツイストの設定
        odom_msg.twist.twist.linear.x = linear_velocity
        odom_msg.twist.twist.linear.y = 0.0
        odom_msg.twist.twist.angular.z = angular_velocity

        # Odometryをパブリッシュ
        self.odom_publisher.publish(odom_msg)

        # 前回の時間を更新
        self.last_time = current_time

    def yaw_to_quaternion(self, yaw):
        """ ヨー角からクォータニオンを生成 """
        half_yaw = yaw / 2.0
        q = Quaternion()
        q.z = math.sin(half_yaw)
        q.w = math.cos(half_yaw)
        return q

    def calculate_crc8(self, data):
        hash = crc8.crc8()
        hash.update(data)
        return hash.digest()[0]

def main(args=None):
    rclpy.init(args=args)
    serial_sender_receiver = SerialSenderReceiver()
    rclpy.spin(serial_sender_receiver)
    serial_sender_receiver.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
