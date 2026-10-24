# docs/conf.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Sphinx configuration for the 1.0 documentation preview."""

import sys
from importlib.metadata import version as distribution_version
from ipaddress import ip_address
from pathlib import Path

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
    "model_pages",
    "provider_pages",
    "concept_pages",
    "problem_pages",
]
myst_enable_extensions = ["dollarmath", "amsmath"]
nb_execution_mode = "force"
nb_execution_raise_on_error = True
nb_execution_timeout = 120
exclude_patterns = [
    "_build/**",
    "_ext/**",
    "roadmap/**",
    "adr/**",
    "releases/**",
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
html_static_path = ["_static"]
html_logo = "_static/brand/pyeconomics-mark.svg"
html_favicon = "_static/brand/pyeconomics-mark.svg"
html_theme_options = {
    "logo": {"text": html_title},
    "announcement": (
        "1.0 alpha preview: APIs may change. Stable documentation is for 0.2.6."
    ),
    "footer_start": ["copyright", "notices-link"],
    "footer_end": ["sphinx-version"],
}
