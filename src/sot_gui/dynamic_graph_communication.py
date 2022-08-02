from typing import Any, List
from sot_ipython_connection.sot_client import SOTClient


class DynamicGraphCommunication():
    """ This class allows to communicate with a SoT dynamic graph on a remote
        kernel.
    """

    def __init__(self):
        self._client = SOTClient()
        self.connect_to_kernel()


    def connect_to_kernel(self) -> bool:
        """ Launches a new client that will attempt a connection with the latest
            kernel.

            Returns:
              True if the connection was successful, False if not.
        """

        if self._client.connect_to_kernel() is False:
            return False
        try:
            self._import_dynamic_graph()
            return True
        except ConnectionError:
            print('DynamicGraphCommunication.connect_to_kernel: could not'
                ' import dynamic graph into kernel (no connection).')
            return False


    def _import_dynamic_graph(self) -> None:
        """ Imports the dynamic graph.

            Raises:
                ConnectionError: The kernel is not running.
        """
        self._run("import dynamic_graph as dg")


    def _run(self, code: str) -> Any:
        """ Runs code on the remote kernel.

        Any output or error given by the kernel will be printed on the standard
        output.

        Args:
            code: The code to execute on the remote server.

        Returns:
            The value returned by the kernel after executing the code.

        Raises:
            ConnectionError: The kernel is not running.
        """
        response = self._client.run_python_command(code)

        if response.stdout:
            print(response.stdout)
        if response.stderr:
            print(response.stderr)

        if response.result:
            return response.result


    def is_kernel_alive(self) -> bool:
        return self._client.is_kernel_alive()


    #
    # DYNAMIC GRAPH API
    #

    def get_all_entities_names(self) -> List[str]:
        """ Returns a list of the names of the dynamic graph's entities.

        Raises:
            ConnectionError: The kernel is not running.
        """
        return self._run("dg.entity.Entity.entities.keys()")


    def entity_exists(self, entity_name: str) -> bool:
        """ Returns True if the dynamic graph contains the given entity.

        Args:
            entity_name: Name of the entity.

        Raises:
            ConnectionError: The kernel is not running.
        """
        return self._run(f"{entity_name} + in dg.node.Entity.entities")


    def get_entity_type(self, entity_name: str) -> str:
        """ Returns the type of the entity, as a string.

        Args:
            entity_name: Name of the entity.

        Raises:
            ConnectionError: The kernel is not running.
        """
        return self._run(f"dg.entity.Entity.entities['{entity_name}']"
                         ".className")


    def get_entity_signals(self, entity_name: str) -> List[str]:
        """ Returns information on an entity's signals.

        The information is a list of strings (one for each signal) in the form:
        `'Add_of_double(add1)::input(double)::sin0'.

        Args:
            entity_name: Name of the entity.

        Raises:
            ConnectionError: The kernel is not running.
        """
        return self._run(f"[s.name for s in dg.entity.Entity"
            f".entities['{entity_name}'].signals()]")


    def is_signal_plugged(self, entity_name: str, signal_name: str) -> bool:
        """ Returns True if an entity's signal is plugged to another entity.

        Args:
            entity_name: Name of the entity owning the signal.
            signal_name: Name of the signal.

        Raises:
            ConnectionError: The kernel is not running.
        """
        return self._run(f"dg.entity.Entity.entities"
            f"['{entity_name}'].signal('{signal_name}').isPlugged()")


    def get_linked_signal(self, entity_name: str, signal_name: str) -> str:
        """ Returns the name of the signal linked to an entity's signal.

        Args:
            entity_name: Name of the entity owning the signal.
            signal_name: Name of the signal.

        Raises:
            ConnectionError: The kernel is not running.
        """
        return self._run(f"dg.entity.Entity.entities"
            f"['{entity_name}'].signal('{signal_name}').getPlugged().name")


    def get_signal_value(self, entity_name: str, signal_name: str) -> Any:
        """ Returns the value of an entity's signal.

        Args:
            entity_name: Name of the entity owning the signal.
            signal_name: Name of the the signal.

        Raises:
            ConnectionError: The kernel is not running.
        """
        return self._run(f"dg.entity.Entity.entities\
            ['{entity_name}'].signal('{signal_name}').value")


    def get_exec_time(self, entity_name: str, signal_name: str) -> int:
        """ Returns the time of the last execution of a signal.

        Args:
            entity_name: Name of the entity owning the signal.
            signal_name: Name of the signal.

        Raises:
            ConnectionError: The kernel is not running.
        """
        return self._run(f"dg.entity.Entity.entities"
            f"['{entity_name}'].signal('{signal_name}').time")
