"""
The controller portion of the PypeIt Setup GUI.

.. include common links, assuming primary doc root is up one directory
.. include:: ../include/links.rst
"""

import os
from collections import deque
import re
import traceback
import enum
import glob
import numpy as np
import io
from functools import partial

from qtpy.QtCore import QAbstractTableModel, QAbstractItemModel, QAbstractListModel, QModelIndex, Qt, Signal, QObject, QThread, QStringListModel
from qtpy.QtGui import QTextDocument, QTextCursor

from configobj import ConfigObj

from pypeit import msgs, spectrographs
from pypeit.pypeitsetup import PypeItSetup
from pypeit.metadata import PypeItMetaData
from pypeit.inputfiles import PypeItFile
from pypeit.core.framematch import FrameTypeBitMask

class ModelState(enum.Enum):
    """The state values for a model object."""

    NEW = enum.auto()
    """The model is in a fresh, uninitialized state."""

    UNCHANGED = enum.auto()
    """The model contains data that has not been changed since being read from or saved to a file."""

    CHANGED = enum.auto()
    """The model contains data that has not been saved to a file."""


class OpCanceledError(Exception):
    """Exception thrown when a background operation has been canceled."""
    def __init__(self):
        super().__init__()


class LogBuffer(io.TextIOBase):
    """Imitation file object that is passed to the PypeIt msgs logging system. It maintains a buffer
    of log messages that the user can view through the GUI. It is also used to monitor progress of 
    background operations, by registering regular expressions to watch the log for.

    Args:
        log_file (str): The log file to receive the log messages. If this is None the log is not
                        written to a file.
        verbosity (int): The verbosity of log messages to pass on. 0 = No logging. 1 = INFO,
                         BUG, WARNING, and ERROR only, 2 = All.
        max_len (int,Optional):   The maximum number of log lines to buffer. Defaults to 1000.
    """

    def __init__(self, log_file, verbosity, max_len=1000):
        super().__init__()

        if log_file is not None:
            self._log = open(os.fspath(log_file), "w")
        else:
            self._log = None
        self._verbosity = verbosity
        self._watches = dict()
        self.maxlen = max_len
        self._buffer = deque([], maxlen=max_len)

    def write(self, message):
        """Simulates the write method of a file object to monitors log messages for for matching messages.
        The messages are then sent to a log file (if one has been configured).
        
        Args:
            message (str): The log message being written to the log.
        """

        # Store the message
        self._buffer.append(message)

        # Notify clients for specific watched log messages
        for watch in self._watches.items():
            re = watch[1][0]
            if re is None:
                watch[1][1](message)
            else:
                match = re.search(message)
                if match is not None:
                    watch[1][1](watch[0], match)

        # Enforce verbosity
        if self._verbosity == 0:
            return

        # Write to the log file if one was given
        if self._log is not None:
            self._log.write(message)
            self._log.flush()


    def close(self):
        """Closes the log file (if any)."""
        if self._log is not None:
            self._log.close()

    def watch(self, name, compiled_re, callback):
        """Registers a regular expression to watch the log for.
        If a log message that matches the expression is logged, the client callback 
        is called.

        Args:
            name (str):                                      Name to register the regular expression under. This can be
                                                             passed to :meth:`unwatch` to stop monitoring for that expression.
            callback (:class:`collections.abc.Callable`):    A function or object that will be called when a matching log
                                                             message is found. It is called with two arguments: the name
                                                             used to register the expression and the Match object regurned by
                                                             the regular expression.
            compiled_re (:class:`typing.Pattern`, Optional): A compiled Python regular expression to match log messages
                                                             against. If this is not given, the caller is notified of all log messages.
        """
        self._watches[name] = (compiled_re, callback)

    def unwatch(self, name):
        """Stops monitoring the log for a previously registered regular expression.

        Args:
            name (str): The name passed to :meth:`watch` to register the regular expression.
        """
        if name in self._watches:
            del self._watches[name]

    def __iter__(self):
        """Allow iteration through the log buffer.
        
        Returns:
            (:obj:`collections.abc.Iterator`): An iterator over the lines in  the log buffer."""
        return self._buffer.__iter__()

    def __len__(self):
        """Return the number of lines in the buffer.
        
        Returns:
            int
        """
        return len(self._buffer)

    def __bool__(self):
        """Return a true status indicating we're ready to receive data"""
        return True

def available_spectrographs():
    """Return a list of the supported spectrographs"""
    return spectrographs.available_spectrographs

