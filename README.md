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
It'll allow Maya to pick up the whole repo automatically for you on startup.

You can always run `sys.path.append()` on the python source folder `pyfrost\src`.

# Usage

Once the module is installed, all you need to do is to run `import pyfrost` inside Maya.

Please note that importing `pyfrost.main` may cause a freeze of Maya as it's also ensuring the `bifrostGraph` plugin is loaded, which is taking some time.

Example multiply node:

```python
graph = pyfrost.main.Graph("multiplyNode")

mult = graph.create_node("multiply")

root = graph["/input"]
root.value1.add("output", "float")
root.value2.add("output", "float")
root.value1 >> mult.value1
root.value2 >> mult.value2
mult.output >> graph["/output"].result
```

If you don't like the `>>` operator to connect nodes, you can always use the `Attribute.connect()` method.

```python
root.value1.connect(mult.value1)
```
