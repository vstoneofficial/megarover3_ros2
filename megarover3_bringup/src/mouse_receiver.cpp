#include <chrono>
#include <functional>
#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"


using std::placeholders::_1;
using namespace std::chrono_literals;

class MouseReceiverNode : public rclcpp::Node
{
public:
  MouseReceiverNode()
  : Node("mouse_receiver")
  {
    publisher_ = this->create_publisher<geometry_msgs::msg::Twist>("rover_twist", rclcpp::QoS(1));

    // publish odometry data and tf transform every 50ms (=20hz)
    timer_ = this->create_wall_timer(
      50ms, std::bind(&MouseReceiverNode::timer_callback, this));

    subscription_ = this->create_subscription<geometry_msgs::msg::Twist>(
      "mouse_vel", rclcpp::SensorDataQoS(), std::bind(&MouseReceiverNode::mouse_callback, this, _1));

  }
  
private:
  void timer_callback()
  {
    auto msg = geometry_msgs::msg::Twist();
    
    msg.linear.x = v_x;
    msg.linear.y = v_y;
    msg.angular.z = v_z;
    
    publisher_->publish(msg);
  }
  
  void mouse_callback(const std::shared_ptr<geometry_msgs::msg::Twist> msg)
  {
    v_x = msg->linear.x;
    v_y = msg->linear.y;
    v_z = msg->angular.z;
    
  }
  
  double v_x;
  double v_y;
  double v_z;
  
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr publisher_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr subscription_;
  rclcpp::TimerBase::SharedPtr timer_;
  
};


int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<MouseReceiverNode>());
  rclcpp::shutdown();
  return 0;
}


