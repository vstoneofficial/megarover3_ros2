#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/joy.hpp"
#include "geometry_msgs/msg/twist.hpp"

using std::placeholders::_1;

class RoverGamepad : public rclcpp::Node
{
public:
  RoverGamepad() : Node("rover_gamepad"), last_time_(this->now())
  {
    // QoS設定（Gazebo互換: RELIABLE / VOLATILE）
    rclcpp::QoS qos(rclcpp::KeepLast(10));
    qos.reliability(RMW_QOS_POLICY_RELIABILITY_RELIABLE);
    qos.durability(RMW_QOS_POLICY_DURABILITY_VOLATILE);

    joy_sub_ = this->create_subscription<sensor_msgs::msg::Joy>(
      "joy", qos, std::bind(&RoverGamepad::joy_callback, this, _1));
    twist_pub_ = this->create_publisher<geometry_msgs::msg::Twist>("rover_twist", qos);

    // 100Hz周期でTwist出力
    timer_ = this->create_wall_timer(
      std::chrono::milliseconds(10),
      std::bind(&RoverGamepad::timer_callback, this));

    RCLCPP_INFO(this->get_logger(), "Rover Gamepad node started (Gazebo-compatible)");
  }

private:
  void joy_callback(const sensor_msgs::msg::Joy::SharedPtr msg)
  {
    std::lock_guard<std::mutex> lock(mutex_);
    last_time_ = this->now();

    // Reset previous command
    current_cmd_ = geometry_msgs::msg::Twist();

    // --- 軸番号・ボタン番号定義 ---
    const int AXIS_LEFT_X = 0;     // 左スティック左右
    const int AXIS_LEFT_Y = 1;     // 左スティック上下
    const int AXIS_DPAD_X = 6;     // 十字左右
    const int AXIS_DPAD_Y = 7;     // 十字上下

    const int BTN_SQUARE   = 3;    // □
    const int BTN_CROSS    = 0;    // ×
    const int BTN_CIRCLE   = 1;    // ○
    const int BTN_TRIANGLE = 2;    // △
    const int BTN_L1 = 4;
    const int BTN_R1 = 5;
    const int BTN_L2 = 6;
    const int BTN_R2 = 7;

    // --- 基本速度設定 ---
    double linear_speed  = 0.3;   // 十字・記号キー基準速度
    double angular_speed = 1.0;   // 十字・記号キー基準旋回速度

    // --- ショルダーボタンで最高速度切替 ---
    if (msg->buttons[BTN_L1]) { linear_speed = 0.8; angular_speed = 1.57; }
    if (msg->buttons[BTN_R1]) { linear_speed = 0.5; angular_speed = 1.04; }
    if (msg->buttons[BTN_L2]) { linear_speed = 1.5; angular_speed = 2.5; }
    if (msg->buttons[BTN_R2]) { linear_speed = 1.0; angular_speed = 2.10; }

    // --- 記号ボタン操作 ---
    if (msg->buttons[BTN_TRIANGLE]) current_cmd_.linear.x  += linear_speed;   // △: 前進
    if (msg->buttons[BTN_CROSS])    current_cmd_.linear.x  -= linear_speed;   // ×: 後進
    if (msg->buttons[BTN_SQUARE])   current_cmd_.angular.z += angular_speed;  // □: 左旋回
    if (msg->buttons[BTN_CIRCLE])   current_cmd_.angular.z -= angular_speed;  // ○: 右旋回

    // --- 十字キー操作 ---
    if (msg->axes[AXIS_DPAD_Y] > 0.5) current_cmd_.linear.x  += linear_speed;  // 十字上
    if (msg->axes[AXIS_DPAD_Y] < -0.5) current_cmd_.linear.x -= linear_speed;  // 十字下
    if (msg->axes[AXIS_DPAD_X] < -0.5) current_cmd_.angular.z -= angular_speed; // 十字左
    if (msg->axes[AXIS_DPAD_X] > 0.5) current_cmd_.angular.z += angular_speed; // 十字右

    // --- アナログスティック操作 ---
    bool stick_active = false;
    if (msg->buttons[BTN_L1] || msg->buttons[BTN_L2] || msg->buttons[BTN_R1] || msg->buttons[BTN_R2]) {
      current_cmd_.linear.x  = msg->axes[AXIS_LEFT_Y] * linear_speed;
      current_cmd_.angular.z = msg->axes[AXIS_LEFT_X] * angular_speed;
      stick_active = true;
    }

    // --- 出力を安全に確保 ---
    if (!stick_active && current_cmd_.linear.x == 0.0 && current_cmd_.angular.z == 0.0) {
      // 入力が無い場合 → 停止命令
      current_cmd_.linear.x = 0.0;
      current_cmd_.angular.z = 0.0;
    }

    // デバッグ表示（軽量化済）
    std::string pressed;
    if (msg->buttons[BTN_TRIANGLE]) pressed += "△ ";
    if (msg->buttons[BTN_CIRCLE])   pressed += "○ ";
    if (msg->buttons[BTN_SQUARE])   pressed += "□ ";
    if (msg->buttons[BTN_CROSS])    pressed += "× ";
    if (msg->axes[AXIS_DPAD_Y] > 0.5) pressed += "↑ ";
    if (msg->axes[AXIS_DPAD_Y] < -0.5) pressed += "↓ ";
    if (msg->axes[AXIS_DPAD_X] < -0.5) pressed += "← ";
    if (msg->axes[AXIS_DPAD_X] > 0.5) pressed += "→ ";
    
  }

  void timer_callback()
  {
    std::lock_guard<std::mutex> lock(mutex_);

    // 安全停止: 一定時間入力がなければ停止
    rclcpp::Time now = this->now();
    if ((now - last_time_).seconds() > 1.0) {
      current_cmd_.linear.x = 0.0;
      current_cmd_.angular.z = 0.0;
    }

    twist_pub_->publish(current_cmd_);
  }

  rclcpp::Subscription<sensor_msgs::msg::Joy>::SharedPtr joy_sub_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr twist_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
  geometry_msgs::msg::Twist current_cmd_;
  rclcpp::Time last_time_;
  std::mutex mutex_;
};

int main(int argc, char *argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<RoverGamepad>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}

