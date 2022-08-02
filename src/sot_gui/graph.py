from __future__ import annotations # To prevent circular dependencies of typing
from typing import List, Any, Dict, Union
from subprocess import Popen, PIPE
from copy import deepcopy

from PySide2.QtWidgets import QGraphicsItem

from sot_gui.dynamic_graph_communication import DynamicGraphCommunication
from sot_gui.dot_data_generator import DotDataGenerator
from sot_gui.json_to_qt_generator import JsonToQtGenerator
from sot_gui.utils import quoted


class GraphElement:
    def __init__(self):
        self._name: str = None
        self._type: str = None
        self._last_exec: int = None
        self._qt_item: QGraphicsItem = None


    def name(self) -> str:
        return self._name


    def type(self) -> str:
        return self._type
    def set_type(self, type: str) -> None:
        self._type = type


    def last_exec(self) -> int:
        return self._last_exec
    def set_last_exec(self, last_exec: int) -> None:
        self._last_exec = last_exec


    def qt_item(self) -> QGraphicsItem:
        return self._qt_item
    def set_qt_item(self, qt_item: QGraphicsItem) -> None:
        self._qt_item = qt_item


class Node(GraphElement):
    def __init__(self):
        super().__init__()
        self._cluster: Cluster = None
        self._inputs: List[Port] = None
        self._outputs: List[Port] = None


    def cluster(self) -> Cluster:
        return self._cluster
    def set_cluster(self, cluster: Cluster) -> None:
        self._cluster = cluster


    def inputs(self) -> List[Port]:
        if self._inputs is not None:
            return self._inputs.copy()
        return []
    def outputs(self) -> List[Port]:
        if self._outputs is not None:
            return self._outputs.copy()
        return []

    def parent_nodes(self) -> List[Node]:
        parents = []
        for input in self.inputs():
            if input.edge() is not None:
                parents.append(input.edge().tail().node())
        return parents

    def child_nodes(self) -> List[Node]:
        children = []
        for output in self.outputs():
            if output.edge() is not None:
                children.append(output.edge().head().node())
        return children


    def ports(self) -> List[Port]:
        ports = []
        ports += self.inputs()
        ports += self.outputs()
        return ports


    def add_port(self, name: str, type: str) -> Port:
        new_port = Port(name, type, self)
        if type == 'input':
            self._inputs.append(new_port)
        elif type == 'output':
            self._outputs.append(new_port)
        else:
            raise ValueError("Port type must be either 'input' or 'output'")
        return new_port


    def set_edge_for_port(self, edge: Edge, port_name: str) -> None:
        port = self.get_port_per_name(port_name)
        if port is None:
            raise ValueError(f"Port {port_name} of node {self._name} does not exist.")
        port.set_edge(edge)


    def get_port_per_name(self, name: str) -> Port | None:
        for port in self._inputs + self._outputs:
            if port.name() == name:
                return port
        return None


class InputNode(Node):
    def __init__(self, output_edge: Edge):
        super().__init__()

        self._type = output_edge.value_type()
        self._cluster = None

        child_port_name = output_edge.head().name()
        child_node_name = output_edge.head().node().name()
        self._name = f"input_{child_node_name}_{child_port_name}"

        output_port = Port("sout0", 'output', self)
        output_port.set_edge(output_edge)
        self._outputs = [output_port]


    def value(self) -> Any:
        return self.outputs()[0].value()
    def type(self) -> type:
        return self._type
    def port(self) -> Port:
        return self._outputs[0]

    def child_port(self) -> Port:
        return self.port().edge().head()
    def child_node(self) -> Node:
        return self.child_port().node()


class EntityNode(Node):
    def __init__(self, name: str, type: str = None):
        super().__init__()
        self._name = name
        self._type = type
        self._cluster = None
        self._inputs = []
        self._outputs = []