class PypeItMetadataModel(QObject):
    """Model that wraps a PypeItMetaData object for the setup gui. This model does not
    implement the QAbstractItemModel, rather it provides an interface to proxy models that
    present the model to QAbstractItemViews.
    
    Args:
        config_name (str): The name of the unique configuration for the metadata. Defaults to 'ObsLog' for
                           all metadata rows regardless of their configuration.
        obslog_model (PypeItMetadataModel): A reference to the PypeItMetadataModel for the obslog. Defaults to None
                                            for the ObsLog model itself.
        metadata (PypeItMetaData): The PypeItMetadata object being wrapped. This is None when the model is in a 
                                   "NEW" state. Defaults to None.
    """

    modelReset = Signal()
    """Signals when underlying PypeItMetadata object has been changed/reset."""

    dataChanged = Signal(int, int)
    """Signals when data has been modified but columns/rows have not changed."""

    rowsAdded = Signal(int, int)
    """Signals when a row has been added to this model."""

    rowsRemoved = Signal(int, int)
    """Signals when a row has been removed from this model."""

    def __init__(self, config_name='ObsLog', obslog_model= None, metadata=None):
        super().__init__()
        self.metadata = metadata
        self.config_name = config_name
        self.obslog_model=obslog_model if config_name != 'ObsLog' else self
        self.configs = dict()

    def setMetadata(self, metadata):
        """Sets the PypeItMetaData object being wrapped.
        
        Args:
            metadata (PypeItMetaData): The metadata being wrapped.
        """
        self.metadata=metadata
        self.modelReset.emit()

    def addNewConfig(self, config_name, model):
        """
        Add a new configuration to the list of configurations known to the obslog model.

        Args:
            config_name (str): The name of the new configuration.
            model (PypeItMetaDataModel): The model for that configuration.
        """
        self.configs[config_name] = model

    def getDefaultColumns(self):
        """Return the default columns to display to the user. This can vary based
        on the current spectrograph.
        
        Return:
        A list of column names, in order to display.
        """
        if self.metadata is not None:
            default_columns = self.metadata.set_pypeit_cols(write_bkg_pairs=True)
            # The GUI also wants setup
            default_columns.insert(1,'setup')
            return default_columns
        else:
            return ['filename', 'setup', 'frametype', 'ra', 'dec', 'target', 'dispname', 'decker', 'binning', 'mjd', 'airmass', 'exptime']

    def getCopyForConfig(self, config_name):
        """
        Create a copy of this Metadata object for rows with the given configuration.
        """
        msgs.info(f"Creating new copy for config {config_name}")

        config_rows = [ config_name in setup for setup in self.metadata.table['setup'] ]
        table_copy = self.metadata.table[config_rows].copy(True)                
        copy = PypeItMetadataModel(metadata=PypeItMetaData(self.metadata.spectrograph, self.metadata.par, data=table_copy), 
                                   config_name = config_name,
                                   obslog_model=self.obslog_model)
        self.obslog_model.addNewConfig(config_name, copy)
        return copy
    
    def getCopyForNewConfig(self, config_rows, config_name):
        
        # Add the new config to each row
        for row_index in config_rows:
            row = self.metadata.table[row_index]
            
            current_setups = row['setup'].split(",")
            current_setups.append(config_name)

            self.obslog_model.updateRowConfig(row, ",".join(current_setups))

        return self.getCopyForConfig(config_name)

    def removeFile(self, directory, filename):
        row_index = (self.metadata.table['directory'] == directory) & (self.metadata.table['filename'] == filename)
        self.metadata.table.remove_rows(row_index)

        rows = np.where(row_index)[0]
        msgs.info(f"Removing file from config {self.config_name}, file {filename} rows {rows}")

        # There should only be one row that matches, but just in case we loop
        for idx in rows:
            self.rowsRemoved.emit(idx,idx)

    def updateFileSetup(self, directory, filename, value):
        row_index = (self.metadata.table['directory'] == directory) & (self.metadata.table['filename'] == filename)
        self.metadata.table['setup'][row_index] = value
        rows = np.where(row_index)[0]
        msgs.info(f"Updating file setup for config {self.config_name}, file {filename} rows {rows} to {value}")

        # There should only be one row that matches, but just in case we loop
        for idx in rows:
            self.dataChanged.emit(idx, idx)

    def addMetadataRow(self, metadata_row):
        file = metadata_row['filename']
        directory = metadata_row['directory']
        setup = metadata_row['setup']
        msgs.info(f"Adding row {directory}/{file} with setup {setup} to {self.config_name}")

        new_index = len(self.metadata.table)
        self.metadata.table.add_row(metadata_row)
        file = self.metadata[new_index]['filename']
        directory = self.metadata[new_index]['directory']
        setup = self.metadata[new_index]['setup']
        msgs.info(f"Post add row {directory}/{file} with setup {setup} to {self.config_name} row {new_index}")
        self.rowsAdded.emit(new_index, new_index)

    def updateRowConfig(self, metadata_row, value):
        file = metadata_row['filename']
        directory = metadata_row['directory']
        msgs.info(f"Updating row config {directory}/{file} to '{value}'")
        new_config_list = sorted(value.split(','))
        if "" in new_config_list:
            new_config_list.remove("")

        new_setup_value = ",".join(new_config_list)

        current_config_list = sorted(metadata_row["setup"].split(","))
        msgs.info(f"current_configs: {current_config_list} new configs {new_config_list}")

        # The metadata_row passed in hasn't been changed yet, so do that now
        metadata_row['setup'] = new_setup_value

        if new_config_list == current_config_list:
            # Do nothing, the lists are the same
            return

        for current_config in current_config_list:
            if current_config not in new_config_list:
                # Remove this row from configs it's no longer a member of
                self.configs[current_config].removeFile(directory, file)
            else:
                # Update configs that the row is currently a member of
                self.configs[current_config].updateFileSetup(directory,file,new_setup_value)

        for new_config in new_config_list:
            # A brand new config won't be in our current list of configurations yet.
            # so don't try to update it
            if new_config in self.configs:
                # Add the row to a config that previously did not have             
                if new_config not in current_config_list:
                    self.configs[new_config].addMetadataRow(metadata_row)

        # This method is only called on the obslog model, which should get the new value
        self.updateFileSetup(directory, file, new_setup_value)


    def setValue(self, colname, row, value):
        msgs.info(f"Setting {colname} row {row} to '{value}'")
        if colname == "setup":
            # Changing the setup means moving a file between different PypeIt files,
            # which affects things outside of this model, so we forward this to the
            # obslog model
            row_to_move = self.metadata.table[row]
            self.obslog_model.updateRowConfig(row_to_move, value)
        else:
            self.metadata.table[colname][row] = value
            self.dataChanged.emit(self.metadata.table.colnames.index(colname), row)

