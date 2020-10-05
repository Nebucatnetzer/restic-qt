from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt, QModelIndex


class ResticTableModel(QAbstractTableModel):
    def __init__(self, data, parent=None):
        """
        Args:
            datain: a list of lists\n
            headerdata: a list of strings
        """
        QAbstractTableModel.__init__(self, parent)
        self.load_data(data)

    def load_data(self, data):
        self.input_dates = data[0]
        self.input_ids = data[1]

        self.column_count = 2
        self.row_count = len(self.input_dates)

    def rowCount(self, parent=QModelIndex()):
        return self.row_count

    def columnCount(self, parent=QModelIndex()):
        return self.column_count

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return ("Date", "ID")[section]

    def data(self, index, role=Qt.DisplayRole):
        column = index.column()
        row = index.row()

        if role == Qt.DisplayRole:
            if column == 0:
                return self.input_dates[row]
            elif column == 1:
                return self.input_ids[row]
        return None