class Cluster(Node):
    # Not the number or existing clusters, but the number of clusters ever created:
    clusters_creation_count = 0

    def __init__(self, label: str, nodes: List[Node]):
        super().__init__()

        self._name: str = str(Cluster.clusters_creation_count)
        Cluster.clusters_creation_count += 1

        self._label: str = label
        self._nodes: List[Node] = nodes
        self._qt_item: QGraphicsItem = None

        # If the cluster is shrinked, it is displayed as a single node. If it is
        # expanded, it is displayed as a subgraph (section of the graph bounded
        # by a rectangle):
        self._expanded: bool = False

        # The cluster's ports are its nodes' ports that are not linked to a node
        # in the same cluster
        self._inputs: List[ClusterPort] = []
        self._outputs: List[ClusterPort] = []
        for node in self._nodes:
            node.set_cluster(self)

            for port in node.ports():
                if self.is_port_internal(port):
                    continue
                if port.type() == 'input':
                    self._inputs.append(ClusterPort(port, self))
                else:
                    self._outputs.append(ClusterPort(port, self))


    def is_port_internal(self, port: Port) -> bool:
        """ Returns True if the port is internal, i.e if the node it belongs to
            and the node it is plugged to both belong to this cluster.

            If the port is not plugged to any node, it is considered external.
        """
        cluster_nodes = self.nodes()

        if port.node() not in cluster_nodes:
            return False

        plugged_node = port.plugged_node() # Node plugged to this port
        if plugged_node is None:
            return False
        return plugged_node in cluster_nodes


    def nodes(self) -> List[Node]:
        return self._nodes.copy()
    def label(self) -> str:
        return self._label
    def is_expanded(self) -> bool:
        return self._expanded

    def get_cluster_port_per_node_port(self, port: Port) -> ClusterPort | None:
        for cluster_port in self.ports():
            if cluster_port.node_port() == port:
                return cluster_port
        return None


class Port(GraphElement):
    """ This class represents a node's port, where a signal can be plugged to
        the node.
    """
    def __init__(self, name: str, type: str, node: Node):
        super().__init__()
        self._edge = None
        self._name = name
        self._type = type # 'input' or 'output'
        self._node = node
        self._value = None


    def node(self) -> Node:
        return self._node


    def value(self) -> Any:
        return self._value
    def set_value(self, value: Any) -> None:
        self._value = value


    def edge(self) -> Edge:
        return self._edge
    def set_edge(self, edge: Edge) -> None:
        self._edge = edge
        self.set_value(edge.value())
        self.set_last_exec(edge.last_exec())
        if self._type == 'input':
            edge.set_head(self)
        elif self._type == 'output':
            edge.set_tail(self)
        else:
            raise ValueError("Port type must be either 'input' or 'output'")


    def plugged_port(self) -> Port:
        edge = self.edge()
        if edge is not None:
            if self.type() == 'input':
                return edge.tail()
            else:
                return edge.head()
        return None


    def plugged_node(self) -> Node:
        plugged_port = self.plugged_port()
        if plugged_port is not None:
            return plugged_port.node()
        return None


class ClusterPort(Port):
    """ This class represents a cluster port. Each node port of a cluster which
        is linked to a node external to the cluster will be considered as a
        cluster port.
    """
    def __init__(self, node_port: Port, node: Cluster):
        super().__init__(None, None, None)
        self._name = f"{node_port.node().name()}_{node_port.name()}"
        self._type = node_port.type()
        self._node = node
        self._edge = node_port.edge()
        self._node_port: Port = node_port

    def node_port(self) -> Port:
        return self._node_port


