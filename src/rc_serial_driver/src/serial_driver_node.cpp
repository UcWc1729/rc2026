#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <std_msgs/msg/float32.hpp>
#include "rm_serial_driver/serial_port.hpp"
#include "rm_serial_driver/protocol.hpp"
#include <cstring>
#include <cmath>
#include <vector>

namespace rm_serial_driver
{

class SerialDriverNode : public rclcpp::Node
{
public:
  SerialDriverNode()
  : Node("serial_driver_node")
  {
    // 声明参数
    this->declare_parameter<std::string>("port_name", "/dev/ttyUSB0");
    this->declare_parameter<int>("baudrate", 115200);
    this->declare_parameter<std::string>("cmd_vel_topic", "/cmd_vel");
    this->declare_parameter<double>("max_linear_vel", 1.0);
    this->declare_parameter<double>("max_angular_vel", 1.0);
    this->declare_parameter<double>("timeout", 0.1);  // 超时时间（秒）
    this->declare_parameter<bool>("publish_odom", true);  // 是否发布里程计
    this->declare_parameter<std::string>("odom_topic", "/odom_serial");  // 里程计话题

    // 获取参数
    std::string port_name = this->get_parameter("port_name").as_string();
    int baudrate = this->get_parameter("baudrate").as_int();
    std::string cmd_vel_topic = this->get_parameter("cmd_vel_topic").as_string();
    max_linear_vel_ = this->get_parameter("max_linear_vel").as_double();
    max_angular_vel_ = this->get_parameter("max_angular_vel").as_double();
    timeout_ = this->get_parameter("timeout").as_double();
    bool publish_odom = this->get_parameter("publish_odom").as_bool();
    std::string odom_topic = this->get_parameter("odom_topic").as_string();

    // 打开串口
    if (!serial_port_.open(port_name, baudrate)) {
      RCLCPP_ERROR(this->get_logger(), "Failed to open serial port: %s", port_name.c_str());
      return;
    }
    RCLCPP_INFO(this->get_logger(), "Serial port opened: %s at %d baud", port_name.c_str(), baudrate);

    // 初始化序列号
    tx_seq_ = 0;

    // 创建订阅者
    cmd_vel_sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
      cmd_vel_topic,
      10,
      std::bind(&SerialDriverNode::cmdVelCallback, this, std::placeholders::_1)
    );

    // 创建里程计发布者（如果启用）
    if (publish_odom) {
      odom_pub_ = this->create_publisher<nav_msgs::msg::Odometry>(odom_topic, 10);
    }

    // 创建定时器，用于超时检测和读取反馈
    timeout_timer_ = this->create_wall_timer(
      std::chrono::milliseconds(static_cast<int>(timeout_ * 1000)),
      std::bind(&SerialDriverNode::timeoutCallback, this)
    );

    // 创建定时器，用于读取下位机反馈（50Hz）
    feedback_timer_ = this->create_wall_timer(
      std::chrono::milliseconds(20),
      std::bind(&SerialDriverNode::readFeedback, this)
    );

    last_cmd_time_ = this->now();
    RCLCPP_INFO(this->get_logger(), "Serial driver node initialized");
  }

  ~SerialDriverNode()
  {
    // 发送停止指令
    sendStopCommand();
    serial_port_.close();
  }

private:
  void cmdVelCallback(const geometry_msgs::msg::Twist::SharedPtr msg)
  {
    last_cmd_time_ = this->now();

    // 限制速度范围
    double vx = std::max(-max_linear_vel_, std::min(msg->linear.x, max_linear_vel_));
    double vy = std::max(-max_linear_vel_, std::min(msg->linear.y, max_linear_vel_));
    double vtheta = std::max(-max_angular_vel_, std::min(msg->angular.z, max_angular_vel_));

    // 发送速度指令
    sendChassisSpeedCommand(vx, vy, vtheta);
  }

  void timeoutCallback()
  {
    // 检查是否超时
    auto elapsed = (this->now() - last_cmd_time_).seconds();
    if (elapsed > timeout_) {
      // 超时，发送停止指令
      sendStopCommand();
    }
  }

