import os
import sys
import subprocess
from time import strftime

from PyQt5.QtWidgets import QApplication

import restic_qt.restic_interface as restic
from restic_qt.helper import create_path


app = QApplication(sys.argv)


def test_backup(repository):
    backup_thread = restic.BackupThread(['.'])
    backup_thread.run()
    output = subprocess.check_output(['restic', 'list'], encoding='utf8')
    assert -1 != output.find(strftime('%Y-%m-%d_%H:'))


def test_backup_with_prefix(repository):
    backup_thread = restic.BackupThread(['.'], prefix='test')
    backup_thread.run()
    output = subprocess.check_output(['restic', 'list'], encoding='utf8')
    assert -1 != output.find(strftime('test_%Y-%m-%d_%H:'))


def test_restore(target_path, archives):
    archive_list = archives
    archive_name = archive_list[0]['name']
    restore_path = os.path.join(target_path, archive_name)
    create_path(restore_path)
    thread = restic.RestoreThread(archive_name, restore_path)
    thread.run()
    assert os.path.exists(
        os.path.join(restore_path, os.path.realpath(__file__)))


def test_delete(target_path, archives):
    archive_list = archives
    archive_name = archive_list[0]['name']
    thread = restic.DeleteThread(archive_name)
    thread.run()
    list_thread = restic.ListThread()
    repo_archives = list_thread.run()
    assert archive_name not in repo_archives


def test_mount(target_path, archives):
    archive_list = archives
    archive_name = archive_list[0]['name']
    mount_path = os.path.join(target_path, archive_name)
    create_path(mount_path)
    thread = restic.MountThread(archive_name, mount_path)
    thread.run()
    assert os.path.exists(
        os.path.join(mount_path, os.path.realpath(__file__)))
    os.system('restic umount ' + mount_path)


def test_prune(repository, create_archive):
    archive_list = create_archive(2)
    thread = restic.PruneThread({'hourly': '1'})
    thread.run()
    list_thread = restic.ListThread()
    repo_archives = list_thread.run()
    assert len(archive_list) > len(repo_archives)
