from ament_index_python.packages import get_package_share_path, get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue

from launch.launch_description_sources import PythonLaunchDescriptionSource

import os


def generate_launch_description():
    default_rviz_config_path = get_package_share_path('megarover3_navigation') / 'rviz/gmapping.rviz'
    rviz_arg = DeclareLaunchArgument(name='rvizconfig', default_value=str(default_rviz_config_path),
                                     description='Absolute path to rviz config file')

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('rvizconfig')],
    )

    launch_gmapping_slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('slam_gmapping'),
                'launch',
                'slam_gmapping.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time':'false'
        }.items()
    )

    return LaunchDescription([
        rviz_arg,
        rviz_node,
        launch_gmapping_slam,
    ])