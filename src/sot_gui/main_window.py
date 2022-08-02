from __future__ import annotations
from typing import Union, List, Dict, Tuple
from enum import Enum
import threading
from time import sleep

from PySide2.QtWidgets import (QMainWindow, QGraphicsScene, QGraphicsView,
    QToolBar, QAction, QMessageBox, QLabel, QGraphicsItem, QInputDialog,
    QDockWidget, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QScrollArea, QWidget, QGraphicsPolygonItem, QStatusBar)
from PySide2.QtGui import QColor
from PySide2.QtCore import Qt

from sot_gui.graph import (Graph, GraphElement, Node, Port, Edge, EntityNode,
    InputNode, Cluster, ClusterPort)
from sot_gui.dynamic_graph_communication import DynamicGraphCommunication


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stack Of Tasks GUI")

        # Adding the graph scene and its view:
        self._graph_scene = SoTGraphScene(self)
        self._view = SoTGraphView(self)
        self._view.setScene(self._graph_scene)
        self.setCentralWidget(self._view)

        self._add_main_toolbar()
        self._add_cluster_toolbar()
        self._add_status_bar()
        self._add_cluster_side_panel()
        self._add_info_side_panel()

        # Displaying the graph:
        self._refresh_graph()


    #
    # ADDITIONAL WIDGETS
    #

    def _add_main_toolbar(self) -> None:
        """ Adds the sot graph toolbar to the main window. """
        toolbar = QToolBar("main_toolbar")
        self._main_toolbar = toolbar
        self.addToolBar(toolbar)

        button_refresh = QAction("Refresh", self)
        button_refresh.triggered.connect(self._refresh_graph)
        toolbar.addAction(button_refresh)

        button_reconnect = QAction("Reconnect", self)
        button_reconnect.triggered.connect(self._reconnect)
        toolbar.addAction(button_reconnect)

        button_clusterize = QAction("Create cluster", self)
        button_clusterize.triggered.connect(self._create_cluster)
        toolbar.addAction(button_clusterize)

        button_manage_clusters = QAction("Manage clusters", self)
        button_manage_clusters.triggered.connect(self._manage_clusters)
        toolbar.addAction(button_manage_clusters)


    def _add_cluster_toolbar(self):
        self.addToolBarBreak()
        toolbar = QToolBar("cluster_toolbar")
        self.addToolBar(toolbar)
        self._cluster_toolbar = toolbar

        button_complete = QAction("Confirm cluster", self)
        button_complete.triggered.connect(self._view._completeClusterCreation)
        toolbar.addAction(button_complete)

        button_cancel = QAction("Cancel clusterization", self)
        button_cancel.triggered.connect(self._view.cancelClusterCreation)
        toolbar.addAction(button_cancel)

        # This toolbar will only be shown during cluster creation
        toolbar.hide()


    def show_cluster_toolbar(self):
        self._cluster_toolbar.show()
    def hide_cluster_toolbar(self):
        self._cluster_toolbar.hide()


    def _add_status_bar(self) -> None:
        """ Adds a connection status bar to the main window. """
        status_bar = ConnectionStatusBar(self, self._graph_scene.is_kernel_running)
        self.setStatusBar(status_bar)


    def _add_cluster_side_panel(self) -> None:
        self._cluster_side_panel = ClustersPanel(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self._cluster_side_panel)
        self._cluster_side_panel.hide()


    def _add_info_side_panel(self) -> None:
        self._info_side_panel = InfoPanel(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._info_side_panel)
        self._info_side_panel.hide()


    def _message_box_no_connection(self, refresh: bool = False) -> None:
        """ Displays a message box which asks the user if the want to reconnect
            to the kernel.

            If the user clicks Yes, a connection attempt is made. If they click
            No, nothing is done. In any case, the message box is closed.

            Args:
                refresh: if True, the graph will be refreshed after the
                    connection attempt, if it was successful.
        """
        message_box = QMessageBox(self)
        message_box.setWindowTitle("No connection")

        # Asking the user if they want to reconnect and refresh:
        message_box.setText("A connection to the kernel is needed.")
        message_box.setInformativeText('Do you want to try to connect?')
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message_box.setDefaultButton(QMessageBox.Yes)

        return_value = message_box.exec_()
        if return_value == QMessageBox.Yes:
            self._reconnect()
            if refresh:
                self._refresh_graph()


    #
    # BUTTONS CALLBACKS
    #

    def _refresh_graph(self) -> None:
        """ Refreshes the graph. New graph data will be fetched from the kernel
            and displayed.

            If there is no connection to a running kernel, the refresh is
            aborted and a message box is opened to offer the user to connect.
            If they click yes, a new graph refresh will be attempted after the
            reconnection.
        """
        self._cancel_ongoing_actions()
        if self.statusBar().reconnection_needed():
            self._message_box_no_connection(refresh=True)
        else:
            try:
                self._graph_scene.refresh()
            except ConnectionError:
                self._message_box_no_connection(refresh=True)


    def _reconnect(self) -> None:
        """ Reconnects the graph to the latest running kernel.

            The graph will not be automatically refreshed.
            If there is no running kernel, a message box is opened to alert the
            user and let them launch one before re-attempting a connection.
        """
        self._cancel_ongoing_actions()
        if self._graph_scene.reconnect():
            self.statusBar().set_reconnection_needed(False)
        else:
            self._message_box_no_connection()


    def _create_cluster(self) -> None:
        """ Launches the creation of a cluster. """
        self._view.enter_cluster_creation_mode()


    def _cancel_ongoing_actions(self) -> None:
        if (self._view.interactionMode ==
            SoTGraphView.InteractionMode.CLUSTER_CREATION):
            self._view.cancelClusterCreation()


    def _manage_clusters(self) -> None:
        self._cluster_side_panel.show()


