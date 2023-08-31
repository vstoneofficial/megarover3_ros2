import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.conditions import IfCondition, LaunchConfigurationEquals


def generate_launch_description():
    nav2_launch_file_dir = os.path.join(
        get_package_share_directory('megarover3_navigation'), 'launch')

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    map_dir = LaunchConfiguration(
        'map',
        default=os.path.join(
            get_package_share_directory('megarover3_navigation'),
            'maps',
            'tb_slam1.yaml'))  # change this to your own map for navigation

    mega3_param_dir = LaunchConfiguration(
        'params_file',
        default=os.path.join(
            get_package_share_directory('megarover3_navigation'),
            'config',
            'mega3_nav2_params.yaml'))

    f120a_param_dir = LaunchConfiguration(
        'params_file',
        default=os.path.join(
            get_package_share_directory('megarover3_navigation'),
            'config',
            'f120a_nav2_params.yaml'))

    rviz_config_dir = os.path.join(
        get_package_share_directory('megarover3_navigation'),
        'rviz',
        'nav2.rviz')

    return LaunchDescription([
        DeclareLaunchArgument(
            'rover',
            default_value='mega3',
            description='Megarover model',
            choices=['mega3', 'f120a']),

        DeclareLaunchArgument(
            'map',
            default_value=map_dir,
            description='Full path to map file to load'),

        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation (Gazebo) clock if true'),

        DeclareLaunchArgument(
            'params_file',
            condition=LaunchConfigurationEquals('rover', 'mega3'),
            default_value=mega3_param_dir,
            description='Full path to param file to load'),

        DeclareLaunchArgument(
            'params_file',
            condition=LaunchConfigurationEquals('rover', 'f120a'),
            default_value=f120a_param_dir,
            description='Full path to param file to load'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [nav2_launch_file_dir, '/bringup_launch.py']),
            condition=LaunchConfigurationEquals('rover', 'mega3'),
            launch_arguments={
                'map': map_dir,
                'use_sim_time': use_sim_time,
                'params_file': mega3_param_dir}.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [nav2_launch_file_dir, '/bringup_launch.py']),
            condition=LaunchConfigurationEquals('rover', 'f120a'),
            launch_arguments={
                'map': map_dir,
                'use_sim_time': use_sim_time,
                'params_file': f120a_param_dir}.items(),
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config_dir],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen'),
    ])