class PypeItMetadataUniquePathsProxy(QAbstractListModel):
    """A Proxy model filtering the content of a PypeItMetadata model to only show the
    unique paths within it to Qt views.
    
    Args:
        metadata_model (PypeItMetadata): The model being filtered.
    """
    def __init__(self, metadata_model):
        super().__init__()
        self.source_model = metadata_model
        self._setUniqueIndex()
        self.source_model.modelReset.connect(self._setUniqueIndex)
        self.source_model.rowsAdded.connect(self._setUniqueIndex)
        self.source_model.rowsRemoved.connect(self._setUniqueIndex)
        self.source_model.dataChanged.connect(self._setUniqueIndex)

    def _setUniqueIndex(self, *args, **kwargs):
        """Sets the Numpy index array for the unique paths within the metadata."""
        self.beginResetModel()
        
        if self.source_model.metadata is not None:
            items, self._unique_index = np.unique(self.source_model.metadata['directory'],return_index=True)
        else:
            self._unique_index = []

        self.endResetModel()
    
    def rowCount(self, parent_index=QModelIndex()):
        """Returns the number of unique paths. Inherited from QAbstractItemModel."""
        return len(self._unique_index)
    
    def data(self, index, role):
        """Returns the path for a given QModelIndex.
        
        Args:
            index (QModelIndex):   The QModelIndex for the row to get data for.
            role (Qt.DisplayRole): The role to return data for. This method only supports "DisplayRole".
        """
        if role == Qt.DisplayRole:
            if index.isValid() and self.source_model.metadata is not None and index.row() < len(self._unique_index):
                return str(self.source_model.metadata['directory'][self._unique_index][index.row()])

        return None    


