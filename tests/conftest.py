import json
import os
import pytest
import subprocess
from shutil import copyfile

import restic_qt.restic_interface as restic
from restic_qt.main_window import MainWindow
from restic_qt.helper import remove_path


def example_config():
    return '/tmp/test.conf'


@pytest.fixture
def mock_home(tmpdir):
    envs = {
        'HOME': tmpdir.strpath,
    }
    yield envs
    remove_path(envs['HOME'])


@pytest.fixture
def setup_config():
    tmp_path = '/tmp/test.conf'
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(dir_path,
                               '../docs/restic_qt.conf.example')
    copyfile(config_path, tmp_path)
    yield tmp_path
    os.remove(tmp_path)


@pytest.fixture
def form(setup_config, monkeypatch):
    form = MainWindow()
    monkeypatch.setattr(form.config, '_get_path', example_config)
    form.config.read()
    return form


@pytest.fixture(scope='session')
def repository(tmpdir_factory):
    repository_path = tmpdir_factory.mktemp('test-resticqt')
    os.environ['RESTIC_REPOSITORY'] = repository_path.strpath
    os.environ['RESTIC_PASSWORD'] = 'foo'
    subprocess.run(['restic', 'init'],
                   stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)
    yield
    remove_path(repository_path)

@pytest.fixture
def archives(repository):
    backup_thread = restic.BackupThread(['.'])
    backup_thread.run()
    list_thread = restic.ListThread()
    output = list_thread.run()
    return output

@pytest.fixture
def target_path(tmpdir):
    yield str(tmpdir)
    remove_path(str(tmpdir))


@pytest.fixture
def create_archive():
    def _create_archive(number_of_turns):
        while number_of_turns > 0:
            backup_thread = restic.BackupThread(['.'])
            backup_thread.run()
            number_of_turns -= 1
        list_thread = restic.ListThread()
        return list_thread.run()
    return _create_archive
