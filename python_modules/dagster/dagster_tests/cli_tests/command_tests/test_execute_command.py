from __future__ import print_function

import re

import pytest
from click import UsageError
from click.testing import CliRunner

from dagster.cli.pipeline import execute_execute_command, pipeline_execute_command
from dagster.core.errors import DagsterUserCodeProcessError
from dagster.core.test_utils import mocked_instance
from dagster.utils import file_relative_path

from .test_cli_commands import execute_command_contexts, valid_pipeline_target_cli_args


def test_execute_mode_command():
    runner = CliRunner()

    with mocked_instance():
        add_result = runner_pipeline_execute(
            runner,
            [
                '-w',
                file_relative_path(__file__, '../../workspace.yaml'),
                '--config',
                file_relative_path(
                    __file__, '../../environments/multi_mode_with_resources/add_mode.yaml'
                ),
                '--mode',
                'add_mode',
                '-p',
                'multi_mode_with_resources',  # pipeline name
            ],
        )

        assert add_result

        mult_result = runner_pipeline_execute(
            runner,
            [
                '-w',
                file_relative_path(__file__, '../../workspace.yaml'),
                '--config',
                file_relative_path(
                    __file__, '../../environments/multi_mode_with_resources/mult_mode.yaml'
                ),
                '--mode',
                'mult_mode',
                '-p',
                'multi_mode_with_resources',  # pipeline name
            ],
        )

        assert mult_result

        double_adder_result = runner_pipeline_execute(
            runner,
            [
                '-w',
                file_relative_path(__file__, '../../workspace.yaml'),
                '--config',
                file_relative_path(
                    __file__, '../../environments/multi_mode_with_resources/double_adder_mode.yaml'
                ),
                '--mode',
                'double_adder_mode',
                '-p',
                'multi_mode_with_resources',  # pipeline name
            ],
        )

        assert double_adder_result


def test_execute_preset_command():
    with mocked_instance():
        runner = CliRunner()
        add_result = runner_pipeline_execute(
            runner,
            [
                '-w',
                file_relative_path(__file__, '../../workspace.yaml'),
                '--preset',
                'add',
                '-p',
                'multi_mode_with_resources',  # pipeline name
            ],
        )

        assert 'PIPELINE_SUCCESS' in add_result.output

        # Can't use --preset with --config
        bad_res = runner.invoke(
            pipeline_execute_command,
            [
                '-w',
                file_relative_path(__file__, '../../workspace.yaml'),
                '--preset',
                'add',
                '--config',
                file_relative_path(
                    __file__, '../../environments/multi_mode_with_resources/double_adder_mode.yaml'
                ),
                '-p',
                'multi_mode_with_resources',  # pipeline name
            ],
        )
        assert bad_res.exit_code == 2


@pytest.mark.parametrize('gen_execute_args', execute_command_contexts())
def test_execute_command_no_env(gen_execute_args):
    with gen_execute_args as (cli_args, uses_legacy_repository_yaml_format, instance):
        if uses_legacy_repository_yaml_format:
            with pytest.warns(
                UserWarning,
                match=re.escape(
                    'You are using the legacy repository yaml format. Please update your file '
                ),
            ):
                execute_execute_command(env_file_list=None, cli_args=cli_args, instance=instance)
        else:
            execute_execute_command(env_file_list=None, cli_args=cli_args, instance=instance)


@pytest.mark.parametrize('gen_execute_args', execute_command_contexts())
def test_execute_command_env(gen_execute_args):
    with gen_execute_args as (cli_args, uses_legacy_repository_yaml_format, instance):
        if uses_legacy_repository_yaml_format:
            with pytest.warns(
                UserWarning,
                match=re.escape(
                    'You are using the legacy repository yaml format. Please update your file '
                ),
            ):
                execute_execute_command(
                    env_file_list=[file_relative_path(__file__, 'default_log_error_env.yaml')],
                    cli_args=cli_args,
                    instance=instance,
                )
        else:
            execute_execute_command(
                env_file_list=[file_relative_path(__file__, 'default_log_error_env.yaml')],
                cli_args=cli_args,
                instance=instance,
            )


