import numpy as np
import spyndex

green = np.array([0.3, 0.2, 0.0], dtype=np.float64)
swir1 = np.array([0.1, 0.2, 0.0], dtype=np.float64)

with np.errstate(divide="ignore", invalid="ignore"):
    result = spyndex.computeIndex("MNDWI", {"G": green, "S1": swir1})

expected = np.array([0.5, 0.0, np.nan])
np.testing.assert_allclose(result, expected, equal_nan=True)
print("MNDWI cross-check passed:", result.tolist())
print("formula:", spyndex.indices.MNDWI.formula)
