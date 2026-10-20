#!/usr/bin/python3
# Copyright 2020, EAIBOT
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import LifecycleNode
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.parameter_descriptions import ParameterValue

import os


def launch_setup(context):
    parameters = [LaunchConfiguration('params_file')]
    lidar_port = LaunchConfiguration('lidar_port').perform(context)
    if lidar_port:
        parameters.append({'port': ParameterValue(lidar_port, value_type=str)})
    driver_node = LifecycleNode(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='ydlidar_ros2_driver_node',
        output='screen',
        emulate_tty=True,
        parameters=parameters,
        namespace='/',
    )
    tf2_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_pub_laser',
        arguments=['0', '0', '0', '0', '0', '0', '1', 'base_link', 'laser_frame'],
    )

    return [
        driver_node,
        tf2_node,  # Also published by the description launch file.
    ]


def generate_launch_description():
    megarover3_bringup_share_dir = get_package_share_directory('megarover3_bringup')
    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(megarover3_bringup_share_dir, 'params', 'TG30.yaml'),
            description='Path to the ROS2 parameters file to use.',
        ),
        DeclareLaunchArgument(
            'lidar_port',
            default_value='',
            description='Override the TG30 serial port; empty uses the parameter file.',
        ),
        OpaqueFunction(function=launch_setup),
    ])