class PypeItMetadataProxy(QAbstractTableModel):
    """
    Provides a proxy Qt model interface for a PypeItMetadata object.  This proxy implements
    a QAbstractItemModel interface to present file metadata
    in a PypeItMetadataModel to Qt views. It filters the columns visible to the view based on the
    columns typically present in a PypeItFile.

    It also supports editing. Edits are propagated to other proxies by the PypeItMetadataModel's signals.

    Args:
        source_model (PypeItMetadataModel): The model this proxy is wrapping.
    """
    def __init__(self, source_model):
        super().__init__()

        self.source_model = source_model
        self.editable_columns=['calib', 'comb_id', 'bkg_id', 'frametype', 'setup']

        self.colnames = []
        self.reset()
        
        # Notify views when the underlying model changes
        source_model.dataChanged.connect(self._sourceDataChanged)

        # Reset if the source structure changes
        source_model.modelReset.connect(self.reset)

        source_model.rowsAdded.connect(self._forwardRowsInserted, Qt.ConnectionType.DirectConnection)
        source_model.rowsRemoved.connect(self._forwardRowsRemoved, Qt.ConnectionType.DirectConnection)

    def _forwardRowsInserted(self, start_row, end_row):
        msgs.info(f"Signalling inserted rows from {start_row} to {end_row}")
        self.rowsInserted.emit(QModelIndex(), start_row, end_row)

    def _forwardRowsRemoved(self, start_row, end_row):
        msgs.info(f"Signalling removed rows from {start_row} to {end_row}")
        self.rowsInserted.emit(QModelIndex(), start_row, end_row)
                               
    def _sourceDataChanged(self, col, row):
        self.dataChanged.emit(self.index(row, col, parent=QModelIndex()),
                              self.index(row, col, parent=QModelIndex()))


    def getColumnFromName(self, colname):
        if colname in self.colnames:
            return self.colnames.index(colname)
        else:
            return -1

    def getColumnName(self, index):
        return self.colnames[index.column()]

    def getAllFrameTypes(self):
        return FrameTypeBitMask().keys()

    def rowCount(self, parent_index=QModelIndex()):
        """Returns number of rows under a parent. Overridden method from QAbstractItemModel.
        
        Args:
            parent_index (QModelIndex): The index of the parent. Not applicable to a table model
                                        as there's no parent/child heirarchy.

        Returns:
            int: The number of rows in the table.
        """
        if (parent_index.isValid() or # Per Qt docs for a table model
            self.source_model.metadata is None):
            return 0
        else:
            return len(self.source_model.metadata)

    def columnCount(self, parent_index=QModelIndex()):
        """Returns number of columns in under a parent. Overridden method from QAbstractItemModel. 

        Args:
            parent_index (QModelIndex): The index of the parent. Not applicable to a table model
                                        as there's no parent/child heirarchy.

        Returns:
            int: The number of columns in the table.
        """
        if parent_index.isValid():
            # Per Qt docs for a table model
            return 0
        else:
            return len(self.colnames)

    def data(self, index, role):
        """Returns data for a given role at a given index. Overridden method from QAbstractItemModel. 
        
        Args:
            index (QModelIndex): The index in the table to return data form.
            role (Qt.DisplayRole): The role to return data for. This method supports the "TextAlignmentRole"
                                   for returning alignment information for a table cell, and the "DisplayRole"
                                   for displaying the data within a table cell.

        Return:
            Object: The requested data, or None if there is no applicable data.
        """

        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft

        elif role != Qt.DisplayRole or self.source_model.metadata is None or index.row() > len(self.source_model.metadata) or index.column() > len(self.colnames):
            return None # Nothing to display at this index
            
        else:
            # The columns being displayed are a subset of the metadata,
            # So we use the column name instead of the index
            colname = self.colnames[index.column()]
            value = self.source_model.metadata[colname][index.row()]
            # Round floating point values to look better
            if isinstance(value, np.float64) or isinstance(value, np.float32):
                value = round(value, 3)
            return str(value)

    def setData(self, index, value, role=Qt.EditRole):
        if role==Qt.EditRole and self.source_model.metadata is not None:
            colname = self.colnames[index.column()]
            if colname in self.editable_columns:
                try:             
                    self.source_model.setValue(colname, index.row(), value)
                    return True
                except ValueError as e:
                    msgs.warn(f"Failed to set {colname} row {index.row()} to '{value}': {e}")

        return False

    def flags(self, index):
        base_flags = super().flags(index)
        if self.colnames[index.column()] in self.editable_columns:
            base_flags |= Qt.ItemFlag.ItemIsEditable
        return base_flags

    def headerData(self, section, orientation, role):
        """Display header data for the table. For columns we give a column name, for rows we return
        a number. Overridden method from QAbstractItemModel.

        Args:
            section (int): The "section" the header is used for. For table models this is the 
                           zero based row or column number.
            orientation (Qt.Orientation): Whether the horizontal (column header) or vertical (row header)
                                          is being requested.
            role (Qt.Role): The role header data is being requested for. This method supports
                            Qt.InitialSortOrderRole and Qt.DisplayRole.

        Returns:
            str: The name for the column/row, or None if there is no applicable name for the given section/orientation/role.
        """
        if role == Qt.DisplayRole:
            # Display the actual name of the header row/column
            if orientation == Qt.Orientation.Horizontal and section < len(self.colnames):
                # Columns have propper names
                return self.colnames[section]
            else:
                return " "
        else:
            # A non-applicable role or a sort order request for a column that we're not sorted by.
            return None

    def reset(self):
        """
        Reset the proxy assuming the metadata object has completely changed
        """
        # Tell views a model reset is happening
        super().beginResetModel()

        # Reset column names
        self.colnames = self.source_model.getDefaultColumns()

        if ('setup') not in self.colnames:
            self.colnames.insert(1, 'setup')

        super().endResetModel()

class _UserConfigTreeNode:
    """
    Internal class used to represent the tree structure of PypeIt parameters.
    It is used as the internal pointer in PypeItParamsProxy.

    Take this example config::

        [rdx]
            spectrograph = shane_kast_blue
        [calibrations]
            bpm_usebias = true
            [[biasframe]]
                frametype = bias

    The resulting data structure is::

        Node 1: 
            parent = None
            key = None
            value = None
            children = [Node 2, Node 4]
        Node 2:
            parent = None
            key = "rdx"
            value = None
            children = [Node 3]
        Node 3:
            parent = Node 2
            key = "spectrograph"
            value = "shane_kast_blue"
            children = []
        Node 4:
            parent = None
            key = "calibrations"
            value = None
            children = [Node 5, Node 6]
        Node 5:
            parent = Node 4
            key = "bpm_usebias"
            value = True
            children = []
        Node 6:
            parent = Node 4
            key = biasframe
            value = None
            children = [Node 7]
        Node 7:
            parent = Node 6
            key = frametype
            value = bias
            children = []

    Of note is that the "root" in the data model used by Qt is an invalid entry, i.e. it isn't shown in 
    the view as a node. This matches the PypeIt parameters format in that there can be multiple
    top level entries (e.g. [rdx] and [calibrations] above). This is why nodes 2 and 4 have parent = None 
    even though Node 1 is their parent in the data structure. It prevents them from reporting a parent node to Qt and 
    causing issues.

    Args:
        node (dict or value):  The data for a node within a tree. If it's a dict, this
                               is a parent node with no value but each entry in the dict
                               is a child. Otherwise it's treated as a value 
                               for the given key.
        key (str): Name of the value or section (e.g. "rdx" or "spectrograph"). If None, this is the
                   root entry which has no equivalent in Qt.
        parent (_UserConfigTreeNode): The parent of this entry. None if the entry is the root entry or
                                      a top level entry.
        
    """
    def __init__(self, node, key=None, parent=None):
        
        self.parent = parent
        self.key = key
        if isinstance(node, dict):
            self.children = [_UserConfigTreeNode(key=k, node=node[k], parent=self if key is not None else None) for k in node.keys()]
            self.value=None
        else:
            self.value=node
            self.children = []

    def getConfigLines(self, level=0):
        indent = " " * (level-1)
        if len(self.children) == 0:
            return [f"{indent}{self.key} = {self.value}"]
        else:
            if self.key is not None:                
                lines = [ f"{indent}{'['*level}{self.key}{']'*level}"]
            else:
                # Only the root node should have a None key
                lines = []

            for child in self.children:
                lines += child.getConfigLines(level+1)

            return lines

