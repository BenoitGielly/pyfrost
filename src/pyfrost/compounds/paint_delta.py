"""Create a paintDelta bifrost compound.

:author: Benoit Gielly <benoit.gielly@gmail.com>

Based on the compound created by Iker J. de los Mozos:
https://forums.autodesk.com/t5/bifrost-forum/paintdeltamap-compound/td-p/8972674

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
        root["/input.source"].add("output", "Amino::Object")
        root["/input.target"].add("output", "Amino::Object")
        root["/input.multiplier"].add("output", "float")
        root["/input.colorR"].add("output", "float")
        root["/input.colorG"].add("output", "float")
        root["/input.colorB"].add("output", "float")

        # create node network
        sub = root.create_node("Core::Math,subtract")
        for each in ("target", "source"):
            node = root.create_node("Geometry::Properties,get_point_position")
            root["/input"][each].connect(node["geometry"])
            node["point_position"].connect(sub[each + "_point_position"])

        type_ = "Core::Conversion,vector3_to_scalar"
        vector3_to_scalar = root.create_node(type_)
        sub["output"].connect(vector3_to_scalar["vector3"])

        add = root.create_node("Core::Math,add")
        for xyz in "xyz":
            power = root.create_node("Core::Math,power")
            vector3_to_scalar[xyz].connect(power["base"])
            power["exponent"].value = 2
            power["power"].connect(add["power" + xyz.upper()])

        sqrt = root.create_node("Core::Math,square_root")
        add["output"].connect(sqrt["value"])

        multiply = root.create_node("Core::Math,multiply")
        sqrt["root"].connect(multiply["sqrt"])
        root["/input.multiplier"].connect(multiply["multiplier"])

        type_ = "Core::Conversion,scalar_to_vector4"
        scalar_to_vector4 = root.create_node(type_)
        for xyz, rgb in zip("xyz", "RGB"):
            node = root.create_node("Core::Math,multiply")
            multiply["output"].connect(node["multiply" + xyz.upper()])
            root["/input"]["color" + rgb].connect(node["color" + rgb])
            node["output"].connect(scalar_to_vector4[xyz])

        geo_prop = root.create_node("Geometry::Properties,set_geo_property")
        root["/input.source"].connect(geo_prop["geometry"])
        scalar_to_vector4["vector4"].connect(geo_prop["data"])
        geo_prop["property"].value = "color"
        geo_prop["default"].value = "{0, 0, 0, 1}"

        build_array = root.create_node("Core::Array,build_array")
        value = root.create_node("Core::Constants, array<array<float>>")
        value["output"].connect(build_array["datatype"])
        multiply["output"].connect(build_array["weights"])

        # add and connect to output ports
        geo_prop["out_geometry"].connect(root["/output.outMesh"])
        build_array["array"].connect(root["/output.weightList"])