  void sendChassisSpeedCommand(double vx, double vy, double vtheta)
  {
    // 按照协议文档201-205行定义的ChassisSpeedCmd结构发送
    // CMD_CHASSIS_SPEED (0x0101)
    // typedef struct {
    //     float vx;       // 前进速度 (m/s) [-5.0, 5.0]
    //     float vy;       // 横向速度 (m/s) [-5.0, 5.0] (仅全向轮)
    //     float wz;       // 旋转角速度 (rad/s) [-3.14, 3.14]
    // } ChassisSpeedCmd;
    // 数据长度: 12字节 (3个float，各4字节)
    
    uint8_t data[12];
    float vx_f = static_cast<float>(vx);      // 前进速度 (m/s)
    float vy_f = static_cast<float>(vy);      // 横向速度 (m/s)
    float wz_f = static_cast<float>(vtheta);   // 旋转角速度 (rad/s)，对应协议中的wz
    
    // 按照协议结构顺序打包：vx, vy, wz (小端序)
    memcpy(&data[0], &vx_f, 4);   // vx: 字节0-3
    memcpy(&data[4], &vy_f, 4);   // vy: 字节4-7
    memcpy(&data[8], &wz_f, 4);   // wz: 字节8-11
    
    // 打包帧
    uint8_t frame_buffer[128];
    uint16_t frame_len = packFrame(
      CmdID::CHASSIS_SPEED,
      data,
      12,
      tx_seq_,
      frame_buffer
    );
    
    if (frame_len > 0) {
      // 发送数据
      int bytes_sent = serial_port_.write(frame_buffer, frame_len);
      if (bytes_sent != static_cast<int>(frame_len)) {
        RCLCPP_WARN_THROTTLE(
          this->get_logger(), *this->get_clock(), 1000,
          "Failed to send complete frame. Sent %d/%d bytes", bytes_sent, frame_len);
      } else {
        // 序列号自增（0-255循环）
        tx_seq_ = (tx_seq_ + 1) % 256;
      }
    } else {
      RCLCPP_ERROR(this->get_logger(), "Failed to pack frame");
    }
  }

  void sendStopCommand()
  {
    sendChassisSpeedCommand(0.0, 0.0, 0.0);
  }

  void readFeedback()
  {
    // 读取串口数据
    uint8_t read_buffer[256];
    int bytes_read = serial_port_.read(read_buffer, sizeof(read_buffer));
    
    if (bytes_read > 0) {
      // 将数据添加到接收缓冲区
      rx_buffer_.insert(rx_buffer_.end(), read_buffer, read_buffer + bytes_read);
      
      // 尝试解析帧
      while (rx_buffer_.size() >= FRAME_MIN_LEN) {
        // 查找帧头
        auto sof_pos = std::find(rx_buffer_.begin(), rx_buffer_.end(), FRAME_HEADER_SOF);
        if (sof_pos == rx_buffer_.end()) {
          // 没有找到帧头，清空缓冲区
          rx_buffer_.clear();
          break;
        }
        
        // 移除帧头之前的数据
        rx_buffer_.erase(rx_buffer_.begin(), sof_pos);
        
        // 检查是否有足够的数据
        if (rx_buffer_.size() < FRAME_MIN_LEN) {
          break;
        }
        
        // 尝试解析帧头以获取长度
        FrameHeader * header = reinterpret_cast<FrameHeader *>(rx_buffer_.data());
        uint16_t expected_len = 5 + header->data_length + 2;
        
        if (rx_buffer_.size() < expected_len) {
          // 数据不完整，等待更多数据
          break;
        }
        
        // 解析帧
        uint16_t cmd_id;
        const uint8_t * data;
        uint16_t data_len;
        uint8_t seq;
        
        if (parseFrame(rx_buffer_.data(), expected_len, &cmd_id, &data, &data_len, &seq)) {
          // 解析成功，处理数据
          handleFeedback(cmd_id, data, data_len);
          
          // 移除已处理的数据
          rx_buffer_.erase(rx_buffer_.begin(), rx_buffer_.begin() + expected_len);
        } else {
          // 解析失败，移除帧头，继续查找下一个帧头
          rx_buffer_.erase(rx_buffer_.begin());
        }
      }
      
      // 限制缓冲区大小，防止无限增长
      if (rx_buffer_.size() > 512) {
        rx_buffer_.clear();
        RCLCPP_WARN(this->get_logger(), "RX buffer overflow, cleared");
      }
    }
  }

