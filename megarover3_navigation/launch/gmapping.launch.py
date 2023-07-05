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
    description_package_path = get_package_share_path('megarover_description')
    nav_package_path = get_package_share_path('megarover3_navigation')
    default_model_path = description_package_path / 'urdf/mega3.xacro'
    default_rviz_config_path = nav_package_path / 'rviz/gmapping.rviz'
    rviz_arg = DeclareLaunchArgument(name='rvizconfig', default_value=str(default_rviz_config_path),
                                     description='Absolute path to rviz config file')

    model_arg = DeclareLaunchArgument(name='model', default_value=str(default_model_path),
                                      description='Absolute path to robot urdf file')

    robot_description = ParameterValue(Command(['xacro ', LaunchConfiguration('model')]),
                                       value_type=str)
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('rvizconfig')],
    )

    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
    )
    
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}]
    )

    pub_odom_node = Node(
        package='megarover3_bringup',
        executable='pub_odom',
        name='pub_odom'
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
        model_arg,
        rviz_arg,
        launch_gmapping_slam,
        robot_state_publisher_node,
        joint_state_publisher_node,
        pub_odom_node,
        rviz_node,
    ])