#
# OTHER WIDGETS
#

class ConnectionStatusBar(QStatusBar):
    """ Status bar displaying the connection status thanks to a thread
        monitoring this status.
    """
    def __init__(self, parent, co_check_method):
        super().__init__(parent)

        self._co_check_method = co_check_method

        # If the kernel is stopped and relaunched, its session has changed and
        # sending commands will result in a crash. To prevent this, we don't
        # allow the user to send commands until they triggered a reconnection:
        self._reconnection_needed = not self.kernel_is_alive()

        self._co_status_indicator = QLabel("")
        self.addPermanentWidget(self._co_status_indicator)

        def connection_status_updating() -> None:
            while 1:
                if self.kernel_is_alive() is False:
                    self._reconnection_needed = True

                self._update_co_status_indicator()
                sleep(0.1)

        # Launching a thread to update the connection status of the kernel:
        self._kernel_heartbeat_thread = threading.Thread(
            target=connection_status_updating)
        self._kernel_heartbeat_thread.setDaemon(True)
        self._kernel_heartbeat_thread.start()


    def _update_co_status_indicator(self) -> None:
        """ Updates the text and color of the connection status indicator. """
        if self.kernel_is_alive() is False:
            color = 'red'
            text = 'No kernel detected'

        elif self._reconnection_needed is True:
            color = 'orange'
            text = 'Reconnection available'

        else:
            color = 'green'
            text = 'Connected'

        if self._co_status_indicator is None:
            self._co_status_indicator.setText(text)
            self._co_status_indicator.setStyleSheet('QLabel {color: ' + color + '}')


    def kernel_is_alive(self) -> bool:
        return self._co_check_method()

    def reconnection_needed(self) -> bool:
        return self._reconnection_needed
    def set_reconnection_needed(self, reconnection_needed: bool) -> None:
        self._reconnection_needed = reconnection_needed


    def __del__(self):
        self._kernel_heartbeat_thread.join()
        del self._kernel_heartbeat_thread


