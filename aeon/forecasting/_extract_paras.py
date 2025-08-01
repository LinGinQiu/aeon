"""ARIMA Utility Function."""

import numpy as np
from numba import njit


@njit(cache=True, fastmath=True)
def _extract_arma_params(params, model):
    """Extract ARIMA parameters from the parameter vector."""
    n_parts = len(model)
    starts = np.zeros(n_parts, dtype=np.int32)
    for i in range(1, n_parts):
        starts[i] = starts[i - 1] + model[i - 1]

    max_len = np.max(model)
    result = np.empty((n_parts, max_len), dtype=params.dtype)
    for i in range(n_parts):
        for j in range(max_len):
            result[i, j] = np.nan

    for i in range(n_parts):
        length = model[i]
        start = starts[i]
        for j in range(length):
            result[i, j] = params[start + j]

    return result