@pytest.mark.parametrize('execute_cli_args', valid_pipeline_target_cli_args())
def test_execute_command_runner(execute_cli_args):
    cli_args, uses_legacy_repository_yaml_format = execute_cli_args
    runner = CliRunner()

    with mocked_instance():
        if uses_legacy_repository_yaml_format:
            with pytest.warns(
                UserWarning,
                match=re.escape(
                    'You are using the legacy repository yaml format. Please update your file '
                ),
            ):
                runner_pipeline_execute(runner, cli_args)

                runner_pipeline_execute(
                    runner,
                    ['--config', file_relative_path(__file__, 'default_log_error_env.yaml')]
                    + cli_args,
                )
        else:
            runner_pipeline_execute(runner, cli_args)

            runner_pipeline_execute(
                runner,
                ['--config', file_relative_path(__file__, 'default_log_error_env.yaml')] + cli_args,
            )


def test_output_execute_log_stdout(capfd):
    with mocked_instance(
        overrides={
            'compute_logs': {
                'module': 'dagster.core.storage.noop_compute_log_manager',
                'class': 'NoOpComputeLogManager',
            }
        },
    ) as instance:
        execute_execute_command(
            env_file_list=None,
            cli_args={
                'python_file': file_relative_path(__file__, 'test_cli_commands.py'),
                'attribute': 'stdout_pipeline',
            },
            instance=instance,
        )

        captured = capfd.readouterr()
        # All pipeline execute output currently logged to stderr
        assert 'HELLO WORLD' in captured.err


def test_output_execute_log_stderr(capfd):
    with mocked_instance(
        overrides={
            'compute_logs': {
                'module': 'dagster.core.storage.noop_compute_log_manager',
                'class': 'NoOpComputeLogManager',
            }
        },
    ) as instance:
        execute_execute_command(
            env_file_list=None,
            cli_args={
                'python_file': file_relative_path(__file__, 'test_cli_commands.py'),
                'attribute': 'stderr_pipeline',
            },
            instance=instance,
        )
        captured = capfd.readouterr()
        assert 'I AM SUPPOSED TO FAIL' in captured.err


def test_more_than_one_pipeline():
    with mocked_instance() as instance:
        with pytest.raises(
            UsageError,
            match=re.escape(
                "Must provide --pipeline as there is more than one pipeline in bar. "
                "Options are: ['baz', 'foo']."
            ),
        ):
            execute_execute_command(
                env_file_list=None,
                cli_args={
                    'repository_yaml': None,
                    'pipeline': None,
                    'python_file': file_relative_path(__file__, 'test_cli_commands.py'),
                    'module_name': None,
                    'attribute': None,
                },
                instance=instance,
            )


def test_attribute_not_found():
    with mocked_instance() as instance:
        with pytest.raises(
            DagsterUserCodeProcessError, match=re.escape('nope not found at module scope in file')
        ):
            execute_execute_command(
                env_file_list=None,
                cli_args={
                    'repository_yaml': None,
                    'pipeline': None,
                    'python_file': file_relative_path(__file__, 'test_cli_commands.py'),
                    'module_name': None,
                    'attribute': 'nope',
                },
                instance=instance,
            )


def test_attribute_is_wrong_thing():
    with mocked_instance() as instance:
        with pytest.raises(
            DagsterUserCodeProcessError,
            match=re.escape(
                'Loadable attributes must be either a PipelineDefinition or a '
                'RepositoryDefinition. Got 123.'
            ),
        ):
            execute_execute_command(
                env_file_list=[],
                cli_args={
                    'repository_yaml': None,
                    'pipeline': None,
                    'python_file': file_relative_path(__file__, 'test_cli_commands.py'),
                    'module_name': None,
                    'attribute': 'not_a_repo_or_pipeline',
                },
                instance=instance,
            )


