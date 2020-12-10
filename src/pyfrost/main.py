"""Convenient class used to create bifrost node graphs in python.

:author: Benoit Gielly <benoit.gielly@gmail.com>

Bifrost VNN command documentation
https://help.autodesk.com/view/BIFROST/ENU/?guid=__CommandsPython_index_html

"""
import json
import logging
import os
import uuid

from maya import cmds

LOG = logging.getLogger(__name__)

NODE_LIBS = {
    # constant
    "float": "Core::Constants,float",
    "string": "Core::Constants,string",
    # generic
    "number_to_string": "Core::String,number_to_string",
    # arrays
    "build_array": "Core::Array,build_array",
    # vectors
    "vector3_to_scalar": "Core::Conversion,vector3_to_scalar",
    "scalar_to_vector3": "Core::Conversion,scalar_to_vector3",
    "scalar_to_vector4": "Core::Conversion,scalar_to_vector4",
    # maths
    "add": "Core::Math,add",
    "subtract": "Core::Math,subtract",
    "multiply": "Core::Math,multiply",
    "divide": "Core::Math,divide",
    "power": "Core::Math,power",
    "square_root": "Core::Math,square_root",
    # geometry
    "get_point_position": "Geometry::Properties,get_point_position",
    "set_geo_property": "Geometry::Properties,set_geo_property",
}

if not cmds.pluginInfo("bifrostGraph", query=True, loaded=True):
    cmds.loadPlugin("bifrostGraph")


class Graph(object):
    """Create a bifrost graph with convient methods."""

    board_name = "default"

    def __init__(self, board=None):
        self.board = self.get_board(board)
        self._nodes = []

        # add a string attribute to identify the board
        node_attr = self.board + ".board_name"
        if not cmds.objExists(node_attr):
            cmds.addAttr(self.board, longName="board_name", dataType="string")
        cmds.setAttr(node_attr, self.board_name, type="string")

    def __repr__(self):
        return '{}("{}")'.format(self.__class__.__name__, self.board)

    def __str__(self):
        return self.board

    def __getitem__(self, value):
        return self.get(value)

    @staticmethod
    def get_board(name=None):
        """Get existing or create new BifrostBoard."""
        if name and cmds.objExists(name):
            if cmds.nodeType(name) == "bifrostBoard":
                return name
        name = name if name else "bifrostGraph"
        board = cmds.createNode("bifrostBoard")
        return cmds.rename(board, name)

    @property
    def name(self):
        """Get the name of the board."""
        return self.board

    @name.setter
    def name(self, value):
        self.board = cmds.rename(self.board, value)

    @property
    def nodes(self):
        """Get nodes at the board/root level."""
        children = cmds.vnnCompound(self.board, "/", listNodes=True) or []
        return [self[x] for x in children]

    def create_node(self, type_, parent="/", name=None):
        """Create a new bifrost node in the graph."""
        return Node(self, parent, type_, name)

    def get(self, value):
        """Get given string as node or attr."""
        if "." in value:
            node, attr = value.replace(".first.", ".").split(".", 1)  # wtf??
            return Node(self, node).attr(attr)
        return Node(self, value)

    def node(self, *path):
        """Get an existing bifrost node in the graph."""
        return Node(self, "/".join([str(x) for x in path]))

    def from_json(self, path):  # WIP
        """Create a compound from JSON file."""
        # read json file
        data = {}
        if os.path.exists(path):
            with open(path, "r") as stream:
                data = json.load(stream)
        data = data.get("compounds", [None])[-1]
        if not data:
            return None

        # create main compound node to host the imported graph
        compound = self.create_node("compound", name="paintDelta")

        # create in/out plugs on compound root
        for each in data.get("ports", []):
            name = each.get("portName")
            direction = each.get("portDirection")
            type_ = each.get("portType", "auto")
            compound.attr(name).add(direction, type_)

        # create nodes
        for each in data.get("compoundNodes", []):
            name = each.get("nodeName")
            type_ = each.get("nodeType")
            if not type_:
                type_ = "Core::Constants," + each.get("valueType")
            node = self.create_node(type_, parent=compound, name=name)
            for port in each.get("multiInPortNames", []):
                node.attr(port).add("input")
            for meta in each.get("metadata", []):
                node.set_metadata((meta["metaName"], meta["metaValue"]))

        # create connections
        for each in data.get("connections", []):
            source = self.get(compound / each.get("source"))
            target = self.get(compound / each.get("target"))
            source.connect(target)

        # set values
        for each in data.get("values", []):
            name = each.get("valueName")
            type_ = each.get("valueType")
            value = each.get("value")
            if type_ == "float":
                value = value[:-1] if value.endswith("f") else value
            elif "Math::float" in type_:
                value = "{{{}}}".format(
                    ",".join([x[:-1] for x in value.values()])
                )
            else:
                value = str(value)
            self.get(compound / name).set(value)

        return compound


