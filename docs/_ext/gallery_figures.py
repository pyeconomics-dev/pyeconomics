# docs/_ext/gallery_figures.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Draw a gallery script's Plotly figure from this site's own copy of Plotly.js.

The scripts run inside the build, so they read Plotly's default renderer, whose
page loads Plotly.js and MathJax from their CDNs. This one names the copy
`html_static_path` publishes, and a figure needs no MathJax.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import plotly.io as pio
from plotly.io.base_renderers import MimetypeRenderer

if TYPE_CHECKING:
    from sphinx.application import Sphinx

#: The generated pages sit one directory below `_static`.
_PLOTLY_JS = "../_static/plotly.min.js"
_HEIGHT = "450px"
#: A figure draws while the page is still laying out, wider than the column it
#: ends up in. The theme then scales its SVG, which has no viewBox, so it is
#: cropped, axes first. `responsive` answers only a window's resize.
_FIT_THE_COLUMN = (
    'window.addEventListener("load", () => Plotly.Plots.resize("{plot_id}"));'
)


class GalleryRenderer(MimetypeRenderer):
    """Render a figure as HTML that loads nothing from another origin."""

    def to_mimebundle(self, fig_dict: dict[str, Any]) -> dict[str, str]:
        """Return the figure's HTML, for sphinx-gallery's ``_repr_html_`` capture."""
        html = pio.to_html(
            fig_dict,
            config={"responsive": True},
            default_width="100%",
            default_height=_HEIGHT,
            post_script=_FIT_THE_COLUMN,
            include_plotlyjs=_PLOTLY_JS,
            include_mathjax=False,
            full_html=False,
            validate=False,
        )
        return {"text/html": html}


def setup(app: Sphinx) -> dict[str, Any]:  # noqa: ARG001 - Sphinx's signature
    """Make the gallery's renderer the default for this build's process."""
    pio.renderers["gallery"] = GalleryRenderer()
    pio.renderers.default = "gallery"
    return {"parallel_read_safe": True, "parallel_write_safe": True}