  void handleFeedback(uint16_t cmd_id, const uint8_t * data, uint16_t data_len)
  {
    switch (cmd_id) {
      case CmdID::CHASSIS_FEEDBACK: {
        // 解析底盘反馈数据 (33字节)
        if (data_len == 33 && odom_pub_ != nullptr) {
          publishChassisFeedback(data);
        }
        break;
      }
      
      case CmdID::CHASSIS_ODOM: {
        // 解析里程计数据
        if (odom_pub_ != nullptr) {
          publishOdom(data, data_len);
        }
        break;
      }
      
      case CmdID::SYSTEM_STATUS: {
        // 解析系统状态
        RCLCPP_DEBUG(this->get_logger(), "Received system status");
        break;
      }
      
      default:
        RCLCPP_DEBUG(this->get_logger(), "Received unknown command: 0x%04X", cmd_id);
        break;
    }
  }

  void publishChassisFeedback(const uint8_t * data)
  {
    // 解析ChassisFeedback结构 (33字节)
    // uint32_t timestamp, float pos_x, float pos_y, float yaw,
    // float vel_x, float vel_y, float ang_vel, uint8_t status
    
    uint32_t timestamp;
    float pos_x, pos_y, yaw;
    float vel_x, vel_y, ang_vel;
    uint8_t status;
    
    memcpy(&timestamp, &data[0], 4);
    memcpy(&pos_x, &data[4], 4);
    memcpy(&pos_y, &data[8], 4);
    memcpy(&yaw, &data[12], 4);
    memcpy(&vel_x, &data[16], 4);
    memcpy(&vel_y, &data[20], 4);
    memcpy(&ang_vel, &data[24], 4);
    memcpy(&status, &data[32], 1);
    
    // 发布里程计
    auto odom_msg = nav_msgs::msg::Odometry();
    odom_msg.header.stamp = this->now();
    odom_msg.header.frame_id = "odom";
    odom_msg.child_frame_id = "base_link";
    
    odom_msg.pose.pose.position.x = pos_x;
    odom_msg.pose.pose.position.y = pos_y;
    odom_msg.pose.pose.position.z = 0.0;
    
    // 将yaw转换为四元数
    double cy = cos(yaw * 0.5);
    double sy = sin(yaw * 0.5);
    odom_msg.pose.pose.orientation.w = cy;
    odom_msg.pose.pose.orientation.x = 0.0;
    odom_msg.pose.pose.orientation.y = 0.0;
    odom_msg.pose.pose.orientation.z = sy;
    
    odom_msg.twist.twist.linear.x = vel_x;
    odom_msg.twist.twist.linear.y = vel_y;
    odom_msg.twist.twist.angular.z = ang_vel;
    
    odom_pub_->publish(odom_msg);
  }

  void publishOdom(const uint8_t * data, uint16_t data_len)
  {
    // 根据实际数据格式解析里程计
    // 这里可以根据协议文档中的CMD_CHASSIS_ODOM格式实现
    (void)data;  // 暂时未使用，避免编译警告
    RCLCPP_DEBUG(this->get_logger(), "Received odom data, length: %d", data_len);
  }

  SerialPort serial_port_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
  rclcpp::TimerBase::SharedPtr timeout_timer_;
  rclcpp::TimerBase::SharedPtr feedback_timer_;

  double max_linear_vel_;
  double max_angular_vel_;
  double timeout_;
  rclcpp::Time last_cmd_time_;
  
  uint8_t tx_seq_;  // 发送序列号
  std::vector<uint8_t> rx_buffer_;  // 接收缓冲区
};

}  // namespace rm_serial_driver

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rm_serial_driver::SerialDriverNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
