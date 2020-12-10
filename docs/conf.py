# pylint: disable=invalid-name, protected-access, redefined-builtin
"""Default sphinx configuration file.

This file should be used as a template for any sphinx generated documentation.

Note:
    pip install sphinx sphinx-rtd-theme m2r2

:author: Benoit Gielly <benoit.gielly@gmail.com>
"""
import datetime
import os
import shutil
import sys

try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser


# -- Parse configuration file ----------------------------------------------
today_date = datetime.datetime.now()
cwd = os.getcwd()
project_root = os.path.dirname(cwd)
cfg_file = ConfigParser()
cfg_file.read(os.path.join(project_root, "setup.cfg"))
project_cfg = cfg_file._sections.get("project", {})
_project_name = project_cfg.get("project_name", "[project]")
_project_author = project_cfg.get("project_author", "Benoit GIELLY")
_project_version = project_cfg.get("project_version", "1.0.0")
_project_sources = project_cfg.get("project_src_dir", "").split()
_repository_url = project_cfg.get("repository_url", "")

sphinx_cfg = cfg_file._sections.get("sphinx", {})
_sphinx_syspath = sphinx_cfg.get("custom_syspath", "").split()
_sphinx_mock = sphinx_cfg.get("mock_modules", "").split()
_sphinx_order = sphinx_cfg.get("member_order", "bysource")


# -- General configuration ---------------------------------------------
# Add source folders to sys.path
for each_ in _project_sources:
    sys.path.insert(0, os.path.join(project_root, each_))
sys.path.extend(_sphinx_syspath)

# setup extensions
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.extlinks",
    "sphinx.ext.todo",
    "m2r2",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
    "": "markdown",
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3.7", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
}

extlinks = {}
if _repository_url:
    extlinks.update({"issue": ("{}/issues/%s".format(_repository_url), "")})

todo_include_todos = True
templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"

project = _project_name
copyright = "2013-{} | {}, All Rights Reserved.".format(
    today_date.year, _project_author
)

release = _version = _project_version

exclude_patterns = ["_build"]
add_function_parentheses = True
add_module_names = False
show_authors = True
pygments_style = "default"


# -- Options for HTML output -------------------------------------------
# html_theme = "alabaster"
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "prev_next_buttons_location": "both",
    "navigation_depth": -1,
}

html_static_path = ["_static"]
htmlhelp_basename = _project_name + "doc"


# -- Options for Apidoc --------------------------------------------------
autodoc_mock_imports = _sphinx_mock
autodoc_member_order = _sphinx_order
autodoc_default_options = {
    "members": None,
    "undoc-members": None,
    "special-members": None,
    "show-inheritance": None,
    "exclude-members": "__dict__,__weakref__,__module__,staticMetaObject",
}


# -- Sphinx App Configuration --------------------------------------------
def setup(app):
    """Sphinx app setup."""
    # run apidoc automatically on each build
    app.connect("builder-inited", run_apidoc)


def run_apidoc(_):
    """Generate apidoc.

    See: https://github.com/rtfd/readthedocs.org/issues/1139
    """
    import sphinx
    from sphinx.ext import apidoc

    logger = sphinx.util.logging.getLogger(__name__)
    logger.info("Running apidoc...")
    api_folder = os.path.join(cwd, "_api")
    template_folder = os.path.join(cwd, "_templates")

    if os.path.exists(api_folder):
        shutil.rmtree(api_folder)
    os.mkdir(api_folder)

    argv = ["-M", "--separate", "-t", template_folder, "-o", api_folder]
    for each in _project_sources:
        module = os.path.join(project_root, each)
        apidoc.main(argv + [module])
        if os.path.exists(os.path.join(api_folder, "modules.rst")):
            os.remove(os.path.join(api_folder, "modules.rst"))