class ClustersPanel(QDockWidget):
    def __init__(self, parent):
        super().__init__('Clusters', parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self._list_widget = QListWidget(self)
        self.setWidget(self._list_widget)

        # Setting the context menu options (right click on the item)
        option_delete = QAction("Delete", self)
        option_delete.triggered.connect(self._remove_clusters)
        option_infos = QAction("Display informations", self)
        option_infos.triggered.connect(self._display_cluster_info)

        self._list_widget.addAction(option_delete)
        self._list_widget.addAction(option_infos)
        self._list_widget.setContextMenuPolicy(Qt.ActionsContextMenu)
        self._list_widget.setSortingEnabled(True)


    def add_cluster(self, cluster: Cluster) -> None:
        item = QListWidgetItem(cluster.label())
        self._list_widget.addItem(item)


    def _get_selected_item(self) -> str:
        selected_items = self._list_widget.selectedItems()
        return selected_items[0]


    def _get_selected_items(self) -> str:
        selected_items = self._list_widget.selectedItems()
        return selected_items


    def _remove_clusters(self) -> None:
        selected_items = self._get_selected_items()
        for item in selected_items:
            item_row = self._list_widget.indexFromItem(item).row()
            self._list_widget.takeItem(item_row)
            cluster_label = item.text()
            self.parent()._view.scene().remove_cluster(cluster_label)


    def _display_cluster_info(self) -> None:
        selected_item = self._get_selected_item()
        self.parent()._view.display_cluster_info(selected_item.text())


class InfoPanel(QDockWidget):
    def __init__(self, parent):
        super().__init__('Info panel', parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)


    def _get_element_info(self, element: GraphElement) -> Dict:
        """ Returns a dictionary containing the element data to be displayed.

            Args:
                element: The graph element whose info to return (Node, Port,
                    Edge, Cluster or ClusterPort)

            Returns:
                A dictionary containing a 'title' element (title to give to the
                display panel) and a 'data' element. This data is a list of
                each section's content to display, as tuples (title, info).
                This 'info' element can be a string (in this case it should be
                displayed as-is, as a label) or an array of arrays (in this case
                it should be displayed as a table, with its first element being
                the horizontal labels).
        """
        if isinstance(element, EntityNode):
            return self._get_entity_node_data(element)
        elif isinstance(element, InputNode):
            return self._get_input_node_data(element)
        elif isinstance(element, Port):
            return self._get_port_data(element)
        elif isinstance(element, Edge):
            return self._get_edge_data(element)
        elif isinstance(element, Cluster):
            return self._get_cluster_data(element)
        raise ValueError('Could not resolve type of clicked graph element.')


    def _get_entity_node_data(self, node: EntityNode) -> Dict:
        """ Returns a dictionary containing the node data to be displayed.
            See _get_element_info for details.
        """
        element_info = dict()
        element_info['title'] = 'Entity'

        data = []
        data.append(('Name', node.name()))
        data.append(('Type', node.type()))

        cluster = node.cluster()
        cluster_label = cluster.label() if cluster is not None else "None"
        data.append(('Cluster', cluster_label))

        signals = [['Name', 'Value', 'Last execution']]
        node_ports = node.ports()
        for port in node_ports:
            signal_value = str(port.value())
            last_exec = 't = ' + str(port.last_exec())
            signals.append([port.name(), signal_value, last_exec])
        data.append(('Signals', signals))

        element_info['data'] = data
        return element_info


    def _get_input_node_data(self, node: InputNode) -> Dict:
        """ Returns a dictionary containing the node data to be displayed.
            See _get_element_info for details.
        """
        element_info = dict()
        element_info['title'] = 'Input'

        data = []
        linked_node = node.child_node()
        linked_port = node.child_port()
        cluster = linked_node.cluster()
        cluster_label = cluster.label() if cluster is not None else "None"
        data.append(('Input of', f"{linked_node.name()}:{linked_port.name()}"
                    f" (Cluster: {cluster_label})"))

        data.append(('Value', f"{str(node.value())} ({node.type()})"))
        data.append(('Cluster', str(node.cluster())))

        element_info['data'] = data

        return element_info


    def _get_port_data(self, port: Port) -> Dict:
        """ Returns a dictionary containing the port data to be displayed.
            See _get_element_info for details.
        """
        element_info = dict()
        element_info['title'] = 'Port'

        data = []
        data.append(('Name', port.name()))

        if isinstance(port, ClusterPort):
            node = port.node_port().node()
            cluster = port.node()
        else:
            node = port.node()
            cluster = port.node().cluster()

        node_name = node.name()
        cluster_label = cluster.label() if cluster is not None else "None"
        data.append(('Node', f"{node_name} (Cluster: {cluster_label})"))

        data.append(('Value', port.value()))

        # Names of linked node, port, and their cluster:
        linked_port = port.plugged_port()
        if linked_port is None:
            data.append(('Linked to', 'None'))

        elif isinstance(port.plugged_node(), InputNode):
            data.append(('Linked to', 'Fixed value'))

        else:
            linked_node = port.plugged_node()
            linked_cluster = linked_node.cluster()
            linked_cluster_label = (linked_cluster.label() if linked_cluster
                                    is not None else "None")
            data.append(('Linked to', f"{linked_node.name()}:"
                    f"{linked_port.name()} (Cluster: {linked_cluster_label})"))

        data.append(('Last execution', port.last_exec()))

        element_info['data'] = data

        return element_info


    def _get_edge_data(self, edge: Edge) -> Dict:
        """ Returns a dictionary containing the edge data to be displayed.
            See _get_element_info for details.
        """
        element_info = dict()
        element_info['title'] = 'Signal'

        data = []

        tail_node = edge.tail_node()
        if isinstance(tail_node, InputNode):
            data.append(('Tail', 'Fixed value'))
        else:
            tail_cluster = edge.tail_node().cluster()
            tail_cluster_label = (tail_cluster.label() if tail_cluster is not
                                None else "None")
            data.append(('Tail', f"{tail_node.name()}:{edge.tail().name()} "
                        f"(Cluster: {tail_cluster_label})"))

        head_cluster = edge.head_node().cluster()
        head_cluster_label = (head_cluster.label() if head_cluster is not None
                            else "None")
        data.append(('Head', f"{edge.head_node().name()}:{edge.head().name()} "
                    f"(Cluster: {head_cluster_label})"))

        data.append(('Value', str(edge.value())))
        data.append(('Last execution', f"t = {edge.last_exec()}"))

        element_info['data'] = data

        return element_info


    def _get_cluster_data(self, cluster: Cluster) -> Dict:
        """ Returns a dictionary containing the cluster data to be displayed.
            See _get_element_info for details.
        """
        element_info = dict()
        element_info['title'] = 'Cluster'

        data = []
        data.append(('Name', cluster.label()))

        signals = [['Name', 'Node', 'Value', 'Last execution']]
        ports = cluster.ports()
        for port in ports:
            node_port = port.node_port()
            signal_value = str(node_port.value())
            last_exec = 't = ' + str(node_port.last_exec())
            signals.append([node_port.name(), node_port.node().name(),
                            signal_value, last_exec])
        data.append(('Signals', signals))
        element_info['data'] = data

        nodes = [['Name']]
        for node in cluster.nodes():
            nodes.append([node.name()])
        data.append(['Nodes', nodes])

        return element_info


    def display_element_info(self, element: GraphElement) -> None:

        self._scroll_area = QScrollArea()
        self._info_widget = QWidget()
        self._layout = QVBoxLayout()

        element_info = self._get_element_info(element)

        self.setWindowTitle(f"Info panel: {element_info['title']}")

        for (title, data) in element_info['data']:

            if isinstance(data, list): # Table section
                # Adding the title of the section
                label = QLabel(f'<b>{title}</b>')
                self._layout.addWidget(label)

                # Creating the table
                table_info = QTableWidget(len(data) - 1, len(data[0]), self)
                table_info.setEditTriggers(QTableWidget.NoEditTriggers)
                self._layout.addWidget(table_info)

                # Setting the horizontal and vertical labels
                table_info.verticalHeader().setVisible(False)
                table_info.setHorizontalHeaderLabels(data[0])

                # Adding each element of the table
                for line_idx, table_line in enumerate(data[1:]):
                    for col_idx, table_elem in enumerate(table_line):
                        new_item = QTableWidgetItem(table_elem)
                        new_item.setToolTip(table_elem)
                        table_info.setItem(line_idx, col_idx, new_item)

            else: # Text section
                label = QLabel(f'<b>{title}</b><br>{data}')
                self._layout.addWidget(label)

        self._info_widget.setLayout(self._layout)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setWidget(self._info_widget)
        self.setWidget(self._scroll_area)

        self.show()


class SoTGraphView(QGraphicsView):
    """ QGraphicsView which handles events to interact with the SoTGraphScene
        items.
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.interactionMode = self.InteractionMode.DEFAULT

        # When the user drags the mouse, it moves the view:
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        # To center the zoom on the position of the mouse:
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)


    class InteractionMode(Enum):
        """ This enum is used to determine how to handle events based on there
            being an ongoing user action or not (e.g when the user creates a
            cluster, a click on a node must be handled differently)
        """
        DEFAULT = 0
        CLUSTER_CREATION = 1 # When the user is creating a group of entities


    #
    # EVENT OVERRIDES
    #

    def wheelEvent(self, event):
        """ See QGraphicsView.wheelEvent """
        super().wheelEvent(event)
        # The user can zoom in or out by rotating the mouse wheel:
        self._handleZoom(event.angleDelta().y())


    def mouseReleaseEvent(self, event):
        """ See QGraphicsView.mouseReleaseEvent """
        super().mouseReleaseEvent(event)

        if event.button() == Qt.LeftButton:
            self._handle_left_click(event)
        elif event.button() == Qt.RightButton:
            self._handle_right_click(event)


    #
    # EVENT CALLBACKS
    #

    def _handle_left_click(self, event):
        click_pos = event.localPos()
        clicked_item = self.itemAt(click_pos.x(), click_pos.y())
        if clicked_item is None:
            return
        #print(self.scene().get_graph_elem_per_qt_item(clicked_item))

        if self.interactionMode == self.InteractionMode.CLUSTER_CREATION:
            self.scene().select_item_for_cluster_creation(clicked_item)
        elif self.interactionMode == self.InteractionMode.DEFAULT:
            graph_elem = self.scene().get_graph_elem_per_qt_item(clicked_item)
            self._display_element_info(graph_elem)


    def _display_element_info(self, element: GraphElement) -> None:
        self.scene().clear_selection()
        self.scene().update_selected_elements(element)
        self.parent()._info_side_panel.display_element_info(element)


    def display_cluster_info(self, cluster_label: str) -> None:
        cluster = self.scene().get_cluster_per_label(cluster_label)
        if cluster is not None:
            self._display_element_info(cluster)


    def _handle_right_click(self, event):
        ...


    def _handleZoom(self, delta: int) -> None:
        """ Rescales the view according to the amount that the mouse wheel was
            rotated.

            Args:
                delta: relative amount that the wheel was rotated
        """
        # For more info on the delta value, see:
        # https://doc.qt.io/qtforpython-5/PySide2/QtGui/QWheelEvent.html#PySide2.QtGui.PySide2.QtGui.QWheelEvent.angleDelta
        if delta > 0:
            self.scale(1.25, 1.25)
        else:
            self.scale(0.8, 0.8)


    def enter_cluster_creation_mode(self) -> None:
        if self.interactionMode != self.InteractionMode.CLUSTER_CREATION:
            self.scene().clear_selection()
            self.parent().show_cluster_toolbar()
            self.interactionMode = self.InteractionMode.CLUSTER_CREATION
    def exit_cluster_creation_mode(self) -> None:
        self.interactionMode = self.InteractionMode.DEFAULT
        self.parent().hide_cluster_toolbar()
        self.scene().clear_selection()


    def _completeClusterCreation(self) -> None:
        # If clusterizing the selected nodes is not possible, we let the user
        # keep on selecting:
        if self.scene().check_clusterizability() is False:
            self._message_box_wrong_nodes_for_cluster()
            return

        # Else, we let them enter the label of the cluster in a dialog box,
        # displaying a message if the label is already used by another cluster:

        label = None
        while label is None:
            label, clicked_ok = QInputDialog().getText(self, 'Cluster label',
                                    'Please enter a label for this cluster.')

            if clicked_ok:
                if not self.scene().is_cluster_label_available(label):
                    label = None
                    self._message_box_wrong_cluster_label()
                    continue

                new_cluster = self.scene().complete_cluster_creation(label)
                self.parent()._cluster_side_panel.add_cluster(new_cluster)
                self.exit_cluster_creation_mode()

            else: # If the user canceled, we let them keep on selecting
                return



    def cancelClusterCreation(self) -> None:
        self.exit_cluster_creation_mode()


    def _message_box_wrong_nodes_for_cluster(self) -> None:
        """ Displays a message box to tell the user that the current selection
            is sot suitable to create a cluster.
        """
        message_box = QMessageBox(self)
        message_box.setWindowTitle("Wrong selection")

        # Asking the user if they want to reconnect and refresh:
        message_box.setText("A cluster cannot be created with the currently "
                            "selected nodes.")
        message_box.setInformativeText('Please select:\n  - at least two nodes'
                                        '\n  - only directly linked nodes')
        message_box.exec_()


    def _message_box_wrong_cluster_label(self) -> None:
        """ Displays a message box to tell the user that the label they chose
            for a cluster is already used by another cluster.
        """
        message_box = QMessageBox(self)
        message_box.setWindowTitle("Label unavailable")

        # Asking the user if they want to reconnect and refresh:
        message_box.setText("This label is already assigned to another existing"
            " cluster.")
        message_box.setInformativeText("Please enter another label for this new"
            " cluster.\nThe list of all clusters names can be displayed by"
            " clicking on 'Manage clusters'.")
        message_box.exec_()


class SoTGraphScene(QGraphicsScene):
    """ QGraphicsScene which contains the graph qt items and manages the
        communication with the Graph object.

        Attributes: See QGraphicsScene
    """

    def __init__(self, parent):
        super().__init__(parent)
        self._connected_to_kernel = False
        self._dg_communication = DynamicGraphCommunication()
        self._graph = Graph(self._dg_communication)

        self._selected_nodes = []
        self._selected_elements = []


    def is_kernel_running(self) -> bool:
        """ Returns True if a running SOTKernel is detected.

            Every SOTKernel uses the same ports, which means a kernel can be
            detected without the client being connected to it (if the client
            was previously connected to a SOTKernel which has been stopped).
        """
        return self._dg_communication.is_kernel_alive()


    def update_display(self) -> None:
        """ Updates the graph display. New graph data will not be fetched from
            the kernel.
        """
        self._graph.generate_qt_items()
        self.clear()
        self._items = self._graph.get_qt_items()
        for item in self._items:
            self.addItem(item)


    def refresh(self) -> None:
        """ Refreshes the graph. New graph data will be fetched from the kernel
            and displayed.

        Raises:
            ConnectionError: the kernel is not running.
        """

        self._graph.refresh_graph_data()
        self.update_display()


    def reconnect(self) -> bool:
        """ Attemps to reconnect the client to the latest kernel.

        Returns:
            True if the connection was successful, False if not.
        """
        return self._dg_communication.connect_to_kernel()


    def select_item_for_cluster_creation(self, item: QGraphicsItem) -> None:
        selected_node = None
        graph_elem = self.get_graph_elem_per_qt_item(item)

        if isinstance(graph_elem, Node):
            selected_node = graph_elem

        elif isinstance(graph_elem, Port):
            selected_node = graph_elem.node()

        elif isinstance(graph_elem, Edge):
            return # Edges are not selected

        self._update_selected_nodes(selected_node)


    def update_selected_elements(self, element: GraphElement) -> None:
        """ Adds / removes an element to / from the selection.

            Only the given element will be added to the selection, i.e if the
            element is a port, the whole node will not be added.

            Args:
                element: The graph element to add to the selection.
        """
        if element in self._selected_elements:
            self._selected_elements.remove(element)
            self._update_color_selected_element(element, False)
        else:
            self._selected_elements.append(element)
            self._update_color_selected_element(element, True)


    def _update_selected_nodes(self, node: Node) -> None:
        """ Adds / removes a whole node to / from the selection.

            When a node is selected, if will be colored in its entirety (label
            cell + ports).

            Args:
                node: The node to add or remove.
        """
        if node in self._selected_nodes:
            self._selected_nodes.remove(node)
            self._update_color_selected_node(node, False)
        else:
            self._selected_nodes.append(node)
            self._update_color_selected_node(node, True)


    def complete_cluster_creation(self, cluster_label: str) -> Cluster:
        new_cluster = self._graph.add_cluster(cluster_label,
                                              self._selected_nodes.copy())
        self.update_display()
        return new_cluster


    def remove_cluster(self, cluster_label: str) -> None:
        self._graph.remove_cluster(cluster_label)
        self.clear_selection()
        self.update_display()


    def check_clusterizability(self) -> bool:
        """ Returns True if a cluster can be created from the currently selected
            nodes.
        """
        return self._graph.check_clusterizability(self._selected_nodes.copy())


    def clear_selection(self) -> None:
        for node in self._selected_nodes:
            self._update_color_selected_node(node, False)
        for element in self._selected_elements:
            self._update_color_selected_element(element, False)
        self._selected_nodes = []
        self._selected_elements = []


    def _update_color_selected_element(self, element: GraphElement,
                                        selected: bool) -> None:
        """ Changes a graph element's color depending on its selection status.

            Args:
                element: The graph element whose color will be updated.
                selected: If True (respectively if False), the node's color will
                    be updated to make it appear selected (respectively
                    unselected).
        """

        qt_item = element.qt_item()
        if qt_item is not None:

            if isinstance(element, Edge): # Coloring the path and the head
                new_color = 'lightGray' if selected else 'black'
                qt_item.setPen(QColor(new_color))
                children = qt_item.childItems()
                for child in children:
                    if isinstance(child, QGraphicsPolygonItem):
                        child.setBrush(QColor(new_color))
                        child.setPen(QColor(new_color))

            else:
                new_color = 'lightGray' if selected else 'white'
                qt_item.setBrush(QColor(new_color))


    def _update_color_selected_node(self, node: Node, selected: bool) -> None:
        """ Changes a node's color (middle column + ports) depending on its
            selection status.

            Args:
                node: The node whose color will be updated.
                selected: If True (respectively if False), the node's color will
                    be updated to make it appear selected (respectively
                    unselected).
        """
        new_color = 'lightGray' if selected else 'white'

        if node.qt_item() is not None:
            node.qt_item().setBrush(QColor(new_color))

        if not isinstance(node, InputNode):
            for port in node.ports():
                if port.qt_item() is not None:
                    port.qt_item().setBrush(QColor(new_color))


    def get_cluster_list(self) -> List[Cluster]:
        return self._graph.clusters()


    def is_cluster_label_available(self, label: str) -> bool:
        clusters = self.get_cluster_list()

        for cluster in clusters:
            if cluster.label() == label:
                return False
        return True


    def get_cluster_per_label(self, label: str) -> Cluster:
        clusters = self.get_cluster_list()

        for cluster in clusters:
            if cluster.label() == label:
                return cluster
        return None


    def get_graph_elem_per_qt_item(self, item: QGraphicsItem) \
        -> Union[Node, Port, Edge]:
        graph_elem = self._graph.get_elem_per_qt_item(item)
        return graph_elem
