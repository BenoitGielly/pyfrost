"""Create a painDelta bifrost compound.

:author: Benoit Gielly <benoit.gielly@gmail.com>
"""

from .. import main


class PainDeltaGraph(main.Graph):
    """Custom Graph to paint deltas between 2 meshes."""

    board_name = "paintDelta"

    def __init__(self, *args, **kwargs):
        as_compound = kwargs.pop("kwargs", False)
        super(PainDeltaGraph, self).__init__(*args, **kwargs)
        self.create_graph(as_compound=as_compound)

    def create_graph(self, as_compound=False):
        """Create paintDelta node graph."""
        root = self
        if as_compound:
            root = self.create_node("compound", name=self.board_name)

        # create input ports
        input_node = root.node("/input")
        input_node.source.add("output", "Amino::Object")
        input_node.target.add("output", "Amino::Object")
        input_node.multiplier.add("output", "float")
        input_node.colorR.add("output", "float")
        input_node.colorG.add("output", "float")
        input_node.colorB.add("output", "float")

        # create node network
        sub = root.create_node("subtract")
        for each in ("target", "source"):
            node = root.create_node("get_point_position")
            input_node.attr(each).connect(node.geometry)
            node.point_position.connect(sub.attr(each + "_point_position"))

        vector3_to_scalar = root.create_node("vector3_to_scalar")
        sub.output.connect(vector3_to_scalar.vector3)

        add = root.create_node("add")
        for xyz in "xyz":
            power = root.create_node("power")
            vector3_to_scalar.attr(xyz).connect(power.base)
            power.exponent.set(2)
            power.power.connect(add.attr("power" + xyz.upper()))

        sqrt = root.create_node("square_root")
        add.output.connect(sqrt.value)

        multiply = root.create_node("multiply")
        sqrt.root.connect(multiply.sqrt)
        input_node.multiplier.connect(multiply.multiplier)

        scalar_to_vector3 = root.create_node("scalar_to_vector3")
        for xyz, rgb in zip("xyz", "RGB"):
            node = root.create_node("multiply")
            multiply.output.connect(node.attr("multiply" + xyz.upper()))
            input_node.attr("color" + rgb).connect(node.attr("color" + rgb))
            node.output.connect(scalar_to_vector3.attr(xyz))

        geo_prop = root.create_node("set_geo_property")
        geo_prop.property.set("color")
        geo_prop.default.set("{0, 0, 0, 1}")
        input_node.source.connect(geo_prop.geometry)
        scalar_to_vector3.vector3.connect(geo_prop.data)

        build_array = root.create_node("build_array")
        value = root.create_node("Core::Constants, array<array<float>>")
        value.output.connect(build_array.datatype)
        multiply.output.connect(build_array.weights)

        # add and connect to output ports
        output_node = root.node("/output")
        geo_prop.out_geometry.connect(output_node.outMesh)
        build_array.array.connect(output_node.weightList)
