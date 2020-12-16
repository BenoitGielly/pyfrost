"""Maya Node API.

:author: Benoit Gielly <benoit.gielly@gmail.com>

The intention here is to build a node API specific to each DDC (here, Maya),
so in the main.py we can call that and remove the `cmds` calls.

When a DCC is started, the relevant API is injected in the Main one.

Note:
    This is a Work in Progress for now and not in use.

Example:
    If we were to rewrite the `pyfrost.main.Graph.validate_board` method, we
    could like that::

        def __init__(self):
            self.api = Api()

        def validate_board(self, name=None):
            node = self.api[name]
            if node.exists and node.type == "bifrostBoard":
                return name
            name = name if name else "bifrostGraph"
            board = api.create("bifrostBoard", name)
            return board.name

    That way, all the main code remains clean of DCC commands.
    Obviously, each DCCs APIs must be implemented the same way
    for this to work.

"""
from __future__ import absolute_import

from functools import partial
import logging

from maya import cmds

LOG = logging.getLogger(__name__)


class MayaAPI(object):
    """Create a Maya API object."""

    def __repr__(self):
        return "{}()".format(self.__class__.__name__)

    def __getitem__(self, key):
        return self.get(key)

    def create(self, nodetype, name=None):
        """Create new node."""
        kwargs = {"name": name} if name else {}
        node = cmds.createNode(nodetype, **kwargs)
        return MayaNode(self, node)

    def get(self, name):
        """Get existing node."""
        if name is None:
            return None

        name, _, attr = name.partition(".")
        if cmds.objExists(name):
            node = MayaNode(self, name)
            return node[attr] if attr else node
        msg = "Node '%s' doesn't exists. Use the 'create' method instead."
        return LOG.debug(msg, name)


class MayaNode(object):
    """Get MayaNode object."""

    def __init__(self, api, node):
        self.api = api
        self.node = node
        self.name = str(node)

    def __repr__(self, *args, **kwargs):
        return '{}("{}")'.format(self.__class__.__name__, self.node)

    def __str__(self):
        return self.name

    def __getitem__(self, key):
        return MayaAttr(self, key)

    def type(self):
        """Get node type."""
        return cmds.nodeType(self.name)

    def rename(self, name):
        """Rename node."""
        self.node = cmds.rename(self.name, name)
        self.name = str(self.node)


class MayaAttr(object):
    """Create a Maya Attribute class."""

    def __init__(self, node, name):
        self.api = node.api
        self.node = node
        self.name = name

        if self.exists():
            self._type = cmds.getAttr(self.plug, type=True)

    def __repr__(self):
        return "{obj.__class__.__name__}({obj.plug})".format(obj=self)

    def __str__(self):
        return self.plug

    @property
    def plug(self):
        """Get plug."""
        return "{obj.node}.{obj.name}".format(obj=self)

    def exists(self):
        """Check if node exists."""
        return cmds.objExists(self.plug)

    @property
    def value(self):
        """Get & set attribute's value."""
        return self.get()

    @value.setter
    def value(self, value):
        self.set(value)

    @property
    def type(self):
        """Get & set attribute's type."""
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    def add(self, type_, **kwargs):
        """Add attribute on node."""
        # if attr already exists, just set its value if passed.
        value = kwargs.pop("value", None)
        if self.exists() and value is not None:
            self.value = value
            LOG.debug("'%s' already exists, only setting value.", self.plug)
            return

        # update type
        self.type = type_

        # dealing with default value (doesn't work if string attribute...)
        if value is not None and self.type != "string":
            kwargs["defaultValue"] = value
        cmds.addAttr(
            self.node.name, longName=self.name, dataType=type_, **kwargs
        )
        if self.type == "string":
            self.value = value

    def get(self):
        """Set node's attribute value."""
        return cmds.getAttr(self.plug)

    def set(self, value):
        """Set node's attribute value."""
        kwargs = {"type": self.type} if self.type == "string" else {}
        func = partial(cmds.setAttr, self.plug, value, **kwargs)
        if isinstance(value, (list, tuple)):
            func = partial(cmds.setAttr, self.plug, *value, **kwargs)
        return func()

    def connect(self, target):
        """Connect current node to target."""
        if not isinstance(target, MayaAttr):
            target = self.api[target]
        cmds.connectAttr(self, target, force=True)

    def disconnect(self, target):
        """Disconnect current node from target."""
        if not isinstance(target, MayaAttr):
            target = self.api[target]
        cmds.disconnectAttr(self, target)
