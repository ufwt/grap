#!/usr/bin/env python
# Inspired by IDAscope.


import threading

from pygrap import graph_free

import idagrap.ui.helpers.QtShim as QtShim
import idc
from idagrap.config.General import config

QMainWindow = QtShim.get_QMainWindow()


class CryptoIdentificationWidget(QMainWindow):
    """Cryptographic identification Widget.

    This is the core of the the cryptographic identification widget.

    Attributes:
        cc (ClassCollection): Collection of many classes.
        parent (QWidget): The parent QWidget.
        central_widget (QWidget): QWidget of this widget.
        signature_widget (QWidget): Table for the found crypto.
        name (str): Name of the widget.
        icon (QIcon): Icon for the widget.
        scanGraphAction (QAction): Toolbar action.
        signature_tree (QTreeWidget): Tree of the signature table.
        qtreewidgetitems_to_addresses (QTreeWidgetItem:int dict): Dictionary
                    that links together QtTreeWidgetItem and the start
                    address of the related match pattern.

    Arguments:
        parent (QWidget): The parent QWidget.

    """

    def __init__(self, parent):
        """Initialization."""
        # Initialization
        self.cc = parent.cc
        self.cc.QMainWindow.__init__(self)
        print "[|] loading CryptoIdentificationWidget"

        # Enable access to shared IDAscope modules
        self.parent = parent
        self.name = "Crypto"
        self.icon = self.cc.QIcon(config['icons_path'] + "crypto.png")

        # This widget relies on the crypto identifier
        self.central_widget = self.cc.QWidget()
        self.setCentralWidget(self.central_widget)
        self._createGui()

    def _createGui(self):
        """
        Setup function for the full GUI of this widget.
        """
        # Toolbar
        self._createToolbar()

        # Signature widget
        self._createSignatureWidget()

        # Layout and fill the widget
        crypto_layout = self.cc.QVBoxLayout()
        splitter = self.cc.QSplitter(self.cc.QtCore.Qt.Vertical)
        q_clean_style = self.cc.QStyleFactory.create('Plastique')
        splitter.setStyle(q_clean_style)
        splitter.addWidget(self.signature_widget)
        crypto_layout.addWidget(splitter)

        self.central_widget.setLayout(crypto_layout)

    def _createToolbar(self):
        """
        Creates the toolbar, containing buttons to control the widget.
        """
        self._createScanGraphAction()
        self.toolbar = self.addToolBar('Crypto Identification Toolbar')
        self.toolbar.addAction(self.scanGraphAction)

    def _createScanGraphAction(self):
        """
        Create an action for the scan button of the toolbar and connect it.
        """
        # Action
        self.scanGraphAction = self.cc.QAction(
            self.cc.QIcon(config['icons_path'] + "scan_graph.png"),
            "Generating and scanning the control flow graph(might take some time)",
            self
        )

        self.scanGraphAction.triggered.connect(self._onScanGraphBouttonClickedThread)

    def _onScanGraphBouttonClickedThread(self):

        thread = threading.Thread(target=self._onScanGraphBouttonClicked)
        thread.start()

    def _onScanGraphBouttonClicked(self):
        """
        The logic of the scan button from the toolbar.
        Uses the scanning functions of in CryptoIdentifier and updates the
        elements displaying the results.
        """
        #
        # Crypto Widget
        #

        # Analyzing
        self.cc.CryptoIdentifier.analyzing()

        # Update the UI
        self.populateSignatureTree()

    def _createSignatureWidget(self):
        """
        Create the widget for the signature part.
        """
        # Initizalition of the table
        self.signature_widget = self.cc.QWidget()
        signature_layout = self.cc.QVBoxLayout()
        self.signature_tree = self.cc.QTreeWidget()
        self.signature_tree.setColumnCount(1)
        self.signature_tree.setHeaderLabels(["Found Crypto Signatures"])

        # Action
        self.signature_tree.itemDoubleClicked.connect(self._onSignatureTreeItemDoubleClicked)

        signature_layout.addWidget(self.signature_tree)
        self.signature_widget.setLayout(signature_layout)

    def populateSignatureTree(self):
        """
        populate the TreeWidget for display of the signature scanning results.
        """
        # Initialization
        self.signature_tree.clear()
        self.signature_tree.setSortingEnabled(False)
        self.qtreewidgetitems_to_addresses = {}

        # For each analyzed patterns
        for ana in self.cc.CryptoIdentifier.get_analyzed_patterns():

            found_patterns = ana.get_found_patterns()
            algo = ana.get_algo()
            patterns = ana.get_patterns()

            # If there is 1 or more matches
            if len(found_patterns) > 0:

                algo_info = self.cc.QTreeWidgetItem(self.signature_tree)
                algo_info.setText(0, algo.get_name())

                patterns_info = self.cc.QTreeWidgetItem(algo_info)
                patterns_info.setText(0, "%s (%d matches)" % (
                    patterns.get_name(),
                    len(found_patterns))
                )

                for match_dict_list in found_patterns:
                    matches_info = self.cc.QTreeWidgetItem(patterns_info)

                    for pattern_id, match_dicts in match_dict_list.iteritems():
                        pattern_info = self.cc.QTreeWidgetItem(matches_info)
                        pattern_info.setText(0, "%s (%d matches)" % (
                            patterns.get_pattern_name(pattern_id),
                            len(match_dicts.values())
                        ))

                        for match in match_dicts.itervalues():
                            match_info = self.cc.QTreeWidgetItem(pattern_info)
                            match_info.setText(0, "0x%x (%d instructions)" % (
                                match.get_start_address(),
                                match.get_num_insts()
                            ))

                            matches_info.setText(0, "%s" % idc.GetFunctionName(match.get_start_address()))

                            # Add the start address for user friendly jump
                            self.qtreewidgetitems_to_addresses[match_info] = match.get_start_address()

        self.signature_tree.setSortingEnabled(True)

    def _onSignatureTreeItemDoubleClicked(self, item, column):
        """Action for the double clicked.

        Arguments:
            item (QTreeWidgetItem): Item that was clicked.
            column (int): Selected column.
        """
        # Jump to the match address
        if item in self.qtreewidgetitems_to_addresses:
            idc.Jump(self.qtreewidgetitems_to_addresses[item])