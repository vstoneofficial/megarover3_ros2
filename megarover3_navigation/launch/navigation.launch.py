import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction,
    SetEnvironmentVariable, SetLaunchConfiguration,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace, SetRemap
from launch_ros.descriptions import ParameterFile
from launch_ros.parameter_descriptions import ParameterValue
from nav2_common.launch import RewrittenYaml


ROVER_PARAMS = {
    'mega3': 'mega3_nav2_params.yaml',
    'f120a': 'f120a_nav2_params.yaml',
    's40a_lb': 's40a_lb_nav2_params.yaml',
}


def _checked_file(value, argument):
    path = Path(os.path.expandvars(os.path.expanduser(value))).resolve()
    if not path.is_file():
        raise RuntimeError(f'{argument} file does not exist: {path}')
    return str(path)


def _resolve_inputs(context, share):
    rover = LaunchConfiguration('rover').perform(context)
    if rover not in ROVER_PARAMS:
        raise RuntimeError(f'Unsupported rover: {rover}')
    params = LaunchConfiguration('params_file').perform(context)
    params = params or os.path.join(share, 'config', ROVER_PARAMS[rover])
    namespace = LaunchConfiguration('namespace').perform(context).strip('/')
    if not IfCondition(LaunchConfiguration('use_namespace')).evaluate(context):
        namespace = ''
    selected = {
        'selected_params_file': _checked_file(params, 'params_file'),
        'effective_namespace': namespace,
    }
    if IfCondition(LaunchConfiguration('slam')).evaluate(context):
        selected['selected_slam_params_file'] = _checked_file(
            LaunchConfiguration('slam_params_file').perform(context), 'slam_params_file',
        )
    else:
        map_file = LaunchConfiguration('map').perform(context)
        selected['selected_map'] = _checked_file(
            map_file or os.path.join(share, 'maps', 'test.yaml'), 'map',
        )
    if IfCondition(LaunchConfiguration('use_rviz')).evaluate(context):
        selected['selected_rvizconfig'] = _checked_file(
            LaunchConfiguration('rvizconfig').perform(context), 'rvizconfig',
        )
    return [SetLaunchConfiguration(name, value) for name, value in selected.items()]


def generate_launch_description():
    share = get_package_share_directory('megarover3_navigation')
    internal = os.path.join(share, 'launch', 'internal')
    namespace = LaunchConfiguration('effective_namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    use_composition = LaunchConfiguration('use_composition')
    container_name = LaunchConfiguration('container_name')
    log_level = LaunchConfiguration('log_level')
    stack_arguments = {
        'namespace': namespace,
        'use_sim_time': use_sim_time,
        'autostart': autostart,
        'params_file': LaunchConfiguration('selected_params_file'),
        'use_composition': use_composition,
        'use_respawn': LaunchConfiguration('use_respawn'),
        'container_name': container_name,
        'log_level': log_level,
    }
    container_params = ParameterFile(
        RewrittenYaml(
            source_file=LaunchConfiguration('selected_params_file'),
            root_key=namespace,
            param_rewrites={'use_sim_time': use_sim_time, 'autostart': autostart},
            convert_types=True,
        ),
        allow_substs=True,
    )

    bringup = GroupAction([
        PushRosNamespace(namespace),
        Node(
            condition=IfCondition(use_composition),
            name=container_name,
            package='rclcpp_components', executable='component_container_isolated',
            parameters=[container_params, {
                'autostart': ParameterValue(autostart, value_type=bool),
                'use_sim_time': ParameterValue(use_sim_time, value_type=bool),
            }],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
            output='screen',
        ),
        GroupAction(
            condition=IfCondition(LaunchConfiguration('slam')),
            actions=[
                SetRemap('/tf', 'tf'), SetRemap('/tf_static', 'tf_static'),
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(os.path.join(internal, 'slam_async.launch.py')),
                    launch_arguments={
                        'use_sim_time': use_sim_time,
                        'slam_params_file': RewrittenYaml(
                            source_file=LaunchConfiguration('selected_slam_params_file'),
                            root_key=namespace,
                            param_rewrites={'use_sim_time': use_sim_time},
                            convert_types=True,
                        ),
                        'autostart': autostart,
                        'use_lifecycle_manager': 'false',
                    }.items(),
                ),
            ],
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(internal, 'localization_stack.launch.py')),
            condition=UnlessCondition(LaunchConfiguration('slam')),
            launch_arguments={
                **stack_arguments, 'map': LaunchConfiguration('selected_map'),
            }.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(internal, 'nav2_stack.launch.py')),
            launch_arguments=stack_arguments.items(),
        ),
        Node(
            condition=IfCondition(LaunchConfiguration('use_rviz')),
            package='rviz2', executable='rviz2', name='rviz2', output='screen',
            arguments=['-d', LaunchConfiguration('selected_rvizconfig')],
            parameters=[{'use_sim_time': ParameterValue(use_sim_time, value_type=bool)}],
        ),
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'rover', default_value='mega3', choices=list(ROVER_PARAMS),
            description='Rover configuration: mega3 or f120a (legacy s40a_lb retained).',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Top-level namespace'),
        DeclareLaunchArgument(
            'use_namespace', default_value='false', description='Whether to apply namespace',
        ),
        DeclareLaunchArgument('slam', default_value='false', description='Whether to run SLAM'),
        DeclareLaunchArgument(
            'map', default_value=os.path.join(share, 'maps', 'test.yaml'),
            description='Map YAML path; empty uses the bundled test map.',
        ),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument(
            'params_file', default_value='',
            description='Optional Nav2 YAML path; empty selects by rover.',
        ),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.join(share, 'config', 'mapper_params_online_async.yaml'),
        ),
        DeclareLaunchArgument('autostart', default_value='true'),
        DeclareLaunchArgument('use_composition', default_value='true'),
        DeclareLaunchArgument('container_name', default_value='nav2_container'),
        DeclareLaunchArgument('use_respawn', default_value='false'),
        DeclareLaunchArgument('log_level', default_value='info'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument(
            'rvizconfig', default_value=os.path.join(share, 'rviz', 'nav2.rviz'),
        ),
        SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1'),
        OpaqueFunction(function=lambda context: _resolve_inputs(context, share)),
        bringup,
    ])
