"""Convenient class used to create bifrost node graphs in python.

:author: Benoit Gielly <benoit.gielly@gmail.com>

Bifrost VNN command documentation
https://help.autodesk.com/view/BIFROST/ENU/?guid=__CommandsPython_index_html

"""
from __future__ import absolute_import, print_function

import json
import logging
import os
import uuid

from maya import cmds

LOG = logging.getLogger(__name__)


if not cmds.pluginInfo("bifrostGraph", query=True, loaded=True):
    cmds.loadPlugin("bifrostGraph")


class Graph(object):
    """Create a new bifrost graph object."""

    board_name = "default"

    def __init__(self, board=None):
        self.board = self._validate_board(board)
        self._create_name_attribute()
        self._nodes = []

    def __repr__(self):
        return '{}("{}")'.format(self.__class__.__name__, self.board)

    def __str__(self):
        return self.board

    def __getitem__(self, key):
        return self.get(key)

    def get(self, name):
        """Get given string as node or attr."""
        if name is None:
            return name

        name, _, attr = name.partition(".")
        node = Node(self, name)
        if attr:
            attr = attr.replace(".first.", ".")  # wtf??
            return node[attr]
        return node

    def _create_name_attribute(self):
        """Create a name attribute to identify the board."""
        # add a string attribute to identify the board
        node_attr = self.board + ".board_name"
        if not cmds.objExists(node_attr):
            cmds.addAttr(self.board, longName="board_name", dataType="string")
        cmds.setAttr(node_attr, self.board_name, type="string")

    @staticmethod
    def _validate_board(name=None):
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
        return [self.get(x) for x in children]

    def create_node(self, type_, parent="/", name=None):
        """Create a new bifrost node in the graph."""
        return Node(self, parent, type_, name)

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
            compound[name].add(direction, type_)

        # create nodes
        for each in data.get("compoundNodes", []):
            name = each.get("nodeName")
            type_ = each.get("nodeType")
            if not type_:
                type_ = "Core::Constants," + each.get("valueType")
            node = self.create_node(type_, parent=compound, name=name)
            for port in each.get("multiInPortNames", []):
                node[port].add("input")
            for meta in each.get("metadata", []):
                node.set_metadata((meta["metaName"], meta["metaValue"]))

        # create connections
        for each in data.get("connections", []):
            source = compound[each.get("source")]
            target = compound[each.get("target")]
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
            compound["/" + name].value = value

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

    def __getitem__(self, key):
        # handles ".first." attribute
        if ".first." in key:
            key = key.replace(".first.", ".")

        # handles normal node path
        if key.startswith("/"):
            return self.node(key)

        # handles duplicate dots (node..attr)
        if key.startswith("."):
            key = key[1:]

        # handles key "node.attr" not starting with "/"
        if "." in key and not key.startswith("."):
            return self.node("/" + key)

        return self.attr(key)

    def attr(self, value):
        """Return the attribute class."""
        return Attribute(self, value)

    def node(self, value):
        """Get a child of this node."""
        if "." in value:
            node, attr = value.split(".", 1)
            node = self.node(node)
            return node[attr]
        node = "/".join([self.path, value]).replace("//", "/")
        return Node(self, node)

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
        """Rename node.

        Note:
            the `renameNode` option doesn't return the new name, so the
            only way to figure out the unique name is to query all nodes,
            rename, query again and diff...(cool stuff, right?!)
        """
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
        type_ = cmds.vnnNode(self.board, self.path, queryTypeName=True)
        type_ = self._fix_type(type_)
        if type_.lower().startswith(self.board.lower()):
            type_ = type_.split(",", 1)[-1]
        return type_

    @property
    def uuid(self):
        """Get node's UUID."""
        return cmds.vnnNode(self.board, self.path, queryMetaData="UUID")

    def set_metadata(self, metadata):
        """Set node metadata."""
        cmds.vnnNode(self.board, self.path, setMetaData=metadata)


class Attribute(object):
    """Create Attribute object."""

    def __init__(self, node_object, attribute=None):
        self.node = node_object
        self.parent = str(node_object)
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
        nodes = cmds.vnnNode(self.board, str(self.node), listPorts=True) or []
        for each in nodes:
            existing.append(each.split(".", 1)[-1])
        return self.name in existing

    @property
    def type(self):
        """Get attribute type."""
        return cmds.vnnNode(
            self.board, str(self.node), queryPortDataType=self.name
        )

    @property
    def value(self):
        """Get and set attribute value."""
        node = self.node if self.node.type else self.node.parent
        return cmds.vnnNode(
            self.board, str(node), queryPortDefaultValues=self.name
        )

    @value.setter
    def value(self, value):
        if not value and not isinstance(value, (int, float, bool, str)):
            return
        kwargs = {"setPortDefaultValues": [self.name, value]}
        if self.node.parent == "/" and not self.node.type:
            cmds.vnnCompound(self.board, self.node.parent, **kwargs)
            return
        node = self.node if self.node.type else self.node.parent
        cmds.vnnNode(self.board, str(node), **kwargs)

    def add(self, direction, datatype="auto", value=None):
        """Add input plug on given node."""
        if not direction in ("input", "output"):
            raise NameError('`direction` must be either "input" or "output"')
        key = "create{}Port".format(direction.title())
        cmd = cmds.vnnCompound if self.node.is_compound else cmds.vnnNode
        cmd(self.board, str(self.parent), **{key: [self.name, datatype]})
        self.value = value

    def connect(self, target):
        """Connect plugs."""
        if not self.exists:
            self.add("output")
        if not target.node.type:  # case: output node
            target.add("input", self.type)
        if not target.exists:
            target.add("input")
        cmds.vnnConnect(self.board, self.plug, target.plug)

    def disconnect(self, target):
        """Disconnect plugs."""
        cmds.vnnConnect(self.board, self.plug, target.plug, disconnect=True)
