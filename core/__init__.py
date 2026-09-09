"""HAND flood-modelling core used by the Streamlit workflow."""

import numpy as np

# pysheds 0.5 still calls np.in1d, which was removed in NumPy 2.4+.
if not hasattr(np, "in1d"):
    np.in1d = np.isin
