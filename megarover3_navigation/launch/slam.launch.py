import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('megarover3_navigation')
    return LaunchDescription([
        DeclareLaunchArgument(
            'rover', default_value='mega3', description='Rover type: mega3, f120a, s40a_lb',
        ),
        DeclareLaunchArgument(
            'rvizconfig', default_value=os.path.join(share, 'rviz', 'slam.rviz'),
        ),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('autostart', default_value='true'),
        DeclareLaunchArgument(
            'use_lifecycle_manager', default_value='false',
            description='External manager owns transitions; disables launch autostart.',
        ),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.join(share, 'config', 'mapper_params_online_async.yaml'),
        ),
        Node(
            condition=IfCondition(LaunchConfiguration('use_rviz')),
            package='rviz2', executable='rviz2', name='rviz2', output='screen',
            parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
            arguments=['-d', LaunchConfiguration('rvizconfig')],
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                share, 'launch', 'internal', 'slam_async.launch.py',
            )),
            launch_arguments={
                name: LaunchConfiguration(name) for name in (
                    'autostart', 'use_lifecycle_manager', 'use_sim_time', 'slam_params_file',
                )
            }.items(),
        ),
    ])
