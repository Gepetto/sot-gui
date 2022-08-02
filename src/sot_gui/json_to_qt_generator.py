from typing import Any, Dict, List, Tuple, Union

from json import loads

from PySide2.QtWidgets import (QGraphicsItem, QGraphicsPolygonItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsPathItem)
from PySide2.QtGui import QPolygonF, QPainterPath, QBrush, QColor
from PySide2.QtCore import QRectF, QPointF

from sot_gui.utils import (get_dict_with_element, get_dicts_with_element,
    get_dict_with_element_in_list, get_dicts_with_element_in_list)


# Documentation on dot's json output:
# https://graphviz.org/docs/outputs/json/


class JsonParsingUtils:
    """ This is a helper class for parsing the dot's json output. """

    # Keys for lists of clusters, nodes and edges:
    OBJECTS = 'objects' # nodes and clusters
    EDGES = 'edges'
    CLUSTER_NODES = 'nodes'
    CLUSTER_EDGES = 'edges'

    # Keys for nodes, clusters and edges' identification:
    ID = '_gvid'
    NAME = 'name'
    HEAD_ID = 'head'
    TAIL_ID = 'tail'

    # Keys for display data of nodes and edges' parts:
    BODY_DRAW = '_draw_'
    HEAD_DRAW = '_hdraw_'
    TAIL_DRAW = '_tdraw_'
    LABEL_DRAW = '_ldraw_'
    HEAD_LABEL_DRAW = '_hldraw_'
    TAIL_LABEL_DRAW = '_tldraw_'

    # Keys for displayed elements' attributes:
    TYPE = 'op' # Type of the json data object
    DIMENSIONS = 'bb' # Bounding box of the graph or a cluster
    WIDTH = 'width'
    HEIGHT = 'height'
    POINTS = 'points'
    RECT = 'rect' # Ellipse's rectangle
    STYLE = 'style'
    COLOR = 'color'
    TEXT = 'text'
    TEXT_POS = 'pt'
    FONT = 'face'
    FONT_SIZE = 'size'

    # Possible values for json data objects' types (TYPE):
    T_STYLE = ['S']
    T_COLOR = ['c', 'C']
    T_FONT = ['F']
    T_TEXT = ['t', 'T']
    T_POLYGON = ['p', 'P']
    T_ELLIPSE = ['e', 'E']
    T_SPLINE = ['b', 'B']
    T_POLYLINE = ['L']


    def get_data_by_key_value(dict_list: List[Dict], key: str,
                                values: Union[Any, List[Any]]) -> Dict:
        """ From the dictionary list, returns the first one whose key/value pair
            corresponds to the given arguments, or None if none was found.
            `values` can be a single element or a list of possible values.
        """
        if isinstance(values, list):
            return get_dict_with_element_in_list(dict_list, key, values)
        else:
            return get_dict_with_element(dict_list, key, values)


    def get_data_list_by_key_value(dict_list: List[Dict], key: str, values:
            Union[Any, List[Any]]) -> List[Dict]:
        """ From the dictionary list, returns those whose key/value pairs
            correspond to the given arguments, or None if none was found.
            `values` can be a single element or a list of possible values.
        """
        if isinstance(values, list):
            return get_dicts_with_element_in_list(dict_list, key, values)
        else:
            return get_dicts_with_element(dict_list, key, values)


j = JsonParsingUtils


