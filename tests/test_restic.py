import os
import sys
import subprocess
from time import strftime

import pytest

from PyQt5.QtWidgets import QApplication

import restic_qt.restic_interface as restic
from restic_qt.helper import create_path
from restic_qt.helper import ResticException


app = QApplication(sys.argv)


def test_backup(repository):
    backup_thread = restic.BackupThread(['.'])
    backup_thread.run()
    output = subprocess.check_output(['restic', 'snapshots', '--json'],
                                     encoding='utf8')
    assert -1 != output.find(str(os.path.realpath('.')))


def test_list(repository):
    backup_thread = restic.BackupThread(['.'])
    backup_thread.run()
    list_thread = restic.ListThread()
    output = list_thread.run()
    assert str(os.path.realpath('.')) == output[0]['paths'][0]


def test_info(repository):
    backup_thread = restic.BackupThread(['.'])
    backup_thread.run()
    info_thread = restic.InfoThread()
    output = info_thread.run()
    assert len(output) == 2


def test_restore(target_path, archives):
    archive_list = archives
    archive_name = archive_list[0]['short_id']
    restore_path = os.path.join(target_path, archive_name)
    create_path(restore_path)
    thread = restic.RestoreThread(archive_name, restore_path)
    thread.run()
    assert os.path.exists(
        os.path.join(restore_path, os.path.realpath(__file__)))


def test_delete(target_path, archives):
    archive_list = archives
    archive_name = archive_list[0]['short_id']
    thread = restic.DeleteThread(archive_name)
    thread.run()
    list_thread = restic.ListThread()
    repo_archives = list_thread.run()
    assert archive_name not in repo_archives


# def test_mount(target_path, archives):
#     archive_list = archives
#     archive_name = archive_list[0]['short_id']
#     mount_path = os.path.join(target_path, archive_name)
#     create_path(mount_path)
#     thread = restic.MountThread(archive_name, mount_path)
#     thread.run()
#     assert os.path.exists(
#         os.path.join(mount_path, os.path.realpath(__file__)))
#     os.system('restic umount ' + mount_path)


def test_prune(repository, create_archive):
    archive_list = create_archive(2)
    thread = restic.PruneThread({'hourly': '1'})
    thread.run()
    list_thread = restic.ListThread()
    repo_archives = list_thread.run()
    assert len(archive_list) > len(repo_archives)


def test_ssh_server_not_reachable(form):
    form.config.config['resticqt']['password'] = "foo"
    form.config.config['resticqt']['port'] = "57683"
    form.config.config['resticqt']['user'] = "restic"
    form.config.config['resticqt']['server'] = "192.168.1.10"
    form.config._set_environment_variables()
    list_thread = restic.ListThread()
    with pytest.raises(ResticException):
        output = list_thread.run()
