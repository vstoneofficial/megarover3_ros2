import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction, SetEnvironmentVariable, SetLaunchConfiguration
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.substitutions import FindPackageShare

def _resolve_params_file(context, bringup_dir):
    params_file = LaunchConfiguration('params_file').perform(context)
    rover = LaunchConfiguration('rover').perform(context)
    if params_file:
        selected = params_file
    elif rover == 'f120a':
        selected = os.path.join(bringup_dir, 'config', 'f120a_nav2_params.yaml')
    elif rover == 's40a_lb':
        selected = os.path.join(bringup_dir, 'config', 's40a_lb_nav2_params.yaml')
    else:
        selected = os.path.join(bringup_dir, 'config', 'mega3_nav2_params.yaml')
    return [SetLaunchConfiguration('selected_params_file', selected)]


def generate_launch_description():
    bringup_dir = get_package_share_directory('megarover3_navigation')
    launch_dir = os.path.join(bringup_dir, 'launch', 'internal')

    namespace = LaunchConfiguration('namespace')
    use_namespace = LaunchConfiguration('use_namespace')
    rover = LaunchConfiguration('rover')
    map_yaml_file = LaunchConfiguration('map')
    use_sim_time = LaunchConfiguration('use_sim_time')
    params_file = LaunchConfiguration('params_file')
    slam = LaunchConfiguration('slam')
    slam_params_file = LaunchConfiguration('slam_params_file')
    autostart = LaunchConfiguration('autostart')
    use_composition = LaunchConfiguration('use_composition')
    container_name = LaunchConfiguration('container_name')
    use_respawn = LaunchConfiguration('use_respawn')
    log_level = LaunchConfiguration('log_level')
    use_rviz = LaunchConfiguration('use_rviz')
    rvizconfig = LaunchConfiguration('rvizconfig')

    selected_params_file = LaunchConfiguration('selected_params_file')

    stdout_linebuf_envvar = SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1')

    bringup_group = GroupAction([
        PushRosNamespace(
            condition=IfCondition(use_namespace),
            namespace=namespace,
        ),

        Node(
            condition=IfCondition(use_composition),
            name='nav2_container',
            package='rclcpp_components',
            executable='component_container_isolated',
            parameters=[
                {'autostart': autostart},
                {'use_sim_time': use_sim_time},
            ],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
            output='screen',
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'slam_async.launch.py')),
            condition=IfCondition(slam),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'slam_params_file': slam_params_file,
            }.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'localization_stack.launch.py')),
            condition=IfCondition(PythonExpression(['not ', slam])),
            launch_arguments={
                'namespace': namespace,
                'map': map_yaml_file,
                'use_sim_time': use_sim_time,
                'autostart': autostart,
                'params_file': selected_params_file,
                'use_composition': use_composition,
                'use_respawn': use_respawn,
                'container_name': container_name,
                'log_level': log_level,
            }.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'nav2_stack.launch.py')),
            launch_arguments={
                'namespace': namespace,
                'use_sim_time': use_sim_time,
                'autostart': autostart,
                'params_file': selected_params_file,
                'use_composition': use_composition,
                'use_respawn': use_respawn,
                'container_name': container_name,
                'log_level': log_level,
            }.items(),
        ),
    ])

    rviz_node = Node(
        condition=IfCondition(use_rviz),
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rvizconfig],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('rover', default_value='mega3', description='Rover type: mega3 or f120a or s40a_lb'),
        DeclareLaunchArgument('namespace', default_value='', description='Top-level namespace'),
        DeclareLaunchArgument('use_namespace', default_value='false', description='Whether to apply namespace'),
        DeclareLaunchArgument('slam', default_value='false', description='Whether to run SLAM'),
        DeclareLaunchArgument('map', default_value=os.path.join(bringup_dir, 'maps', 'test.yaml'), description='Full path to map yaml file'),
        DeclareLaunchArgument('use_sim_time', default_value='false', description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('params_file', default_value='', description='Optional full path to nav2 params file. Empty = auto by rover'),
        DeclareLaunchArgument('slam_params_file', default_value=os.path.join(bringup_dir, 'config', 'mapper_params_online_async.yaml'), description='Full path to slam toolbox params file'),
        DeclareLaunchArgument('autostart', default_value='true', description='Automatically startup the nav2 stack'),
        DeclareLaunchArgument('use_composition', default_value='True', description='Whether to use composed bringup'),
        DeclareLaunchArgument('container_name', default_value='nav2_container', description='Container name when composition is enabled'),
        DeclareLaunchArgument('use_respawn', default_value='False', description='Whether to respawn if a node crashes when composition is disabled'),
        DeclareLaunchArgument('log_level', default_value='info', description='log level'),
        DeclareLaunchArgument('use_rviz', default_value='true', description='Launch RViz2'),
        DeclareLaunchArgument('rvizconfig', default_value=PathJoinSubstitution([FindPackageShare('megarover3_navigation'), 'rviz', 'nav2.rviz']), description='Absolute path to rviz config file'),
        SetLaunchConfiguration('selected_params_file', ''),
        OpaqueFunction(function=lambda context: _resolve_params_file(context, bringup_dir)),

        stdout_linebuf_envvar,
        bringup_group,
        rviz_node,
    ])