class PypeItParamsProxy(QAbstractItemModel):
    """
    A Proxy model that maps a PypeIt :class:`PypeItPar` to a QAbstractItemModel suitable for a Qt QTreeView.
    It uses the _UserConfigTreeNode recursive data structure to represent the parameters.

    Args:
        pypeit_setup (PypeItSetup): The PypeItSetup object containing the parameters to represent.

    """
    def __init__(self, pypeit_setup):
        super().__init__(None)

        # TODO is this needed? Currently self.par isn't used but maybe it could be used
        # to show default values to clients? Or help info?
        self.par = pypeit_setup.par 
        self._userConfigTree = _UserConfigTreeNode(ConfigObj(pypeit_setup.user_cfg))

    def getConfigLines(self):
        return self._userConfigTree.getConfigLines()

    def rowCount(self, parent=QModelIndex()):
        """
        Returns the number of items under a parent node. Overridden from QAbstractItemModel.
        
        Returns:
            int: The number of items under parent. Can be 0 if parent has no child items.

        """
        if not parent.isValid():
            # If parent is invalid, it's the top level of the tree
            node = self._userConfigTree
        else:
            # Otherwise, if the parent is an index created by the index() method, it
            # points to the parent node in its internalPointer()
            if parent.column() == 1:
                # Column 1 does not have children
                return 0

            #msgs.info("rowCount valid")
            node = parent.internalPointer()

        return len(node.children)

    def index(self, row, column, parent=QModelIndex()):
        """
        Creates a QModelIndex that points to an item in the PypeItPar parameter tree. Overridden from QAbstractItemModel.
        
        Args:
            row    (int): The row of the item underneath parent to create an index for.

            column (int): The column of the item. Typically 0 is used for the name of the :class:`PypeItPar` or 
                          value, and 1 is used for actual parameter values (1 is never used for a :class:`PypeItPar`).

            parent (QModelIndex): An index for the parent. If this is invalid, it refers to the root of the tree.

        Returns:
            QModelIndex: A new index object to point to the item.
        
        """
        if not parent.isValid():
            # Use the root of the config tree as the parent
            parent_node = self._userConfigTree
        else:
            if parent.column() == 1:
                # Column one does not have children
                return QModelIndex()

            # The parent is valid, we're creating an index to one of its children
            # Get the parent from the internal data created by this method earlier.
            parent_node = parent.internalPointer()


        # Find the child using the passed in row
        child_node = parent_node.children[row]

        # Create the index, using child_node as the intenralPointer
        return super().createIndex(row, column, child_node)

    def data(self, index, role=Qt.DisplayRole):
        """Returns data for a given index. Overridden from QAbstractItemModel.

        Args:
            index (QModelIndex): The index of the item, as returned by index()

            role (Qt.ItemDataRole): The role of the data being requested. This method supports
                                    Qt.DisplayRole (for displaying text).
        
        
        Returns: 
            str: A string if there's something to display at the given index and role, or
                 None if there's nothing to display.
        """
        if role == Qt.DisplayRole:
            if index.column() == 0:
                # Display the name (aka key) of the item
                # This is the reason for including the key in the UserConfigTreeNode.
                return index.internalPointer().key
            else:
                # Display the value, which will be None if the index isn't
                # pointing to a leaf node
                value = index.internalPointer().value
                if value is not None:
                    return str(value)

        return None

    def headerData(self, section, orientation, role):
        """Return data for the header row of the :class:`PypeItPar` tree.  For the horizontal
        header we call section 0 aka column 0 "Setting" and section 1 aka column 1 "Value".

        Args:
            section (int): The section aka column of the header.
            orientation(Qt.Orientation): The orientation of the header. This model only supports
                                         the horizontal header row.
            role (Qt.DisplayRole): The display role of the data to return. Only Qt.DisplayRole is supported
                                   for showing the text labels of the header.

        Returns:
            str: The name of a column or None if headerData isn't applicable for the
                 section/orientation/role passed in.
        
        """
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if section == 0:
                return "Setting"
            elif section == 1:
                return "Value"
        return super().headerData(section, orientation, role)


    def columnCount(self, parent):
        """Return the number of columns, which is always 2 because we use column 0 for the name of the
        parameter or :class:`PypeItPar` and column 1 for the configuration values. 
        Overridden from QAbstractItemModel.

        Args:
        parent (QModelIndex): Parent to return the column count for. (Not used)

        Return:
            int: The number of columns. Always 2.        
        """
        return 2

    def parent(self, index):
        """Return the parent of an item in the model. Overridden from QAbstractItemModel.

        Args:
            index (QModelIndex): The index of the item, as returned by the index() method.

        Returns: 
            QModelIndex: An index for the items parent. Maybe be invalid if the item is at the top level.
        """
        # This method is why the parent node is included in the _UserConfigTreeNode data.
        node = index.internalPointer()
        if node is None or node.parent is None:
            # Root node or top level node, there is no parent
            return QModelIndex()
        else:
            # Need to know the row # for the parent, which is in the grandparent
            grandparent = node.parent.parent
            if grandparent is None:
                # The grandparent is the root node
                grandparent = self._userConfigTree

            parent_and_siblings = [x.key for x in grandparent.children ]
            row = parent_and_siblings.index(node.parent.key)
            # Column is always 0, because 1 is reserved for leaf nodes which can't be parents
            return super().createIndex(row, 0, node.parent)