def test_attribute_fn_returns_wrong_thing():
    with mocked_instance() as instance:
        with pytest.raises(
            DagsterUserCodeProcessError,
            match=re.escape(
                "Loadable attributes must be either a PipelineDefinition or a RepositoryDefinition."
            ),
        ):
            execute_execute_command(
                env_file_list=[],
                cli_args={
                    'repository_yaml': None,
                    'pipeline': None,
                    'python_file': file_relative_path(__file__, 'test_cli_commands.py'),
                    'module_name': None,
                    'attribute': 'not_a_repo_or_pipeline_fn',
                },
                instance=instance,
            )


def runner_pipeline_execute(runner, cli_args):
    result = runner.invoke(pipeline_execute_command, cli_args)
    if result.exit_code != 0:
        # CliRunner captures stdout so printing it out here
        raise Exception(
            (
                'dagster pipeline execute commands with cli_args {cli_args} '
                'returned exit_code {exit_code} with stdout:\n"{stdout}" and '
                '\nresult as string: "{result}"'
            ).format(
                cli_args=cli_args, exit_code=result.exit_code, stdout=result.stdout, result=result
            )
        )
    return result


def test_default_memory_run_storage():
    with mocked_instance() as instance:
        cli_args = {
            'workspace': (file_relative_path(__file__, 'repository_file.yaml'),),
            'pipeline': 'foo',
            'python_file': None,
            'module_name': None,
            'attribute': None,
        }
        with pytest.warns(
            UserWarning,
            match=re.escape(
                'You are using the legacy repository yaml format. Please update your file '
            ),
        ):
            result = execute_execute_command(
                env_file_list=None, cli_args=cli_args, instance=instance
            )
        assert result.success


def test_override_with_in_memory_storage():
    with mocked_instance() as instance:
        cli_args = {
            'workspace': (file_relative_path(__file__, 'repository_file.yaml'),),
            'pipeline': 'foo',
            'python_file': None,
            'module_name': None,
            'attribute': None,
        }
        with pytest.warns(
            UserWarning,
            match=re.escape(
                'You are using the legacy repository yaml format. Please update your file '
            ),
        ):
            result = execute_execute_command(
                env_file_list=[file_relative_path(__file__, 'in_memory_env.yaml')],
                cli_args=cli_args,
                instance=instance,
            )
        assert result.success


def test_override_with_filesystem_storage():
    with mocked_instance() as instance:
        cli_args = {
            'workspace': (file_relative_path(__file__, 'repository_file.yaml'),),
            'pipeline': 'foo',
            'python_file': None,
            'module_name': None,
            'attribute': None,
        }
        with pytest.warns(
            UserWarning,
            match=re.escape(
                'You are using the legacy repository yaml format. Please update your file '
            ),
        ):
            result = execute_execute_command(
                env_file_list=[file_relative_path(__file__, 'filesystem_env.yaml')],
                cli_args=cli_args,
                instance=instance,
            )
        assert result.success


def test_multiproc():
    with mocked_instance():
        runner = CliRunner()
        add_result = runner_pipeline_execute(
            runner,
            [
                '-w',
                file_relative_path(__file__, '../../workspace.yaml'),
                '--preset',
                'multiproc',
                '-p',
                'multi_mode_with_resources',  # pipeline name
            ],
        )
        assert add_result.exit_code == 0

        assert 'PIPELINE_SUCCESS' in add_result.output


def test_multiproc_invalid():
    # force ephemeral instance by removing out DAGSTER_HOME
    runner = CliRunner(env={'DAGSTER_HOME': None})
    add_result = runner.invoke(
        pipeline_execute_command,
        [
            '-w',
            file_relative_path(__file__, '../../workspace.yaml'),
            '--preset',
            'multiproc',
            '-p',
            'multi_mode_with_resources',  # pipeline name
        ],
    )
    # which is invalid for multiproc
    assert add_result.exit_code != 0
    assert 'DagsterUnmetExecutorRequirementsError' in add_result.output


