# Utility functions

`aeon` has a number of modules dedicated to utilities:

- `aeon.pipeline`, which contains functions for pipeline construction.
- `aeon.testing`, which contains functions for estimator testing and data generation.
- `aeon.utils`, which contains generic utility functions.


## Pipeline

```{eval-rst}
.. currentmodule:: aeon.pipeline

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    make_pipeline
    sklearn_to_aeon
```

## Testing

### Data Generation

```{eval-rst}
.. currentmodule:: aeon.testing.data_generation

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    make_example_3d_numpy
    make_example_2d_numpy_collection
    make_example_3d_numpy_list
    make_example_2d_numpy_list
    make_example_dataframe_list
    make_example_2d_dataframe_collection
    make_example_multi_index_dataframe
    make_example_1d_numpy
    make_example_2d_numpy_series
    make_example_pandas_series
    make_example_dataframe_series
```

### Estimator Checking

```{eval-rst}
.. currentmodule:: aeon.testing.estimator_checking

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    check_estimator
    parametrize_with_checks
```

### Mock Estimators

```{eval-rst}
.. currentmodule:: aeon.testing.mock_estimators

.. autosummary::
    :toctree: auto_generated/
    :template: class.rst

    MockAnomalyDetector
    MockAnomalyDetectorRequiresFit
    MockAnomalyDetectorRequiresY
    MockClassifier
    MockClassifierPredictProba
    MockClassifierFullTags
    MockClassifierParams
    MockClassifierComposite
    MockCluster
    MockDeepClusterer
    MockCollectionTransformer
    MockForecaster
    MockRegressor
    MockRegressorFullTags
    MockSegmenter
    MockSegmenterRequiresY
    MockSeriesTransformer
    MockUnivariateSeriesTransformer
    MockMultivariateSeriesTransformer
    MockSeriesTransformerNoFit
    MockSeriesSimilaritySearch
    MockCollectionSimilaritySearch
```

### Utilities

```{eval-rst}
.. currentmodule:: aeon.testing.utils.deep_equals

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    deep_equals

.. currentmodule:: aeon.testing.utils.output_suppression
```

```{eval-rst}
.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    suppress_output
```

## Utils

### Estimator Discovery & Tags

```{eval-rst}
.. currentmodule:: aeon.utils.base

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    get_identifier
```

```{eval-rst}
.. currentmodule:: aeon.utils.discovery

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    all_estimators
```

```{eval-rst}
.. currentmodule:: aeon.utils.tags

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    check_valid_tags
    all_tags_for_estimator
```

### Data Conversion & Validation

```{eval-rst}
.. currentmodule:: aeon.utils.conversion

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    resolve_equal_length_inner_type
    resolve_unequal_length_inner_type
    convert_collection
    convert_series
```

```{eval-rst}
.. currentmodule:: aeon.utils.validation

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    is_int
    is_float
    is_timedelta
    is_date_offset
    is_timedelta_or_date_offset
    check_n_jobs
    check_window_length
    get_n_cases
    get_type
    is_equal_length
    has_missing
    is_univariate
    is_univariate_series
    is_single_series
    is_collection
    is_tabular
    is_hierarchical
```

### Numba

```{eval-rst}
.. currentmodule:: aeon.utils.numba.general

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    unique_count
    first_order_differences
    first_order_differences_2d
    first_order_differences_3d
    z_normalise_series_with_mean
    z_normalise_series
    z_normalise_series_with_mean_std
    z_normalise_series_2d
    z_normalise_series_2d_with_mean_std
    z_normalise_series_3d
    set_numba_random_seed
    choice_log
    get_subsequence
    get_subsequence_with_mean_std
    sliding_mean_std_one_series
    combinations_1d
    slope_derivative
    slope_derivative_2d
    slope_derivative_3d
    generate_combinations
    get_all_subsequences
    compute_mean_stds_collection_parallel
    prime_up_to
    is_prime
```

```{eval-rst}
.. currentmodule:: aeon.utils.numba.stats

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    mean
    row_mean
    count_mean_crossing
    row_count_mean_crossing
    count_above_mean
    row_count_above_mean
    quantile
    row_quantile
    median
    row_median
    quantile25
    row_quantile25
    quantile75
    row_quantile75
    std
    std_with_mean
    row_std
    numba_min
    row_numba_min
    numba_max
    row_numba_max
    slope
    row_slope
    iqr
    row_iqr
    ppv
    row_ppv
    fisher_score
    gini
    gini_gain
```

```{eval-rst}
.. currentmodule:: aeon.utils.numba.wavelets

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    haar_transform
    multilevel_haar_transform
```

### Other

```{eval-rst}
.. currentmodule:: aeon.utils.self_supervised.general

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    z_normalization
```

```{eval-rst}
.. currentmodule:: aeon.utils.repr

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    show_versions
```

```{eval-rst}
.. currentmodule:: aeon.utils.repr

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    show_versions
```

```{eval-rst}
.. currentmodule:: aeon.utils.show_versions

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    show_versions
```

```{eval-rst}
.. currentmodule:: aeon.utils.sklearn

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    is_sklearn_estimator
    sklearn_estimator_identifier
    is_sklearn_transformer
    is_sklearn_classifier
    is_sklearn_regressor
    is_sklearn_clusterer
```

```{eval-rst}
.. currentmodule:: aeon.utils.split

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    split_series
```

```{eval-rst}
.. currentmodule:: aeon.utils.windowing

.. autosummary::
    :toctree: auto_generated/
    :template: function.rst

    sliding_windows
    reverse_windowing
```