class ObservingConfigModel(QObject):
    """A model representing an observing configuration, which contains a spectrogrpah and configuration values.

    Args:
        spectrograph (Spectrograph): The spectrograph used for the observation.
        config_dict (dict): The configuration values for the observation.
    """
    def __init__(self, config_name, config_keys, config_dict):
        self.name = config_name
        self.config_keys = config_keys
        self.config_dict = config_dict


    @property
    def spectrograph(self):
        """str: Get the spectrograph name for this observing config."""
        return self._spectrograph.name

    def get_config_keys(self):
        """Return the configuration keys for this observing config. They are returned
        in the order they are displayed in by the view.
        Returns:
            list of str: The configuration keys for this observing config.
        """
        return self._spectrograph.configuration_keys()

class PypeItFileModel(QObject):
    """
    A model representing the contents of a single .pypeit file. This involves a spectrograph, configuration values, 
    file metadata, and PypeIt parameters.

    Args: 
        pypeit_setup (PypeItSetup): The PypeItSetup object this configuration is a part of.
        config_name (str):  The name of this configuration.
        config_dict (dict): The metadata for this configurations, as returned by PypeItMetadata.unique_configurations.
        state (ModelState): The state of the model.  "CHANGED" if it was built by running setup or "UNCHANGED" if it came from loading
                            an existing .pypeit file.
    """

    state_changed = Signal(str)
    """Signal(str): Signal sent when the state of the file model changes. The config nasme of the file is sent as the signal parameter."""

    def __init__(self, config_name, config_dict, spectrograph, metadata_model, params_model, state):
        super().__init__()
        self._spectrograph = spectrograph
        self.config_name = config_name 
        self.metadata_model = metadata_model
        self.params_model = params_model
        self.save_location = None
        self.state = state

        # Build a list of the configuration key/value pairs, to avoid displaying them in the
        # arbitrary order chosen by the dict
        self.config_values = [(key, config_dict[key]) for key in self._spectrograph.configuration_keys()]

        # Create a new proxy metadata model 
        self.metadata_proxy_model = PypeItMetadataProxy(metadata_model)

        # A paths model for the paths in this PypeIt file
        self.paths_model = PypeItMetadataUniquePathsProxy(metadata_model)

    @property
    def filename(self):
        """Return the name of the pypeit file.
        """
        save_dir = "" if self.save_location is None else os.path.join(self.save_location ,  f"{self._spectrograph.name}_{self.config_name}")
        return os.path.join(save_dir, f"{self._spectrograph.name}_{self.config_name}.pypeit")

    @property
    def spectrograph(self):
        return self._spectrograph.name

    def save(self):
        """Save a .pypeit file from this model. The file name is chosen per PypeIt standards, and the
        location must be set before calling this method.
        """
        try:
            self.metadata_model.metadata.write_pypeit(self.save_location, cfg_lines=self.params_model.getConfigLines(),
                                                      configs = [self.config_name], write_bkg_pairs=True)
        except Exception as e:
            msgs.warn(f"Failed saving setup {self.config_name} to {self.save_location}.")
            msgs.warn(traceback.format_exc())
            # Raise an exception that will look nice when displayed to the GUI
            raise RuntimeError(f"Failed saving setup {self.config_name} to {self.save_location}.\nException: {e}")
        self.state = ModelState.UNCHANGED
        self.state_changed.emit(self.config_name)
        

