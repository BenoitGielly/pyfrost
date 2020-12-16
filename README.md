# Introduction

`PyFrost` is an object oriented Python API for Maya Bifrost.
It simply wraps the [cmds.vnn](https://help.autodesk.com/view/BIFROST/ENU/?guid=__CommandsPython_index_html) commands.

It it still very early and has a lot of hardcoded stuff, but hopefully it will grow nicely over time (unless Autodesk provides a proper API!)

## License

The current repository is under [MIT License](LICENSE).

Feel free to use, change, and share it as you please.
You don't have to, but mentioning my name whenever you use source code from here would be much appreciated!

## API Documentation

You can find a generated sphinx documentation at <https://pyfrost-maya.readthedocs.io/en/latest/>

# Installation

`PyFrost` requires Autodesk Maya >= 2018 and the latest version of [Bifrost](https://makeanything.autodesk.com/bifrost), currently [2.2.0.1](https://help.autodesk.com/view/BIFROST/ENU/?guid=Bifrost_ReleaseNotes_release_notes_release_notes_2_2_0_0_html)

You can find a module file available in `pyfrost\src\module\modules\` which you can add to the `MAYA_MODULE_PATH` environment variable.
It'll allow Maya to pick up the whole repository automatically for you on startup.

You can always run `sys.path.append()` on the python source folder `pyfrost\src`.

# Usage

Once the module is installed, all you need to do is to run `import pyfrost` inside Maya.

Please note that importing `pyfrost.main` may cause a small freeze as it's also loading the `bifrostGraph` plugin, which can take some time.

Example multiply node:

```python
import pyfrost.main

# create a new graph node
graph = pyfrost.main.Graph("multiplyNode")

# get the input node and add a "value1" float output
root = graph["/input"]
root["value1"].add("output", "float")

# you can also just stack the full path with its attribute
graph["/input.value2"].add("output", "float")

# or you can keep the ports separated if you prefer to
graph["/input"]["value3"].add("output", "float")

# create a new multiply node
# Note: you can find the nodetype in the scriptEditor by creating a node manually first.
# Then remove the "BifrostGraph," that shows up before the node type
mult = graph.create_node("Core::Math,multiply")

# to connect you can use the bitwise operator
root["value1"] >> mult["value1"]

# if a port doesn't exist on either the target or the source,
# it will try to create a new one with the type set to "auto"
root["value2"] >> mult["new_value"]

# you can also use the default method for connection
graph["/input"]["value3"].connect(mult["another_value"])

# now lets connect that to the output of the graph
mult["output"] >> graph["/output"]["result"]
```