class Edge(GraphElement):
    def __init__(self, value: Any = None, value_type: str = None,
                head: Port = None, tail: Port = None):
        super().__init__()
        self._value = value
        self._value_type = value_type
        self._head = head
        self._tail = tail


    def value(self) -> Any:
        return self._value


    def value_type(self) -> str:
        return self._value_type
    def set_value_type(self, value_type: str) -> None:
        self._value_type = value_type


    def head(self) -> Port:
        return self._head
    def set_head(self, head: Port) -> None:
        self._head = head


    def tail(self) -> Port:
        return self._tail
    def set_tail(self, tail: Port) -> None:
        self._tail = tail

    def tail_node(self) -> Node:
        tail_port = self.tail()
        if tail_port is not None:
            return tail_port.node()
        return None

    def head_node(self) -> Node:
        head_port = self.head()
        if head_port is not None:
            return head_port.node()
        return None


class Graph:
    """ This class holds the graph's information: it gets the dynamic graph's
        entities and signals, and generates their corresponding PySide items.

        Constructor argument:
        - `dg_communication`: will be used to fetch data from the dynamic graph
    """

    def __init__(self, dg_communication: DynamicGraphCommunication):
        self._dg_communication = dg_communication
        self._entities_labels_config = self._get_entities_labels_config()

        # Entities that exist in the dynamic graph:
        self._dg_entities: List[EntityNode] = []
        # Input nodes that don't exist in the dynamic graph:
        self._input_nodes: List[InputNode] = []
        # Clusters of nodes created by the user:
        self._clusters: List[Cluster] = []
        # Information about the graph as a whole (name, dimensions, background color...):
        self._graph_info: Dict[str, Any] = {}


    def _get_entities_labels_config(self) -> Dict[str, str]:
        """ Returns a dictionary containing which labels to use for entity
            types we want to label in a specific way.
            This configuration can be modified in entities_labels_config.py.
        """
        try:
            from sot_gui.entities_labels_config import entities_labels
            return entities_labels
        except:
            return None


    def graph_info(self) -> Dict[str, Any]:
        return deepcopy(self._graph_info)

    def clusters(self) -> List[Cluster]:
        return self._clusters.copy()
    def shrinked_clusters(self) -> List[Cluster]:
        return [clust for clust in self._clusters if not clust.is_expanded()]
    def expanded_clusters(self) -> List[Cluster]:
        return [clust for clust in self._clusters if clust.is_expanded()]


    def _get_node_per_name(self, name: str) -> Node | None:
        for node in self._dg_entities + self._input_nodes:
            if node.name() == name:
                return node
        return None


    def refresh_graph_data(self):
        """ This function updates the graph by fetching the dynamic graph's data,
            generating a new graph layout with dot and creating the needed qt items.
            Raises a ConnectionError if there is no connection to the kernel.
        """
        self._clear_dg_data()
        self._get_dg_data()


    def add_cluster(self, name: str, nodes: List[Node]) -> Cluster:
        """ Adds a cluster to the graph. Checks on the validity of the
            cluster should be made before calling this method.

            Returns:
                The new cluster.
        """
        new_cluster = Cluster(name, nodes)
        self._clusters.append(new_cluster)
        return new_cluster


    def remove_cluster(self, label: str) -> None:
        """ Deletes a cluster from the graph elements.

            All the elements it contains are kept, only the cluster is deleted.

            Args:
                label: label of the cluster to remove.
        """
        for index, cluster in enumerate(self._clusters):
            if cluster.label() == label:
                for node in cluster.nodes():
                    node.set_cluster(None)
                self._clusters.pop(index)
                return


    def check_clusterizability(self, nodes: List[Node]) -> bool:
        """ Returns True if a Cluster object can be contructed from the given
            list of Nodes.

            The requirements are:
                - more than one node
                - only direclty linked nodes (every node can be accessed from
                  any other node by going through inputs or outputs)
        """

        if len(nodes) < 2:
            return False

        # For each node, we check if at least one of its parents or children is
        # in the list:
        def _nodes_are_linked(node1: Node, node2: Node) -> bool:
            if node1 == node2:
                return False
            return node1 in (node2.parent_nodes() + node2.child_nodes())

        for node_to_check in nodes:
            node_ok = False # Is this node directly linked to any other node?
            for node in nodes:
                if _nodes_are_linked(node_to_check, node):
                    node_ok = True
                    continue
            if not node_ok:
                return False

        return True


    #
    # DYNAMIC GRAPH DATA FETCHING
    #

    def _get_dg_data(self) -> None:
        """ Fetches the graph data from the dynamic graph and fills the `_dg_entities`
            and `_input_nodes` lists with `Nodes`, `Ports` and `Edges`.
            This method does not create their qt items.
            Raises a ConnectionError if there is no connection to the kernel.
        """

        # Gettings every entity:
        entities_names = self._dg_communication.get_all_entities_names()
        if entities_names is None:
            return

        # For each entity, we will store its signals' infos to create edges later
        # (they have to be created after all ports have been created):
        entities_plugs_infos: Dict[EntityNode, List[str]] = {}

        for name in entities_names:
            # Creating the node:
            type = self._dg_communication.get_entity_type(name)
            new_node = EntityNode(name, type)
            self._dg_entities.append(new_node)

            # Creating the node's ports:
            entities_plugs_infos[new_node] = []
            sig_descriptions = self._dg_communication.get_entity_signals(name)
            for sig_description in sig_descriptions:
                plug_info = self._parse_signal_description(sig_description)
                if plug_info is None:
                    continue
                # Storing this plug's info:
                entities_plugs_infos[new_node].append(plug_info)
                # Adding this port to the node:
                new_node.add_port(plug_info['name'], plug_info['type'])

        # Linking the ports with edges:
        for (node, plugs_infos) in entities_plugs_infos.items():
            for plug_info in plugs_infos:
                # Creating the edge that will be plugged to this port:
                # We only handle input signals to prevent creating an edge twice
                if plug_info['type'] == 'input':
                    self._add_signal_to_dg_data(plug_info, node)

        # Getting the data of outputs with no edges:
        for node in self._dg_entities:
            for port in node.outputs():
                if port.edge() is None:
                    value = self._dg_communication.get_signal_value(node.name(),
                            port.name())
                    port.set_value(value)
                    last_exec = self._dg_communication.get_exec_time(
                                node.name(), port.name())
                    port.set_last_exec(last_exec)


    def _add_signal_to_dg_data(self, plug_info: Dict[str, str],
                                child_node: Node) -> None:
        """ Adds a signal to the dynamic graph data stored in this object.

            Args:
                plug_info: data on the signal (see _parse_signal_description for
                    details).
                child_node: head node of the signal, i.e the node having this
                    signal as an input.
        """
        sig_name = plug_info['name']
        child_node_name = child_node.name()

        # Getting the description of the plug this signal is plugged to,
        # i.e an output signal of the parent entity:
        is_plugged = self._dg_communication.is_signal_plugged(child_node_name, sig_name)
        if not is_plugged:
            return
        linked_plug_descr = self._dg_communication.get_linked_signal(child_node_name, sig_name)
        if linked_plug_descr is None: # If the node doesn't have a parent node
            return
        linked_plug_info = self._parse_signal_description(linked_plug_descr)

        signal_value = self._dg_communication.get_signal_value(child_node_name, sig_name)
        new_edge = Edge(signal_value, plug_info['value_type'])
        last_exec = self._dg_communication.get_exec_time(child_node_name, sig_name)
        new_edge.set_last_exec(last_exec)

        # Linking the signal to the child port:
        child_node.set_edge_for_port(new_edge, plug_info['name'])

        # If the signal is autoplugged (i.e has a fixed value instead of
        # being plugged to a another entity), the entity will appear as
        # linked to itself through this signal
        if child_node_name == linked_plug_info['entity_name']:
            # If the signal is autoplugged, we add an InputNode to the graph
            # to represent the input value
            new_node = InputNode(new_edge)
            self._input_nodes.append(new_node)
        else:
            # If the signal is not autoplugged, we link it to the parent entity
            parent_entity = self._get_node_per_name(linked_plug_info['entity_name'])
            parent_entity.set_edge_for_port(new_edge, linked_plug_info['name'])


    def _parse_signal_description(self, signal_description: str) -> Dict[str, str] | None:
        """ Parses a signal's description (e.g
            `'Add_of_double(add1)::input(double)::sin0'`) and returns a
            dictionary containing its information:
            - `name`: e.g `'sin0'`
            - `type`: `'input'` or `'output'`
            - `value_type`: type of the signal's value (e.g `'double'`)
            - `entity_name`: name of the entity plugged to the signal
            - `entity_type`: class name of the entity plugged to the
              signal (e.g `'Add_of_double'`)
        """
        try:
            split_description = signal_description.split("::")
            return dict(
                entity_type = split_description[0].split('(')[0],
                entity_name = split_description[0].split('(')[1].split(')')[0],
                type = split_description[1].split('(')[0],
                value_type = split_description[1].split('(')[1].split(')')[0],
                name = split_description[2]
            )
        except:
            print(f"Cannot handle signal: {signal_description}")
            return None


    def _clear_dg_data(self) -> None:
        """ Resets all the information on nodes, ports and edges and their qt items. """
        self._dg_entities = []
        self._input_nodes = []
        self._clusters = []
        self._graph_info = {}


    #
    # DOT CODE GENERATION
    #

    def _get_encoded_dot_code(self) -> bytes:
        """ Returns an encoded dot string of the graph data (as generated
            by the `_get_dg_data` method).
        """

        dot_generator = DotDataGenerator()

        # Setting the graph's layout to `left to right`:
        dot_generator.set_graph_attributes({'rankdir': quoted('LR')})

        # Adding the nodes and their ports (if needed), and then the edges:
        self._add_input_nodes_to_dot_code(dot_generator)
        self._add_entity_nodes_to_dot_code(dot_generator)
        self._add_clusters_to_dot_code(dot_generator)
        self._add_edges_to_dot_code(dot_generator)

        return dot_generator.get_encoded_dot_string()


    def _add_input_nodes_to_dot_code(self, dot_generator: DotDataGenerator) \
                                     -> None:
        """ Adds all of the graph's input nodes to the given dot data generator. """

        # From now on, every added node will be round:
        dot_generator.set_node_attributes({'shape': 'ellipse'})

        # For every input, we only display a node (and not its output port):
        for node in self._input_nodes:

            # If the node is in a cluster, we don't add it in the main graph
            if node.cluster() is not None:
                continue

            output_ports = node.outputs()
            if len(output_ports) != 1:
                raise ValueError("An InputNode should have exactly one output.")
            output_value = quoted(str(node.value()))
            dot_generator.add_node(node.name(), {'label': output_value})


    def _add_entity_nodes_to_dot_code(self, dot_generator: DotDataGenerator) \
                                      -> None:
        """ Adds all of the graph's entity nodes, with their ports, to the given
            dot data generator.
        """

        # From now on, every added node will have no shape (the html label will
        # make the shape):
        dot_generator.set_node_attributes({'shape': 'none'})

        for entity in self._dg_entities:

            # If the node is in a cluster, we don't add it in the main graph
            if entity.cluster() is not None:
                continue

            inputs = [port.name() for port in entity.inputs()]
            outputs = [port.name() for port in entity.outputs()]
            label = self._generate_entity_node_label(entity)

            dot_generator.add_html_node(entity.name(), (inputs, outputs), label)


    def _generate_entity_node_label(self, node: EntityNode) -> str:
        """ Generates a label to display on the node, according to its known
            information and labeling configuration.
        """
        node_type = node.type()
        node_name = node.name()

        if self._entities_labels_config is not None \
                and node_type in self._entities_labels_config:
            return self._entities_labels_config[node_type]
        if node_type is None:
            return node_name
        return f"{node_type}({node_name})"


    def _add_clusters_to_dot_code(self, dot_generator: DotDataGenerator) \
                                  -> None:
        """ Adds a cluster to the given dot data generator.

            The cluster will be added as a subgraph if it is expanded. Else, it
            will be added as an html node.
        """
        for cluster in self._clusters:
            if cluster.is_expanded():
                raise NotImplementedError
            else:
                inputs = [port.name() for port in cluster.inputs()]
                outputs = [port.name() for port in cluster.outputs()]
                dot_generator.add_html_node(cluster.name(), (inputs, outputs),
                                            cluster.label())


    def _add_edges_to_dot_code(self, dot_generator: DotDataGenerator):
        """ Adds all of the graph's edges to the given dot data generator. """

        # We only handle input edges so as to not add an edge twice: only entity
        # nodes and clusters can have inputs, and there is no final output
        # displayed
        for node in self._dg_entities + self.shrinked_clusters():

            # If the node is in a cluster, we ignore it as the cluster will be
            # handled later
            if node.cluster() is not None:
                continue

            for port in node.inputs():

                edge: Edge = port.edge()
                if edge is None: # If that port is not plugged to a signal
                    continue

                head_port: Port = port
                tail_port: Port = edge.tail()

                # If the tail is in a shrinked cluster, we link the edge to the
                # cluster port instead of the node port:
                tail_cluster: Cluster = self._get_cluster_for_port(tail_port)
                if tail_cluster is not None and not tail_cluster.is_expanded():
                    tail_port = tail_cluster.get_cluster_port_per_node_port(
                                tail_port)


                self._add_edge_to_dot_code(edge, head_port, tail_port,
                                           dot_generator)


    def _add_edge_to_dot_code(self, edge: Edge, head: Port, tail: Port,
                              dot_generator: DotDataGenerator) -> None:
        """ Adds an edge to a dot code generator.

            Args:
                edge: the edge to add.
                head: the head port of the edge, i.e the node input plugged to
                    this edge.
                tail: the tail port of the edge, i.e the node output plugged to
                    this edge.
                dot_generator: the DotDataGenerator to add the edge to.
        """

        child_port_name = head.name()
        child_node_name = head.node().name()

        parent_port_name = tail.name()
        parent_node = tail.node()
        parent_node_name = tail.node().name()

         # The value is displayed only if the parent node isn't an InputNode:
        attributes = None
        if not isinstance(tail.node(), InputNode):
            attributes = {'label': quoted(str(edge.value()))}

        # The tail port will not be displayed if the parent node is an input
        # value
        if isinstance(parent_node, InputNode):
            tail = (parent_node_name, None)
        else:
            tail = (parent_node_name, parent_port_name)

        head = (child_node_name, child_port_name)

        dot_generator.add_edge(tail, head, attributes)


    #
    # QT ITEMS GENERATION
    #

    def generate_qt_items(self) -> None:
        """ For each Node, Port and Edge, this function generates the
            corresponding list of qt items and stores it as their `_qt_item`
            attribute.
        """
        encoded_dot_code = self._get_encoded_dot_code()
        #print(encoded_dot_code.decode())

        (out, _) = Popen(['dot', '-Tjson'], stdin=PIPE, stdout=PIPE,
                   stderr=PIPE).communicate(encoded_dot_code)
        #print(out.decode())

        self._clear_qt_items()
        qt_generator = JsonToQtGenerator(out.decode('utf-8'))
        # For every node, we get its qt item (as a parent item containing the
        # other items):
        for node in (self._input_nodes + self._dg_entities +
                     self.shrinked_clusters()):

            # If the node is in a cluster, we ignore it as the cluster will be
            # handled later
            if node.cluster() is not None:
                continue

            # If it's an InputNode, only qt items for the node are needed (its
            # ports are not displayed and they have no input edges)
            if isinstance(node, InputNode):
                qt_item_node = qt_generator.get_qt_item_for_node(node.name())
                node.set_qt_item(qt_item_node)
                continue

            # If it's an EntityNode or a shrinked Cluster, the qt item
            # corresponding to the node is the middle column of the html table
            # (i.e the node's label)
            no_input = node.inputs() == []
            qt_item_node = qt_generator.get_qt_item_for_node(node.name(),
                                                             no_input)
            node.set_qt_item(qt_item_node)

            # Getting the qt items for each of the node's ports and edges:
            ports = node.ports()
            for port in ports:
                qt_item_port = qt_generator.get_qt_item_for_port(node.name(),
                                                                 port.name())
                port.set_qt_item(qt_item_port)

                if port.type() == 'output':
                    continue
                edge = port.edge()
                if edge is None:
                    continue
                head_node_name = node.name()

                tail_port = edge.tail()
                tail_cluster_port = self._get_cluster_port_for_port(tail_port)
                if tail_cluster_port is not None:
                    tail_port = tail_cluster_port
                tail_node_name = tail_port.node().name()

                qt_item_edge = qt_generator.get_qt_item_for_edge(head_node_name,
                                                                 tail_node_name)
                edge.set_qt_item(qt_item_edge)


    def _clear_qt_items(self) -> None:
        """ Clears all of the graph elements' qt items. """
        nodes = self._dg_entities + self._input_nodes + self._clusters
        for node in nodes:
            node.set_qt_item(None)

            if isinstance(node, InputNode):
                continue

            ports = node.ports()
            for port in ports:
                port.set_qt_item(None)
                if port.type() == 'input' and port.edge() is not None:
                    port.edge().set_qt_item(None)


    def get_qt_items(self) -> List[QGraphicsItem]:
        """ Returns a list of all the qt items necessary to display the graph.
        """

        qt_items = []

        def add_qt_item(qt_item: QGraphicsItem) -> None:
            if qt_item is not None:
                qt_items.append(qt_item)

        # For each node, we add the qt items of the node, of its ports, and of the
        # port's edge if it's an input (so that edges are not handled twice)
        nodes = self._dg_entities + self._input_nodes + self._clusters
        for node in nodes:
            if node.cluster() is not None:
                continue

            add_qt_item(node.qt_item())

            if isinstance(node, InputNode):
                continue

            ports = node.ports()
            for port in ports:
                add_qt_item(port.qt_item())
                if port.type() == 'input' and port.edge() is not None:
                    add_qt_item(port.edge().qt_item())

        return qt_items


    def get_elem_per_qt_item(self, qt_item: QGraphicsItem) \
                             -> Union[Node, Port, Edge]:
        """ Returns the graph element (node / port / edge) corresponding to a
            given qt item.

            If the qt item is a child item, the graph element of its highest
            parent is returned (e.g if a port label is clicked, the Port object
            is returned).
        """

        # Getting the parent item (e.g if item is a port's label, we must use
        # its parent, which is the outline of the cell)
        item = qt_item
        while item.parentItem() != None:
            item = item.parentItem()

        for node in (self._dg_entities + self._input_nodes
                     + self.shrinked_clusters()):
            if node.qt_item() == item:
                return node

            if isinstance(node, InputNode):
                continue

            for port in node.ports():
                if port.qt_item() == item:
                    return port

                edge = port.edge()
                if edge is not None and edge.qt_item() == item:
                    return edge

        return None


    def _get_cluster_port_for_port(self, port: Port) -> ClusterPort:
        """ Returns the ClusterPort corresponding to the given Port. """
        cluster = self._get_cluster_for_port(port)
        if cluster is None:
            return None
        return cluster.get_cluster_port_per_node_port(port)


    def _get_cluster_for_port(self, port: Port) -> Cluster:
        """ Returns the cluster containing the given node port. """
        return port.node().cluster()