class Node(object):
    """Create Node object."""

    def __init__(self, graph, parent, nodetype=None, name=None):
        # private properties variables
        self._path = None
        self._uuid = None

        # default instance variables
        self.graph = graph
        self.board = graph.board
        self.is_compound = False
        self.path = parent

        # create new node if `nodetype` is given
        if nodetype:
            self._create(nodetype, name)

    def __repr__(self, *args, **kwargs):
        return '{}("{}")'.format(self.__class__.__name__, self.path)

    def __str__(self):
        return str(self.path)

    def __add__(self, value):
        return "{}{}".format(self.path, value)

    def __div__(self, value):
        separator = "" if str(value).startswith((".", "/")) else "/"
        return "{}{}{}".format(self.path, separator, value)

    def __getattr__(self, attribute):
        return self.attr(attribute)

    def get_children(self):
        """Get children nodes."""
        try:
            nodes = cmds.vnnCompound(self.board, self, listNodes=True)
            return [self.node(x) for x in nodes]
        except RuntimeError:
            return []

    def create_node(self, type_, name=None):
        """Create a new node in the current compound."""
        if self.is_compound:
            return Node(self, self.path, type_, name)
        raise RuntimeError("Can only add nodes to compounds!")

    def _create(self, nodetype, name=None):
        """Create a bifrost node in the current graph."""
        path = self.path
        if nodetype == "compound":
            node = cmds.vnnCompound(self.board, path, create="compound")
            self.is_compound = True
        else:
            nodetype = self._fix_type(nodetype)
            type_ = self.board + "," + nodetype
            if nodetype in NODE_LIBS:
                type_ = self.board + "," + NODE_LIBS[nodetype]
            separator = "" if path.endswith("/") else "/"
            node = cmds.vnnCompound(self.board, path, addNode=type_)[0]
            node = "{}{}{}".format(path, separator, node)

        if not node:
            msg = "Can't create node '{}' (Type: '{}')".format(path, nodetype)
            raise RuntimeError(msg)

        self.path = node
        self.set_metadata(["UUID", str(uuid.uuid4()).upper()])
        self.rename(name)

    def rename(self, name):
        """Rename node."""
        if not name or self.name == name:
            return None

        all_nodes = cmds.vnnCompound(self.board, self.parent, listNodes=True)
        cmds.vnnCompound(self.board, self.parent, renameNode=[self.name, name])
        new_nodes = cmds.vnnCompound(self.board, self.parent, listNodes=True)

        node = list(set(new_nodes) - set(all_nodes))[0]
        self.path = self.parent + node
        return self.path

    @staticmethod
    def _fix_type(type_):
        """Fix nodeType when queried from the vnnNode command."""
        split = type_.rsplit("::", 1)
        if not "," in split[-1]:
            type_ = ",".join(split)
        return type_

    def node(self, path):
        """Get a child of this node."""
        node = "/".join([self.path, path]).replace("//", "/")
        return Node(self, node)

    def attr(self, attribute):
        """Return the attribute class."""
        return Attribute(self, attribute)

    # Properties ---
    @property
    def path(self):
        """Get node's path."""
        return self._path

    @path.setter
    def path(self, value):
        value = str(value)
        self._path = "/" + value if not value.startswith("/") else value

    @property
    def name(self):
        """Get node's name."""
        return [x for x in self.path.split("/") if x][-1]

    @property
    def parent(self):
        """Get node's parent."""
        return self.path.rsplit("/", 1)[0] + "/"
        # return self.path[: self.path.rfind("/") + 1]

    @property
    def type(self):
        """Get node's type."""
        type_ = cmds.vnnNode(self.board, self, queryTypeName=True)
        return self._fix_type(type_)

    @property
    def uuid(self):
        """Get node's UUID."""
        return cmds.vnnNode(self.board, self, queryMetaData="UUID") or None

    def set_metadata(self, metadata):
        """Set node metadata."""
        cmds.vnnNode(self.board, self, setMetaData=metadata)


class Attribute(object):
    """Create Attribute object."""

    def __init__(self, node_object, attribute=None):
        if attribute == "__apiobject__":  # maya whatever...
            raise RuntimeError()

        self.node = node_object
        self.board = self.node.board
        self.name = attribute
        self.plug = "{}.{}".format(node_object, attribute)

    # Builtin Methods ---
    def __str__(self):
        return self.plug

    def __repr__(self):
        return '{}("{}")'.format(self.__class__.__name__, self.plug)

    def __rshift__(self, plug):
        return self.connect(plug)

    def __floordiv__(self, plug):
        return self.disconnect(plug)

    # Properties ---
    @property
    def exists(self):
        """Check if attribute exists."""
        existing = []
        for each in cmds.vnnNode(self.board, self.node, listPorts=True) or []:
            existing.append(each.split(".", 1)[-1])
        return self.name in existing

    @property
    def type(self):
        """Get attribute type."""
        return cmds.vnnNode(self.board, self.node, queryPortDataType=self.name)

    # @property
    # def value(self):
    #     """Query or set plug default value."""
    #     node = self.node if self.node.type else self.node.parent
    #     return cmds.vnnNode(self.board, node, queryPortDefaultValues=self.name)

    # @value.setter
    # def value(self, value):
    #     self.set(value)

    def get(self):
        """Get attribute value."""
        node = self.node if self.node.type else self.node.parent
        return cmds.vnnNode(self.board, node, queryPortDefaultValues=self.name)

    def set(self, value):
        """Set attribute value."""
        kwargs = {"setPortDefaultValues": [self.name, value]}
        if self.node.parent == "/" and not self.node.type:
            cmds.vnnCompound(self.board, self.node.parent, **kwargs)
            return
        node = self.node if self.node.type else self.node.parent
        cmds.vnnNode(self.board, node, **kwargs)

    def add(self, direction, datatype="auto", value=None):
        """Add input plug on given node."""
        if not direction in ("input", "output"):
            raise NameError('`direction` must be either "input" or "output"')
        key = "createInputPort" if direction == "input" else "createOutputPort"

        cmd = cmds.vnnCompound if self.node.is_compound else cmds.vnnNode
        cmd(self.board, self.node, **{key: [self.name, datatype]})

        _ = self.set(value) if value else None

    def connect(self, target):
        """Connect plugs."""
        if not self.exists:
            self.add("output")
        if not target.node.type:  # case: output node
            target.add("input", self.type)
        if not target.exists:
            target.add("input")
        cmds.vnnConnect(self.board, self, target)

    def disconnect(self, target):
        """Disconnect plugs."""
        cmds.vnnConnect(self.board, self, target, disconnect=True)
