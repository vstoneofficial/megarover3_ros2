from ament_index_python.packages import get_package_share_path
from launch.actions import DeclareLaunchArgument, GroupAction
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.parameter_descriptions import ParameterValue

from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.conditions import IfCondition, LaunchConfigurationEquals
from launch.actions import LogInfo

import os
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    description_package_path = get_package_share_path('megarover_description')
    bringup_package_path = get_package_share_path('megarover3_bringup')

    rover_arg = DeclareLaunchArgument(name='rover',
                                       default_value='mega3',
                                       description='Megarover Ver.3.0 model',
                                       choices=['mega3', 'f120a'])
    
    mega3_model_path = description_package_path / 'urdf/mega3.xacro'
    f120a_model_path = description_package_path / 'urdf/f120a.xacro'

    mega3_rviz_config_path = os.path.join(
        bringup_package_path,
        'rviz',
        'mega3.rviz')

    f120a_rviz_config_path = os.path.join(
        bringup_package_path,
        'rviz',
        'f120a.rviz')
    
    mega3_start_group = GroupAction(
        condition=LaunchConfigurationEquals('rover', 'mega3'),
        actions=[
            Node(
                package='rviz2',
                executable='rviz2',
                name='mega3_rviz2',
                output='screen',
                arguments=['-d', mega3_rviz_config_path],
                ),
            Node(
                package='robot_state_publisher',
                executable='robot_state_publisher',
                name='mega3_robot_state_publisher_node',
                parameters=[{'robot_description': ParameterValue(
                    Command(['xacro ', str(mega3_model_path)]), value_type=str
                    )}]
            )]
    )
    f120a_start_group = GroupAction(
        condition=LaunchConfigurationEquals('rover', 'f120a'),
        actions=[
            Node(
                package='rviz2',
                executable='rviz2',
                name='f120a_rviz2',
                output='screen',
                arguments=['-d', f120a_rviz_config_path],
                ),
            Node(
                package='robot_state_publisher',
                executable='robot_state_publisher',
                name='f120a_robot_state_publisher_node',
                parameters=[{'robot_description': ParameterValue(
                    Command(['xacro ', str(f120a_model_path)]), value_type=str
                    )}]
            )]
    )


    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
    )

    pub_odom_node = Node(
        package='megarover3_bringup',
        executable='pub_odom',
        name='pub_odom'
    )

    return LaunchDescription([
        rover_arg,
        joint_state_publisher_node,
        mega3_start_group,
        f120a_start_group,

    ])