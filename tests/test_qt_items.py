from pathlib import Path
from typing import List
from unittest import TestCase
from multiprocessing import Process

from PySide2.QtWidgets import QApplication
from PySide2.QtWidgets import QGraphicsItem

from sot_ipython_connection.sot_kernel import SOTKernel
from sot_ipython_connection.app.sot_script_executer import (main as
    script_executer)
from sot_gui.graph import Graph
from sot_gui.dynamic_graph_communication import DynamicGraphCommunication


input_scripts_dir = str(Path(__file__).resolve().parent/'dg_scripts')


class TestQtItems(TestCase):
    """ Tests the generation of qt items, from fetching data from the kernel to
        getting the list of the graph qt items from the Graph object.

        For each test method, a new kernel is launched and a script initializing
        the graph is run on it. The number of generated qt items (including the
        child items) is checked.
    """

    def setup_class(self):
        # Starting a qt app allows to generate qt items
        def start_qt_app():
            self._app.exec_()
            self._app_process.start()

        self._app = QApplication([])
        self._app_process = Process(target=start_qt_app, daemon=True)


    def teardown_class(self):
        # Terminating the qt app subprocess
        if self._app_process.is_alive():
            self._app_process.terminate()
            self._app_process.join()


    def setUp(self):
        # Launching the kernel in a subprocess
        self._kernel = SOTKernel()
        self._kernel.run_non_blocking()
        self._script_executer = script_executer

        self._graph = Graph(DynamicGraphCommunication())


    def tearDown(self):
        # Terminating the kernel subprocess
        del self._graph
        self._kernel.stop_non_blocking()


    def _get_qt_item_nb(self, qt_item_list: List[QGraphicsItem]) -> int:
        """ Returns the number of qt items contained in the list, including
            the child items.

            Args:
                qt_item_list: List of the parent qt items.
        """

        nb_qt_items = 0

        for item in qt_item_list:
            nb_qt_items += 1
            child_items = item.childItems()
            nb_qt_items += self._get_qt_item_nb(child_items)

        return nb_qt_items


    def _check_nb_items_for_file(self, filename: str, nb_items: int) -> bool:
        """ Checks the number of qt items generated for a dynamic graph
            initialized via a script.

        Args:
            filename: name of the script (located in ./dg_scripts) to run on the
                kernel to initialize the graph.
            nb_items: the number of qt items, including the child items, that
                should be generated.

        Returns:
            True if the number of generated items corresponds to nb_items. If
            not, returns False.
        """
        script_path = str(Path(input_scripts_dir)/filename)
        self._script_executer([script_path])

        self._graph.refresh_graph_data()
        self._graph.generate_qt_items()
        qt_items = self._graph.get_qt_items()

        return self._get_qt_item_nb(qt_items) == nb_items


    def test_circular_dependency(self):
        assert self._check_nb_items_for_file('circular_dependency.py', 30)


    def test_no_input_values(self):
        assert self._check_nb_items_for_file('no_input_values.py', 30)


    def test_no_linked_nodes(self):
        assert self._check_nb_items_for_file('no_linked_nodes.py', 24)


    def test_normal_dg_no_recompute(self):
        assert self._check_nb_items_for_file('normal_dg_no_recompute.py', 46)


    def test_normal_dg(self):
        assert self._check_nb_items_for_file('normal_dg.py', 46)


    def test_partially_linked_nodes(self):
        assert self._check_nb_items_for_file('partially_linked_nodes.py', 35)


    def test_empty_graph(self):
        self._graph.refresh_graph_data()
        self._graph.generate_qt_items()
        qt_items = self._graph.get_qt_items()
        assert len(qt_items) == 0
