#include <rclcpp/rclcpp.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <tf2_ros/transform_broadcaster.h>
#include <gazebo_msgs/msg/model_states.hpp>

#include <cmath>
#include <memory>
#include <string>

class GazeboOdomBridge : public rclcpp::Node
{
public:
  GazeboOdomBridge()
  : Node("gazebo_odom_bridge")
  {
    // ==================================================
    // Parameters
    // ==================================================
    model_name_  = declare_parameter<std::string>("model_name", "mega3");
    odom_frame_  = declare_parameter<std::string>("odom_frame", "odom");
    base_frame_  = declare_parameter<std::string>("base_frame", "base_footprint");
    publish_tf_  = declare_parameter<bool>("publish_tf", true);
    flatten_2d_  = declare_parameter<bool>("flatten_to_2d", true);
    cov_lin_     = declare_parameter<double>("cov_linear", 1e-3);
    cov_ang_     = declare_parameter<double>("cov_angular", 1e-3);

    // ==================================================
    // Publisher / TF broadcaster
    // ==================================================
    odom_pub_ =
      create_publisher<nav_msgs::msg::Odometry>(
        "/odom",
        rclcpp::QoS(10)
      );

    tf_broadcaster_ =
      std::make_unique<tf2_ros::TransformBroadcaster>(*this);

    // ==================================================
    // Subscriber
    // ==================================================
    sub_ = create_subscription<gazebo_msgs::msg::ModelStates>(
      "/model_states",
      rclcpp::QoS(10),
      std::bind(&GazeboOdomBridge::cb, this, std::placeholders::_1)
    );
  }

private:
  void cb(const gazebo_msgs::msg::ModelStates::SharedPtr msg)
  {
    // ==================================================
    // Find model index
    // ==================================================
    int model_index = -1;

    for (size_t i = 0; i < msg->name.size(); ++i) {
      if (msg->name[i] == model_name_) {
        model_index = static_cast<int>(i);
        break;
      }
    }

    if (model_index < 0) {
      RCLCPP_WARN_THROTTLE(
        get_logger(),
        *get_clock(),
        5000,
        "Model '%s' not found",
        model_name_.c_str()
      );
      return;
    }

    // ==================================================
    // Extract pose / twist
    // ==================================================
    const auto &pose  = msg->pose[model_index];
    const auto &twist = msg->twist[model_index];

    // ==================================================
    // Odometry message
    // ==================================================
    nav_msgs::msg::Odometry odom;
    odom.header.stamp    = now();
    odom.header.frame_id = odom_frame_;
    odom.child_frame_id  = base_frame_;
    odom.pose.pose       = pose;
    odom.twist.twist     = twist;

    // ==================================================
    // Flatten to 2D (optional)
    // ==================================================
    if (flatten_2d_) {
      odom.pose.pose.position.z      = 0.0;
      odom.twist.twist.linear.z      = 0.0;
      odom.twist.twist.angular.x     = 0.0;
      odom.twist.twist.angular.y     = 0.0;

      // Keep yaw only (roll/pitch = 0)
      const double siny_cosp =
        2.0 * (pose.orientation.w * pose.orientation.z +
               pose.orientation.x * pose.orientation.y);

      const double cosy_cosp =
        1.0 - 2.0 * (pose.orientation.y * pose.orientation.y +
                     pose.orientation.z * pose.orientation.z);

      const double yaw = std::atan2(siny_cosp, cosy_cosp);

      geometry_msgs::msg::Quaternion q;
      q.x = 0.0;
      q.y = 0.0;
      q.z = std::sin(yaw * 0.5);
      q.w = std::cos(yaw * 0.5);

      odom.pose.pose.orientation = q;
    }

    // ==================================================
    // Covariance
    // ==================================================
    for (int i = 0; i < 36; ++i) {
      odom.pose.covariance[i]  = 0.0;
      odom.twist.covariance[i] = 0.0;
    }

    odom.pose.covariance[0]  = cov_lin_;
    odom.pose.covariance[7]  = cov_lin_;
    odom.pose.covariance[35] = cov_ang_;

    odom.twist.covariance[0]  = cov_lin_;
    odom.twist.covariance[7]  = cov_lin_;
    odom.twist.covariance[35] = cov_ang_;

    // ==================================================
    // Publish odometry
    // ==================================================
    odom_pub_->publish(odom);

    // ==================================================
    // Publish TF (optional)
    // ==================================================
    if (publish_tf_) {
      geometry_msgs::msg::TransformStamped tf;
      tf.header            = odom.header;
      tf.child_frame_id    = base_frame_;
      tf.transform.translation.x = odom.pose.pose.position.x;
      tf.transform.translation.y = odom.pose.pose.position.y;
      tf.transform.translation.z = odom.pose.pose.position.z;
      tf.transform.rotation      = odom.pose.pose.orientation;

      tf_broadcaster_->sendTransform(tf);
    }
  }

  // ==================================================
  // Members
  // ==================================================
  std::string model_name_;
  std::string odom_frame_;
  std::string base_frame_;

  bool publish_tf_;
  bool flatten_2d_;

  double cov_lin_;
  double cov_ang_;

  rclcpp::Subscription<gazebo_msgs::msg::ModelStates>::SharedPtr sub_;
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
  std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
};

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<GazeboOdomBridge>());
  rclcpp::shutdown();
  return 0;
}