class PypeItSetupModel(QObject):
    """Model representing a PypeItSetup object to the GUI.
    """

    operation_progress = Signal(str)
    """Signal(str): Signal that indicates a background operation has progressed. Sends a string describing the progress, 
                    e.g. a file name that had it's metadata read."""

    operation_complete = Signal(str)
    """Signal(str): Signal that indicates a background_operation completed. Sends an error message if it failed,
                    `"CANCEL"` if it was canceled, or an empty string if it succeeded."""

    configs_deleted = Signal(list)
    """Signal(list): Signal sent when configurations within the setup have been deleted. Sends the list of
                     removed configurations."""

    configs_added = Signal(list)
    """Signal(list): Signal sent when configurations within the setup have been added. Sends the list of added
                     configurations."""

    spectrograph_changed = Signal(str)
    """Signal(str): Signal sent when the spectrgraph for the setup has changed. Sends the name of the new spectrograph."""

    state_changed = Signal()
    """Signal(): Signal sent when the state attribute of the model has changed."""

    def __init__(self):
        super().__init__()
        self._spectrograph = None
        self._pypeit_setup = None
        self.metadata_model = PypeItMetadataModel()
        self.obslog_model = PypeItMetadataProxy(self.metadata_model)
        self.paths_model = QStringListModel()
        self.raw_data_files = []
        self.pypeit_files = dict()
        self.log_buffer = None
        self.default_extension = ".fits"

    def setup_logging(self, logname, verbosity):
        """
        Setup the PypeIt logging mechanism. Also setups the
        LogWatcher mechanism for monitoring the log.

        Args:
            logname (str): The filename to log to.
            verbosity (int): The verbosity level to log at.
        """
        self.log_buffer = LogBuffer(logname,verbosity)
        msgs.reset(verbosity=verbosity, log=self.log_buffer, log_to_stderr=False)


    @property
    def state(self):
        """ModelState: The state of the model.
        """
        if len(self.pypeit_files.values()) == 0:
            return ModelState.NEW
        else:
            if any([config.state!=ModelState.UNCHANGED for config in self.pypeit_files.values()]):
                return ModelState.CHANGED
            else:
                return ModelState.UNCHANGED

    def set_spectrograph(self, new_spec):
        """Set the current spectrograph.

        Args:
            new_spec (str): The name of the new spectrograph.
        """
        msgs.info(f"Spectrograph is now {new_spec}")
        self._spectrograph = spectrographs.util.load_spectrograph(new_spec)
        self.spectrograph_changed.emit(self._spectrograph.name)

    @property
    def spectrograph(self):
        """str: The name of the current spectrograph. """
        return None if self._spectrograph is None else self._spectrograph.name

    @property
    def raw_data_directories(self):
        """list of str: The list directories containing raw data for the PypeItSetup object."""
        return self.paths_model.stringList()

    def add_raw_data_directory(self, new_directory):        
        """
        Adds a new directory to the model's list of directories.

        Args:
            new_directory (str): The new directory containing raw data.        
        """
        msgs.info(f"Adding raw directory: {new_directory}, current spec is {self._spectrograph}")
        if new_directory not in self.paths_model.stringList():
            row_number = self.paths_model.rowCount()
            self.paths_model.insertRows(row_number, 1)
            self.paths_model.setData(self.paths_model.index(row_number,0),new_directory)

    def scan_raw_data_directories(self):
        """
        Scans all of the raw data directories for raw data files.

        Returns:
            int: The number of raw data files found.
        """
        allowed_extensions = self._spectrograph.allowed_extensions
        if allowed_extensions is None or len(allowed_extensions) == 0:
            # Most spectrographs don't set the allowed extensions, just use the
            # default from the command line. Append a "*" to match compressed files
            allowed_extensions = [self.default_extension + "*"]

        self.raw_data_files = []
        for directory in self.paths_model.stringList():
            msgs.info(f"Scanning directory: {directory}")
            for extension in allowed_extensions:
                #  The command line may set a root, which isn't a directory but a prefix
                if not os.path.isdir(directory):
                    glob_pattern = directory + "*" + extension
                else:
                    glob_pattern = os.path.join(directory, "*" + extension)

                msgs.info(f"Searching for raw data files with {glob_pattern}")
                self.raw_data_files += glob.glob(glob_pattern)

        return len(self.raw_data_files)


    def reset(self):
        """Reset the model to an empty state."""

        msgs.info(f"Resetting to empty setup.")
        self._pypeit_setup = None
        self.raw_data_files = []
        self.raw_data_dirs = []
        self.metadata_model.setMetadata(None)     
        self.paths_model.setStringList([])
        self._spectrograph = None
        self.spectrograph_changed.emit(None)
        self._setConfigurations({})
        self.state_changed.emit()

    def run_setup(self):
        """Run setup on the raw data in this setup. This function is ran as a background 
        operation.
        """
        try:
            self._pypeit_setup = PypeItSetup.from_rawfiles(self.raw_data_files, self._spectrograph.name)

            added_metadata_re = re.compile("Adding metadata for (.*)$")

            self.log_buffer.watch("added_metadata", added_metadata_re, self._addedMetadata)

            # These were taken from the default parameters in pypeit_obslog
            self._pypeit_setup.run(setup_only=True,
                                write_files=False, 
                                groupings=True,
                                clean_config=False)
            self.log_buffer.unwatch("added_metadata")

            self.metadata_model.setMetadata(self._pypeit_setup.fitstbl)
            self.paths_model.setStringList(np.unique(self._pypeit_setup.fitstbl.table['directory']))
            self._setConfigurations(self._pypeit_setup.fitstbl.unique_configurations())
            self.operation_complete.emit("")
            self.state_changed.emit()
        except OpCanceledError:
            # The operation was canceled, reset pypeit_setup and return
            self.log_buffer.unwatch("added_metadata")
            msgs.info("OpCanceled")
            self._pypeit_setup = None
            self.operation_complete.emit("CANCEL")
        except Exception as e:
            self.log_buffer.unwatch("added_metadata")
            msgs.info("Exception")
            msgs.info(traceback.format_exc())
            # Any other exception is an error reading the metadata
            self._pypeit_setup = None
            self.operation_complete.emit("Could not read metadata. Are you sure the spectrograph is set correctly?\nCheck the logs for more information.")

    def open_pypeit_file(self, pypeit_file):
        """Open an existing pypeit file and load it into this setup.

        Args:
            pypeit_file (str): The pypeit file to open.
        """
        
        # We can't just create a PypeItSetup using from_pypeit_file because we 
        # need the paths for raw_data_directory.
        pf = PypeItFile.from_file(pypeit_file)

        if len(pf.file_paths) == 0:
            raise ValueError(f"PypeIt input file {pypeit_file} is missing a path entry.")

        self._pypeit_setup = PypeItSetup(pf.filenames,
                                         usrdata=pf.data,
                                         setups=[pf.setup_name],
                                         cfg_lines=pf.cfg_lines,
                                         pypeit_file=pypeit_file,
                                         setup_dict=pf.setup)

        # Setup our proxy models and notify the view widgets
        self._pypeit_setup.build_fitstbl()        
        self._pypeit_setup.fitstbl.set_configurations(fill=pf.setup_name)
        self._pypeit_setup.fitstbl.get_frame_types(user=dict(zip(pf.data['filename'], pf.data['frametype'])))
        self.paths_model.setStringList(np.unique(self._pypeit_setup.fitstbl.table['directory']))
        self.metadata_model.setMetadata(self._pypeit_setup.fitstbl)        
        self._spectrograph = self._pypeit_setup.spectrograph
        self.spectrograph_changed.emit(self.spectrograph)
        self._setConfigurations(self._pypeit_setup.fitstbl.unique_configurations(), state=ModelState.UNCHANGED)
        self.state_changed.emit()

    def removeConfig(self, name):
        del self.pypeit_files[name]
        self.configs_deleted.emit([name])

    def createNewPypeItFile(self, config_name, selectedRows):
        # Create a new empty configuration.
        # First figure out the name
        # This is assuming a single letter name
        if len(self.pypeit_files) == 0:
            # Now configs, just add "A"
            new_name = "A"
        else:
            largest_name = max(self.pypeit_files.keys())
            if largest_name == 'z':
                raise ValueError("Failed to create new setup because there are too many loaded.")
            new_name = chr(ord(largest_name)+1)
        msgs.info(f"Creating new pypeit file model for {new_name}")

        # Get the metadata model for the given config_name
        if config_name == 'ObsLog':
            model = self.metadata_model
        else:
            model = self.pypeit_files[config_name].metadata_model

        # Get the configuration for the first row
        config_dict = model.metadata.get_configuration(selectedRows[0])
        # TODO warn about mismatches in other rows?

        pf_model = PypeItFileModel(new_name, 
                                   config_dict, 
                                   self._spectrograph, 
                                   model.getCopyForNewConfig(selectedRows, new_name),
                                   PypeItParamsProxy(self._pypeit_setup),
                                   state=ModelState.NEW)

        pf_model.state_changed.connect(self.state_changed)

        self.pypeit_files[new_name] = pf_model            

        self.configs_added.emit([pf_model])
        self.state_changed.emit()

    def _addedMetadata(self, name, match):
        """Callback used to report progress on reading files when running setup."""
        if QThread.currentThread().isInterruptionRequested():
            raise OpCanceledError()

        self.operation_progress.emit(match.group(1))

    def _setConfigurations(self, unique_configs, state=ModelState.CHANGED):
        """
        Private method to reset configurations to a new set. Any previous configurations are deleted.

        Args:
            unique_config (dict): A the new configurations to set.

            state (ModelState, Optional): The state of the new model. Defaults to CHANGED, meaning it has not been saved.

        """
        msgs.info(f"Unique Configs {unique_configs}")

        # Delete previous configurations
        deleted_configs = list(self.pypeit_files.keys())
        if len(deleted_configs) > 0:
            self.configs_deleted.emit(deleted_configs)

        # Create a new PypeItFileModel for each unique configuration
        config_names = list(unique_configs.keys())
        self.pypeit_files = dict()
        for config_name in config_names:
            pf_model = PypeItFileModel(config_name, 
                                       unique_configs[config_name], 
                                       self._spectrograph, 
                                       self.metadata_model.getCopyForConfig(config_name),
                                       PypeItParamsProxy(self._pypeit_setup),
                                       state=state)

            # Any change to the file models can change the over all state, so connect the signals
            pf_model.state_changed.connect(self.state_changed)
            self.pypeit_files[config_name] = pf_model

        msgs.info(f"Self configs: {self.pypeit_files}")
        if len(config_names) > 0:
            self.configs_added.emit(list(self.pypeit_files.values()))