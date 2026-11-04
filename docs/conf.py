# docs/conf.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Sphinx configuration for the 1.0 documentation preview."""

import sys
from importlib.metadata import version as distribution_version
from ipaddress import ip_address
from pathlib import Path

import plotly

sys.path.insert(0, str(Path(__file__).parent / "_ext"))


def offline_build(event: str, args: tuple[object, ...]) -> None:
    """Allow only local kernel connections during the build."""
    if event == "socket.connect":
        address = args[1]
        if isinstance(address, tuple):
            host = str(address[0])
            if host == "localhost" or ip_address(host).is_loopback:
                return
            message = "Documentation builds cannot connect to the network"
            raise OSError(message)


sys.addaudithook(offline_build)

project = "pyeconomics"
copyright = "2026, Nathan Ramos, CFA"  # noqa: A001
author = "Nathan Ramos, CFA"
release = distribution_version("pyeconomics")
extensions = [
    "myst_nb",
    "autoapi.extension",
    "sphinx.ext.napoleon",
    "sphinx_gallery.gen_gallery",
    "gallery_figures",
    "in_browser",
    "model_pages",
    "study_paths",
    "provider_pages",
    "concept_pages",
    "problem_pages",
]
myst_enable_extensions = ["dollarmath", "amsmath"]
nb_execution_mode = "force"
nb_execution_raise_on_error = True
nb_execution_timeout = 120
# The scripts run in this process, so the audit hook above holds them offline.
sphinx_gallery_conf = {
    "examples_dirs": "examples",
    "gallery_dirs": "gallery",
    "filename_pattern": r"\.py$",
    "within_subsection_order": "FileNameSortKey",
    "abort_on_example_error": True,
    "download_all_examples": False,
    # A generated .ipynb would be a source to MyST-NB.
    "notebook_extensions": set(),
    # A figure is Plotly's, through gallery_figures, so nothing here scrapes one.
    "image_scrapers": (),
    "reset_modules": (),
    "default_thumb_file": str(
        Path(__file__).parent / "_static" / "brand" / "pyeconomics-avatar.png"
    ),
    "write_computation_times": False,
    "show_signature": False,
}
exclude_patterns = [
    "_build/**",
    "_ext/**",
    "examples/**",
    "roadmap/**",
    "adr/**",
    "releases/**",
    "operations/**",
    "phase*-qa-findings.md",
    "conftest.py",
]
autoapi_dirs = ["../src/pyeconomics"]
autoapi_type = "python"
autoapi_keep_files = False
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]
napoleon_numpy_docstring = True
napoleon_google_docstring = False
# AutoAPI indexes dataclass fields; Napoleon renders their descriptions as a
# field list so the same attribute is not indexed a second time.
napoleon_use_ivar = True
html_theme = "pydata_sphinx_theme"
html_title = "pyeconomics 1.0 preview"
templates_path = ["_templates"]
# gallery_figures points a gallery page at this copy of Plotly.js.
html_static_path = [
    "_static",
    str(Path(plotly.__file__).parent / "package_data" / "plotly.min.js"),
]
html_logo = "_static/brand/pyeconomics-mark.svg"
html_favicon = "_static/brand/pyeconomics-mark.svg"
html_theme_options = {
    "logo": {"text": html_title},
    "announcement": (
        "1.0 preview: APIs may change. Stable documentation is for 0.2.6."
    ),
    "footer_start": ["copyright", "notices-link"],
    "footer_end": ["sphinx-version"],
}