def test_tags_pipeline():
    runner = CliRunner()
    with mocked_instance() as instance:
        with pytest.warns(
            UserWarning,
            match=re.escape(
                'You are using the legacy repository yaml format. Please update your file '
            ),
        ):
            result = runner.invoke(
                pipeline_execute_command,
                [
                    '-w',
                    file_relative_path(__file__, 'repository_module.yaml'),
                    '--tags',
                    '{ "foo": "bar" }',
                    '-p',
                    'foo',
                ],
            )
        assert result.exit_code == 0
        runs = instance.get_runs()
        assert len(runs) == 1
        run = runs[0]
        assert len(run.tags) == 1
        assert run.tags.get('foo') == 'bar'

    with mocked_instance() as instance:
        result = runner.invoke(
            pipeline_execute_command,
            [
                '-w',
                file_relative_path(__file__, '../../workspace.yaml'),
                '--preset',
                'add',
                '--tags',
                '{ "foo": "bar" }',
                '-p',
                'multi_mode_with_resources',  # pipeline name
            ],
        )
        assert result.exit_code == 0
        runs = instance.get_runs()
        assert len(runs) == 1
        run = runs[0]
        assert len(run.tags) == 1
        assert run.tags.get('foo') == 'bar'


def test_execute_subset_pipeline_single_clause_solid_name():
    runner = CliRunner()
    with mocked_instance() as instance:
        result = runner.invoke(
            pipeline_execute_command,
            [
                '-f',
                file_relative_path(__file__, 'test_cli_commands.py'),
                '-a',
                'foo_pipeline',
                '--solid-selection',
                'do_something',
            ],
        )
        assert result.exit_code == 0
        runs = instance.get_runs()
        assert len(runs) == 1
        run = runs[0]
        assert run.solid_selection == ['do_something']
        assert run.solids_to_execute == {'do_something'}


def test_execute_subset_pipeline_single_clause_dsl():
    runner = CliRunner()
    with mocked_instance() as instance:
        result = runner.invoke(
            pipeline_execute_command,
            [
                '-f',
                file_relative_path(__file__, 'test_cli_commands.py'),
                '-a',
                'foo_pipeline',
                '--solid-selection',
                '*do_something+',
            ],
        )
        assert result.exit_code == 0
        runs = instance.get_runs()
        assert len(runs) == 1
        run = runs[0]
        assert run.solid_selection == ['*do_something+']
        assert run.solids_to_execute == {'do_something', 'do_input'}


def test_execute_subset_pipeline_multiple_clauses_dsl_and_solid_name():
    runner = CliRunner()
    with mocked_instance() as instance:
        result = runner.invoke(
            pipeline_execute_command,
            [
                '-f',
                file_relative_path(__file__, 'test_cli_commands.py'),
                '-a',
                'foo_pipeline',
                '--solid-selection',
                '*do_something+,do_input',
            ],
        )
        assert result.exit_code == 0
        runs = instance.get_runs()
        assert len(runs) == 1
        run = runs[0]
        assert set(run.solid_selection) == set(['*do_something+', 'do_input'])
        assert run.solids_to_execute == {'do_something', 'do_input'}


def test_execute_subset_pipeline_invalid():
    runner = CliRunner()
    with mocked_instance():
        result = runner.invoke(
            pipeline_execute_command,
            [
                '-f',
                file_relative_path(__file__, 'test_cli_commands.py'),
                '-a',
                'foo_pipeline',
                '--solid-selection',
                'a, b',
            ],
        )
        assert result.exit_code == 1
        assert 'No qualified solids to execute found for solid_selection' in str(result.exception)