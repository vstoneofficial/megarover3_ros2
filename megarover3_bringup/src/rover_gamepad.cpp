#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/joy.hpp"
#include "geometry_msgs/msg/twist.hpp"

#include <cmath>
#include <mutex>

using std::placeholders::_1;

class RoverGamepad : public rclcpp::Node
{
public:
  RoverGamepad()
  : Node("rover_gamepad"),
    last_time_(this->now())
  {
    rclcpp::QoS qos(rclcpp::KeepLast(10));
    qos.reliability(RMW_QOS_POLICY_RELIABILITY_RELIABLE);
    qos.durability(RMW_QOS_POLICY_DURABILITY_VOLATILE);

    joy_sub_ = this->create_subscription<sensor_msgs::msg::Joy>(
      "joy",
      qos,
      std::bind(&RoverGamepad::joy_callback, this, _1)
    );

    twist_pub_ =
      this->create_publisher<geometry_msgs::msg::Twist>(
        "rover_twist",
        qos
      );

    timer_ = this->create_wall_timer(
      std::chrono::milliseconds(10),
      std::bind(&RoverGamepad::timer_callback, this)
    );

    RCLCPP_INFO(this->get_logger(), "Rover Gamepad node started");
  }

private:
  void joy_callback(const sensor_msgs::msg::Joy::SharedPtr msg)
  {
    std::lock_guard<std::mutex> lock(mutex_);
    last_time_ = this->now();

    current_cmd_ = geometry_msgs::msg::Twist();

    // ==================================================
    // Axis definitions
    // ==================================================
    const int AXIS_LEFT_X   = 0;
    const int AXIS_LEFT_Y   = 1;
    const int AXIS_RIGHT_X  = 3;
    const int AXIS_RIGHT_Y  = 4;
    const int AXIS_DPAD_X   = 6;
    const int AXIS_DPAD_Y   = 7;

    // ==================================================
    // Button definitions
    // ==================================================
    const int BTN_CROSS     = 0;
    const int BTN_CIRCLE   = 1;
    const int BTN_TRIANGLE = 2;
    const int BTN_SQUARE   = 3;
    const int BTN_L1       = 4;
    const int BTN_R1       = 5;
    const int BTN_L2       = 6;
    const int BTN_R2       = 7;

    // ==================================================
    // Fixed speeds (independent of L/R)
    // ==================================================
    // Symbol buttons: fine control
    const double SYMBOL_LINEAR_SPEED  = 0.1;
    const double SYMBOL_ANGULAR_SPEED = 0.1;

    // D-pad: normal control
    const double DPAD_LINEAR_SPEED  = 0.3;
    const double DPAD_ANGULAR_SPEED = 0.3;

    // ==================================================
    // Stick enable condition (L/R must be pressed)
    // ==================================================
    const bool stick_enabled =
      msg->buttons[BTN_L1] ||
      msg->buttons[BTN_R1] ||
      msg->buttons[BTN_L2] ||
      msg->buttons[BTN_R2];

    // ==================================================
    // Stick speed (affected by L/R)
    // ==================================================
    double stick_linear_speed  = 0.0;
    double stick_angular_speed = 0.0;

    if (msg->buttons[BTN_L1]) {
      stick_linear_speed  = 0.8;
      stick_angular_speed = 1.57;
    }
    if (msg->buttons[BTN_R1]) {
      stick_linear_speed  = 0.5;
      stick_angular_speed = 1.04;
    }
    if (msg->buttons[BTN_L2]) {
      stick_linear_speed  = 1.5;
      stick_angular_speed = 2.5;
    }
    if (msg->buttons[BTN_R2]) {
      stick_linear_speed  = 1.0;
      stick_angular_speed = 2.10;
    }

    // ==================================================
    // Symbol buttons (low speed)
    // ==================================================
    if (msg->buttons[BTN_TRIANGLE]) {
      current_cmd_.linear.x += SYMBOL_LINEAR_SPEED;
    }
    if (msg->buttons[BTN_CROSS]) {
      current_cmd_.linear.x -= SYMBOL_LINEAR_SPEED;
    }
    if (msg->buttons[BTN_SQUARE]) {
      current_cmd_.angular.z += SYMBOL_ANGULAR_SPEED;
    }
    if (msg->buttons[BTN_CIRCLE]) {
      current_cmd_.angular.z -= SYMBOL_ANGULAR_SPEED;
    }

    // ==================================================
    // D-pad (medium speed)
    // ==================================================
    if (msg->axes[AXIS_DPAD_Y] >  0.5) {
      current_cmd_.linear.x += DPAD_LINEAR_SPEED;
    }
    if (msg->axes[AXIS_DPAD_Y] < -0.5) {
      current_cmd_.linear.x -= DPAD_LINEAR_SPEED;
    }
    if (msg->axes[AXIS_DPAD_X] >  0.5) {
      current_cmd_.angular.z += DPAD_ANGULAR_SPEED;
    }
    if (msg->axes[AXIS_DPAD_X] < -0.5) {
      current_cmd_.angular.z -= DPAD_ANGULAR_SPEED;
    }

    // ==================================================
    // Analog sticks (L/R enabled only)
    // ==================================================
    if (stick_enabled) {
      const double deadzone = 0.05;

      const double lx =
        (std::fabs(msg->axes[AXIS_LEFT_X]) > deadzone) ? msg->axes[AXIS_LEFT_X] : 0.0;
      const double ly =
        (std::fabs(msg->axes[AXIS_LEFT_Y]) > deadzone) ? msg->axes[AXIS_LEFT_Y] : 0.0;
      const double rx =
        (std::fabs(msg->axes[AXIS_RIGHT_X]) > deadzone) ? msg->axes[AXIS_RIGHT_X] : 0.0;
      const double ry =
        (std::fabs(msg->axes[AXIS_RIGHT_Y]) > deadzone) ? msg->axes[AXIS_RIGHT_Y] : 0.0;

      double combined_linear  = ly + ry;
      double combined_angular = lx + rx;

      combined_linear  = std::max(-1.0, std::min(1.0, combined_linear));
      combined_angular = std::max(-1.0, std::min(1.0, combined_angular));

      current_cmd_.linear.x  += combined_linear  * stick_linear_speed;
      current_cmd_.angular.z += combined_angular * stick_angular_speed;
    }
  }

  void timer_callback()
  {
    std::lock_guard<std::mutex> lock(mutex_);

    const rclcpp::Time now = this->now();
    if ((now - last_time_).seconds() > 1.0) {
      current_cmd_.linear.x  = 0.0;
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
  rclcpp::spin(std::make_shared<RoverGamepad>());
  rclcpp::shutdown();
  return 0;
}