class JsonToQtGenerator:
    """ When given dot's json output as a string, this class can generate qt
        items for nodes, ports and edges.
    """

    def __init__(self, json_string: str):
        self._qt_generator_per_type = {
            # j.T_STYLE[0]: ,
            # j.T_COLOR[0] ,
            # j.T_COLOR[1]: ,
            # j.T_FONT[0]: ,
            j.T_TEXT[0]: self._generate_text,
            j.T_TEXT[1]: self._generate_text,
            j.T_POLYGON[0]: self._generate_polygon,
            j.T_POLYGON[1]: self._generate_polygon,
            j.T_ELLIPSE[0]: self._generate_ellipse,
            j.T_ELLIPSE[1]: self._generate_ellipse,
            j.T_SPLINE[0]: self._generate_spline,
            j.T_SPLINE[1]: self._generate_spline,
            # j.T_POLYLINE[0]: ,
        }

        self._graph_data: Dict[str, Any] = loads(json_string)

        # Getting the graph's dimensions:
        bounding_box = [ float(str) for str in self._graph_data[j.DIMENSIONS].split(',') ]
        self._graph_bounding_box = {
            'x': bounding_box[0],
            'y': bounding_box[1],
            'width': bounding_box[2],
            'height': bounding_box[3]
        }

        self._html_nodes_data: Dict[str, List[Tuple[List[Dict]]]] = {}
        self._init_html_nodes_data()


    #
    # Nodes and edges generation
    #

    def get_qt_item_for_node(self, node_name: str, no_input: bool = False) \
                             -> QGraphicsItem:
        """ Returns a qt item corresponding to a node.

            The qt item will be the node's body (i.e its shape OR the middle
            column of the html table) as the parent QGraphicsItem, which will
            contain the node label as a child item.
            All those items' positions will be set before return.
            If the node's style was set to invisible, this method will return
            None.

            Args:
                node_name: name of the node, as given in the dot code used to
                    generate the json output.
                no_input: True if the node has no input port displayed.
        """
        # Getting the dictionary containing data on the node:
        node_data = j.get_data_by_key_value(self._graph_data[j.OBJECTS], j.NAME,
                                            node_name)
        if node_data is None:
            raise ValueError(f"Node {node_name} could not be found in dot's"
                             " json output.")

        if node_data.get(j.STYLE) == 'invis': # If the node is invisible
            return None

        # If the node is represented in a regular way, the qt items generated
        # are its shape and its label. If it is represented as an html table,
        # the qt items for its body are the middle column's only cell and its
        # label, as the other columns correspond to the node's ports.
        qt_item_body = None

        # Html tables have no 'drawing body' data section. All info is found in
        # the 'drawing label' section.
        if j.BODY_DRAW in node_data: # Non-html case
            qt_item_shape = self._get_node_shape(node_data[j.BODY_DRAW])
            qt_item_body = qt_item_shape
            # Adding the node's label:
            label = self._get_label(node_data[j.LABEL_DRAW])
            label.setParentItem(qt_item_body)

        else: # Html case
            node_cells_data = self._html_nodes_data[node_name]
            label_cell_index = 0 if no_input else 1
            (outline_data, label_data) = node_cells_data[label_cell_index]
            qt_item_body = self._get_html_cell(outline_data, label_data)

        return qt_item_body


    def get_qt_item_for_port(self, node_name: str, port_name: str) \
                             -> QGraphicsItem:
        """ Returns a qt item corresponding to a port.

        Args:
            node_name: name of the node owning the port, as given in the dot
                code used to generate the json output.
            port_name: name of the port, as given in the dot code used to
                generate the json output. It must be the same as its label.

        Raises:
            RuntimeError: The port's data could not be found in the json output.
        """

        node_cells_data = self._html_nodes_data[node_name]

        for (cell_outline, cell_label) in node_cells_data:

            # The port we want is the one which has `port_name` as text in
            # its label data (cell_label)
            if j.get_data_by_key_value(cell_label, j.TEXT, port_name) is None:
                continue

            qt_item_port = self._get_html_cell(cell_outline, cell_label)
            return qt_item_port

        raise RuntimeError('JsonToQtGenerator.get_qt_item_for_port: '
                            'port data could not be found in json output.')


    def get_qt_item_for_edge(self, head_name: str, tail_name: str) -> QGraphicsItem:
        """ Generates and returns a qt item for the edge linked to the nodes named
            `head_name` and `tail_name` in the dot code used to generate the json output.
            The qt item will be the edge's body (i.e the spline) as the parent
            QGraphicsItem, which will contain the labels as a child items.
            All those items' positions will be set before return.
            If the edge's style was set to invisible, this method will return None.
        """
        # Getting the edge's display info:
        edge_data = self._get_edge_per_nodes_names(head_name, tail_name)
        if edge_data is None:
            raise ValueError(f"Could not find edge with tail {tail_name} and head\
                {head_name}.")

        if edge_data.get(j.STYLE) == 'invis': # If the edge is invisible
            return None

        # Getting the edge's curve, and the tail and head as its children:
        curve = self._get_edge_body(edge_data)
        if curve is None:
            return None

        # Getting the labels (label, headlabel, taillabel):
        for label_type in [j.LABEL_DRAW, j.HEAD_LABEL_DRAW, j.TAIL_LABEL_DRAW]:
            label_data = edge_data.get(label_type)
            if label_data is not None:
                label = self._get_label(label_data)
                label.setParentItem(curve)

        return curve


    def _get_node_shape(self, body_data: List[Dict]) -> QGraphicsItem:
        """ Generates and returns a qt item for a node's shape, with its position set.
            Returns None if the node has no shape.
        """
        # If the node has no shape:
        if body_data is None:
            return None

        # Getting the body's shape type and data (polygon or ellipse):
        shape_data = j.get_data_by_key_value(body_data, j.TYPE, j.T_POLYGON + j.T_ELLIPSE)
        if shape_data is None:
            return None
        shape_type = shape_data[j.TYPE]

        # Generating the shape:
        qt_item_body = self._qt_generator_per_type[shape_type](shape_data)
        return qt_item_body


    def _get_html_cell(self, outline_data: List[Dict], label_data: List[Dict]) \
            -> QGraphicsItem:
        """ Generates and returns qt items for a node's html table's cell,
            with their positions set. The outline will be the parent item, containing
            the label.
        """

        # Generating the outline:
        polygon_data = j.get_data_by_key_value(outline_data, j.TYPE, j.T_POLYGON)
        cell_outline = self._generate_polygon(polygon_data)

        # Generating the label:
        cell_label = self._get_label(label_data, False)
        cell_label.setParentItem(cell_outline)

        return cell_outline


    def _get_edge_body(self, edge_data: Dict[str, Any]) -> QGraphicsItem:
        """ Generates and returns qt items for an edge's body based on the given data,
            with their positions set.
            The body consists of the edge's spline, and its head.
        """

        # Getting the spline:
        spline_data = j.get_data_by_key_value(edge_data.get(j.BODY_DRAW), j.TYPE, j.T_SPLINE)
        if spline_data is None or spline_data.get(j.POINTS) is None:
            return None
        curve = self._generate_spline(spline_data.get(j.POINTS))

        # Getting the head and setting the curve as its parent:
        head_data = j.get_data_by_key_value(edge_data.get(j.HEAD_DRAW), j.TYPE, j.T_POLYGON)
        if head_data is not None and head_data.get(j.POINTS) is not None:
            head = self._generate_polygon(head_data)
            head.setBrush(QBrush(QColor("black"))) # Filling it with black
            head.setParentItem(curve)

        return curve


    def _get_label(self, label_data: List[Dict], compensate_width: bool = True) \
        -> QGraphicsItem:
        """ Generates and returns qt items for a label based on the given data,
            with their positions set.
            If `compensate_width` is True, the position of the label will be shifted
            to compensate for its width. It should always be necessary, except for a
            label in an html table.
        """

        # Each line or differently formatted piece of text will have its own
        # list of dictionaries
        label_pieces_data: List[List[Dict]] = []

        # If a type of info has already been added to a list of dicts, we switch
        # the next list
        stored_info_types = []

        new_label_piece_data = []
        for data in label_data:

            if data[j.TYPE] in stored_info_types: # Switching to a new piece of label
                label_pieces_data.append(new_label_piece_data)
                new_label_piece_data = []
                stored_info_types = []

            stored_info_types.append(data[j.TYPE])
            new_label_piece_data.append(data)

        label_pieces_data.append(new_label_piece_data)

        # The first piece of label will be the parent item, containing the other
        # pieces of text
        parent_qt_item = None
        parent_qt_coords = None

        for label_piece_data in label_pieces_data:

            # Getting the text:
            text_data = j.get_data_by_key_value(label_piece_data, j.TYPE, j.T_TEXT)
            new_qt_item = self._generate_text(text_data)

            # Getting its position in the scene:
            font_data = j.get_data_by_key_value(label_piece_data, j.TYPE, j.T_FONT)
            dot_coords = (text_data[j.TEXT_POS][0], text_data[j.TEXT_POS][1])
            qt_coords = self._dot_coords_to_qt_coords(dot_coords)

            if parent_qt_item is None:
                position = QPointF(
                    qt_coords[0] - ( (text_data[j.WIDTH] / 2) if compensate_width else 0 ),
                    qt_coords[1] - font_data[j.FONT_SIZE]
                )
                new_qt_item.setPos(position)

                parent_qt_coords = qt_coords
                parent_qt_item = new_qt_item

            else:
                # The child's position is relative to its parent:
                qt_coords = (qt_coords[0] - parent_qt_coords[0],
                            qt_coords[1] - parent_qt_coords[1])
                position = QPointF(
                    qt_coords[0],
                    qt_coords[1] + 2,
                )
                new_qt_item.setPos(position)
                new_qt_item.setParentItem(parent_qt_item)

        return parent_qt_item


    #
    # Basic QGraphicsItems generation
    #

    def _generate_polygon(self, data: Dict[str, Any]) -> QGraphicsPolygonItem:
        """ From dot output data, this method generates a polygon with qt
            coordinates.

            Args:
                data: dictionary corresponding to part of the dot output,
                    containing info on the polygon's vertices (coordinates).

            Returns: the polygon as a QGraphicsPolygonItem object.
        """
        polygon = QPolygonF()

        # Adding each of the polygon's points:
        for point in data[j.POINTS]:
            qt_coord = self._dot_coords_to_qt_coords((point[0], point[1]))
            polygon.append(QPointF(qt_coord[0], qt_coord[1]))

        polygonItem = QGraphicsPolygonItem(polygon)
        return polygonItem


    def _generate_ellipse(self, data: Dict[str, Any]) -> QGraphicsEllipseItem:
        """ From dot output data, this method generates an ellipse with qt
            coordinates.

            Args:
                data: dictionary corresponding to part of the dot output,
                    containing info on the ellipse coordinates.

            Returns: the ellipse as a QGraphicsEllipseItem object.
        """
        # Gettings the ellipse's rectangle's dimensions:
        rect_data = data[j.RECT]
        width = rect_data[2] * 2
        height = rect_data[3] * 2

        # Getting its coords:
        dot_coords = (rect_data[0] - width / 2, rect_data[1] + height / 2)
        qt_coords = self._dot_coords_to_qt_coords(dot_coords)

        # Creating the ellipse:
        rect = QRectF(qt_coords[0], qt_coords[1], width, height)
        ellipse = QGraphicsEllipseItem(rect)
        return ellipse


    def _generate_text(self, data: Dict[str, Any]) -> QGraphicsTextItem:
        """ From dot output data, this method generates text with qt
            coordinates.

            Args:
                data: dictionary corresponding to part of the dot output,
                    containing info on which text to display.

            Returns: a QGraphicsTextItem.
        """
        #font = QFont('Times', 14)
        text = QGraphicsTextItem(data[j.TEXT])
        #text.setFont(font)
        return text


    def _generate_spline(self, points_data: List) -> QGraphicsPathItem:
        """ From dot output data, this method generates a line / curve with qt
            coordinates.

            Args:
                data: dictionary corresponding to part of the dot output,
                    containing info on the line / curve coordinates.

            Returns: a QGraphicsPathItem, containing as many QPainterPaths as
                needed to create the whole line / curve.
        """
        # Getting the points qt coordinates:
        coordsQt = []
        for point in points_data:
           coordsQt.append(self._dot_coords_to_qt_coords((point[0], point[1])))

        # A spline is defined by Bezier spline control points.
        # The first 4 points are the first Bezier spline control points, the
        # next 4 points are the second B-spline, etc
        bezier_splines = []
        for i in range(1, len(coordsQt), 3):
            bezier_spline = []
            for j in range(-1, 3):
                bezier_spline.append(coordsQt[i + j])
            bezier_splines.append(bezier_spline)

        main_path = None
        for spline in bezier_splines:
            path = QPainterPath()

            # Setting the first point:
            path.moveTo(spline[0][0], spline[0][1])
            # Setting the 3 next points:
            path.cubicTo(spline[1][0], spline[1][1], spline[2][0], spline[2][1],
                         spline[3][0], spline[3][1])

            if main_path is None:
                main_path = path
            else:
                main_path.addPath(path)

        curve = QGraphicsPathItem(main_path)
        return curve


    #
    # Utils
    #

    def _dot_coords_to_qt_coords(self, coords: Tuple[float, float]) -> Tuple[float, float]:
        """ Converts dot coordinates (origin on the bottom-left corner) to Qt
            coordinates (origin on the top-left corner).
        """
        (x_coord, y_coord) = coords
        return (x_coord, self._graph_bounding_box['height'] - y_coord)


    def _get_node_id_per_name(self, name: str) -> int:
        """ Dot json output includes an id for each node and cluster.
            This method allows to retrieve a node or cluster id based on its
            name.

            Arg:
                name: name of the node or cluster to retrieve.

            Returns: The id given to the node / cluster by dot.
        """
        node = j.get_data_by_key_value(self._graph_data[j.OBJECTS], j.NAME, name)
        return node.get(j.ID)


    def _get_edge_per_nodes_names(self, head_name: str, tail_name: str) \
                                 -> Dict[str, Any]:
        """ Returns data on the edge with the given head and tail.

            Args:
                head_name: name of the head node, i.e the node which has the
                    wanted edge as an input.
                tail_name: name of the tail node, i.e the node which has the
                    wanted edge as an output.

            Returns: part of the dot json output corresponding to the edge.
        """
        # Retrieving the nodes' IDs:
        head_id = self._get_node_id_per_name(head_name)
        tail_id = self._get_node_id_per_name(tail_name)

        # Getting the edges whose heads are `head_name`:
        all_edges = self._graph_data[j.EDGES]
        edges_with_correct_head = j.get_data_list_by_key_value(all_edges, j.HEAD_ID, head_id)

        # Among these edges, finding the one whose tail is `tail_name`:
        edge = j.get_data_by_key_value(edges_with_correct_head, j.TAIL_ID, tail_id)
        return edge


    def _init_html_nodes_data(self) -> None:
        """ Structures and stores the html-style nodes' display data in
        self._graph_data.

        The data will be stored as a dictionary, each key being a node's name
        and its value being a list of the node's cells' display data.
        The display data for a cell is a tuple. Its first element is a list of
        the outline's data dictionaries, and its second element is a list of the
        label's data dictionaries.
        If the graph is empty, self._graph_data will remain an empty list.
        Storing this info at init prevents from recomputing each node's data
        when accessing its body and each of its ports.

        Raises:
            RuntimeError: The json data contains info on a node with less than
                2 cells
        """

        if j.OBJECTS not in self._graph_data: # If the graph is empty
            return

        for node in self._graph_data[j.OBJECTS]:
            # TODO: check that it's not a cluster

            if j.BODY_DRAW not in node: # If it's an html node
                node_data = self._get_html_table_data(node.get(j.LABEL_DRAW))

                # A node must have at least a label cell and an output cell
                if len(node_data) < 2:
                    raise RuntimeError('JsonToQtGenerator._init_html_nodes_data:'
                            " not enough cells in node's label json data.")

                self._html_nodes_data[node[j.NAME]] = node_data


    def _get_html_table_data(self, table_data: List[Dict]) -> List[Tuple[List[Dict]]]:
        """ Goes through a list of dictionaries corresponding to a node's html table
        display data (table outline, cells' outlines and cells' labels), and returns
        a list of every cell's display data.
        The display data for a cell is a tuple. Its first element is a list of the
        outline's data dictionaries, and its second element is a list of the label's
        data dictionaries.
        """
        table_data_list = []

        # For each cell, we get its outline's data and its label's data:
        cell_outline = []
        cell_label = []
        current_data_is_outline = True # Each cell data sequence is: outline, then label
        for data in table_data:
            if current_data_is_outline:
                cell_outline.append(data)
                # A label's data sequence ends with its text:
                if data[j.TYPE] in j.T_POLYGON:
                    current_data_is_outline = False

            else:
                cell_label.append(data)
                # An outline's data sequence ends with the coords of its vertices:
                if data[j.TYPE] in j.T_TEXT:
                    current_data_is_outline = True
                    table_data_list.append((cell_outline, cell_label))
                    cell_outline = []
                    cell_label = []

        return table_data_list