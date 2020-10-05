import os
import sys

from PyQt5 import uic
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import (QMainWindow, QFileSystemModel, QFileDialog,
                             QMessageBox)

from restic_qt.config import Config
from restic_qt.helper import (ResticException, show_error, convert_size, open_path,
                              create_path, remove_path, check_path)
from restic_qt.help import Help
import restic_qt.restic_interface as restic
from restic_qt.progress import ProgressDialog
from restic_qt.restic_model import ResticTableModel


class MainWindow(QMainWindow):
    """The main window of the application. It provides the various functions to
    control Restic."""

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        QCoreApplication.setApplicationName("restic-qt")

        # Load the UI file to get the dialogs layout.
        dir_path = os.path.dirname(os.path.realpath(__file__))
        ui_path = os.path.join(dir_path + '/static/UI/MainWindow.ui')
        uic.loadUi(ui_path, self)

        # Set the window title after the UI has been loaded. Otherwise it gets
        # overwritten.
        self.setWindowTitle("Restic-Qt")

        # Create a Config object for storing the configuration.
        self.config = Config()

        # list of mounted archives
        self.mount_paths = []

        # File tree
        model = QFileSystemModel()
        # model.setRootPath('/')
        model.setRootPath(os.getenv('HOME'))
        self.treeview_files.setModel(model)
        self.treeview_files.expandAll()
        self.treeview_files.setIndentation(20)
        self.treeview_files.setColumnHidden(1, True)
        self.treeview_files.setColumnHidden(2, True)
        self.treeview_files.setColumnHidden(3, True)
        # return the clicking on an item in the tree
        self.treeview_files.clicked.connect(self.get_selected_path)

        self.list_archive.setSortingEnabled(True)

        # Connecting actions and buttons.
        self.action_settings.triggered.connect(self.show_settings)
        self.action_backup.triggered.connect(self.create_backup)
        self.action_restore.triggered.connect(self.restore_backup)
        self.action_delete.triggered.connect(self.delete_backup)
        self.action_mount.triggered.connect(self.mount_backup)
        self.action_help.triggered.connect(self.show_help)

    def start(self):
        """This method is intendet to be used only once at the application
        start. It reads the configuration file and sets the required
        environment variables."""
        try:
            self.config.read()
            # show the help window if needed and save it's answer
            if not self.config.hide_help:
                self.config.config['resticqt']['hide_help'] = (
                    str(self.show_help()))
                self.config.write()
            self.config._set_environment_variables()
            self._create_table()
        except ResticException as e:
            show_error(e)
            sys.exit(1)

    def closeEvent(self, *args, **kwargs):
        super(QMainWindow, self).closeEvent(*args, **kwargs)
        # When the application gets close unmount all the archives and remove
        # their paths.
        self._umount_archives()

    def _umount_archives(self):
        if self.mount_paths:
            for path in self.mount_paths:
                if os.path.exists(path):
                    os.system('restic umount ' + path)
                    remove_path(path)
        self.mount_paths = []

    def _create_table(self):
        tabledata = self._update_archives()
        print(tabledata)
        tablemodel = ResticTableModel(tabledata, self)
        self.list_archive.setModel(tablemodel)

    def show_settings(self):
        """Display the settings dialog."""
        self.config.set_form_values()
        self.config.exec_()

    def background_backup(self):
        self.config.read()
        self.config._set_environment_variables()
        backup_thread = restic.BackupThread(self.config.includes,
                                            excludes=self.config.excludes,
                                            prefix=self.config.prefix)
        backup_thread.run()
        if self.config.retention_policy_enabled:
            prune_thread = restic.PruneThread(self.config.retention_policy)
            prune_thread.run()

    def get_selected_path(self, signal):
        """returns the path of the item selected in the file tree."""
        self.src_path = self.treeview_files.model().filePath(signal)

    def _check_path(self):
        """Makes sure that the user selected a path to backup."""
        message = ("Please select a file or directory "
                   "before taking a backup.")
        if not hasattr(self, 'src_path'):
            raise ResticException(message)

    def create_backup(self):
        """Creates a backup of the selected item in the treeview."""
        if not self._check_mounts():
            return
        try:
            self._check_path()
            backup_thread = restic.BackupThread([self.src_path],
                                                excludes=self.config.excludes,
                                                prefix=self.config.prefix)
            backup_dialog = ProgressDialog(backup_thread)
            backup_dialog.label_info.setText("Restic-Qt is currently creating an"
                                             " archive.")
            backup_dialog.exec_()
            if self.config.retention_policy_enabled:
                prune_thread = restic.PruneThread(self.config.retention_policy)
                prune_dialog = ProgressDialog(prune_thread)
                prune_dialog.label_info.setText("Restic-Qt is currently pruning "
                                                "the repository.")
                prune_dialog.exec_()
            self.update_ui()
        except ResticException as e:
            show_error(e)

    def _get_target_path(self):
        """Opens a file dialog and returns the opened path."""
        dlg = QFileDialog
        dlg.DirectoryOnly
        folder_name = str(dlg.getExistingDirectory(
            self, "Select Directory", os.getenv('HOME')))
        return folder_name

    def show_help(self):
        """Diplays the help dialog with some informations about the
        application."""
        help_window = Help()
        help_window.exec_()
        return help_window.check_hide_enabled.isChecked()

    @property
    def selected_archive(self):
        return self.list_archive.currentItem().text()

    def restore_backup(self):
        """Restores a selected backup to the given path."""
        try:
            archive_name = self.selected_archive
            target_path = self._get_target_path()
        except AttributeError:
            error = ResticException(
                "Please create or select an archive first.")
            archive_name = None
            target_path = None
            show_error(error)

        # Only restore the backup if the target is writeable and the archive
        # was selected.
        if check_path(target_path) and archive_name:
            try:
                restore_path = os.path.join(target_path, archive_name)
                create_path(restore_path)
                thread = restic.RestoreThread(archive_name, restore_path)
                dialog = ProgressDialog(thread)
                dialog.label_info.setText(
                    "Restic-Qt is currently restoring a backup.")
                dialog.exec_()
                open_path(restore_path)
            except ResticException as e:
                show_error(e)
                remove_path(restore_path)

    def delete_backup(self):
        """Deletes the selected archive from the repository."""
        if not self._check_mounts():
            return
        try:
            archive_name = self.selected_archive
        except AttributeError:
            error = ResticException(
                "Please create or select an archive first.")
            archive_name = None
            show_error(error)

        # Only continue if an archive was selected.
        if archive_name:
            # Prompt the user before continuing.
            if self.yes_no("Do you want to delete this archive?"):
                try:
                    thread = restic.DeleteThread(archive_name)
                    dialog = ProgressDialog(thread)
                    dialog.label_info.setText(
                        "Restic-Qt is currently deleting an archive.")
                    dialog.exec_()
                    self.update_ui()
                except ResticException as e:
                    show_error(e)

    def _update_archives(self):
        """Lists all the archive names in the UI."""
        thread = restic.ListThread()
        archives = []
        snapshot_dates = []
        snapshot_ids = []
        for archive in thread.run():
            snapshot_dates.append(archive['time'])
            snapshot_ids.append(archive['short_id'])
        archives.append(snapshot_dates)
        archives.append(snapshot_ids)
        return archives

    def update_ui(self):
        """Updates the archive list and repository stats in the UI."""
        try:
            self._update_archives()
            self._update_repository_stats()
        except ResticException as e:
            show_error(e)

    def _update_repository_stats(self):
        """Update the repository stats and display them in a human readable
        format."""
        thread = restic.InfoThread()
        stats = thread.run()
        self.label_repo_original_size.setText(
            "Original Size: "
            + convert_size(stats['total_size']))

    def mount_backup(self):
        """Mount the selected archive in the tmp directory. If it succeeds the
        mount_path gets written to a property of the main_window."""
        try:
            archive_name = self.selected_archive
        except AttributeError:
            error = ResticException(
                "Please create or select an archive first.")
            archive_name = None
            show_error(error)

        # only continue if the user selected an archive
        if archive_name:
            mount_path = os.path.join('/tmp/', archive_name)
            create_path(mount_path)
            # only continue if the mount_path is writeable
            if os.access(mount_path, os.W_OK):
                thread = restic.MountThread(archive_name, mount_path)
                try:
                    thread.run()
                    self.mount_paths.append(mount_path)
                    open_path(mount_path)
                except ResticException as e:
                    show_error(e)
                    remove_path(mount_path)
            else:
                # Opens the path in a file manager
                open_path(mount_path)

    def _check_mounts(self):
        if self.mount_paths:
            if self.yes_no("To proceed you need to unmout all "
                           "archives. Do you want to continue?"):
                self._umount_archives()
                return True
            else:
                return False

    def yes_no(self, question):
        """Simple yes/no dialog.

        Args:
                question (str) The question to display to the user."""
        button_reply = QMessageBox.question(self, 'Restic-Qt', question,
                                            QMessageBox.Yes |
                                            QMessageBox.No, QMessageBox.No)
        if button_reply == QMessageBox.Yes:
            return True
        else:
            return False
