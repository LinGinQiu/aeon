"""Symbolic Fourier Approximation (SFA) Transformer.

Configurable SFA transform for discretising time series into words.

"""

__maintainer__ = []
__all__ = ["SFAFast"]

import math
import sys
from warnings import simplefilter

import numpy as np
import scipy.fft
from numba import (
    NumbaPendingDeprecationWarning,
    NumbaTypeSafetyWarning,
    njit,
    objmode,
    prange,
)
from numba.core import types
from numba.typed import Dict
from scipy.sparse import csr_matrix
from sklearn.feature_selection import chi2, f_classif
from sklearn.preprocessing import KBinsDiscretizer
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.utils import check_random_state

from aeon.transformations.collection import BaseCollectionTransformer
from aeon.utils.numba.general import AEON_NUMBA_STD_THRESHOLD
from aeon.utils.validation import check_n_jobs

# The binning methods to use: equi-depth, equi-width, information gain or kmeans
binning_methods = {
    "equi-depth",
    "equi-width",
    "information-gain",
    "information-gain-mae",
    "kmeans",
    "quantile",
}

simplefilter(action="ignore", category=NumbaPendingDeprecationWarning)
simplefilter(action="ignore", category=NumbaTypeSafetyWarning)


class SFAFast(BaseCollectionTransformer):
    """Symbolic Fourier Approximation (SFA) Transformer.

    Overview: for each series:
        run a sliding window across the series
        for each window
            shorten the series with DFT
            discretise the shortened series into bins set by MFC
            form a word from these discrete values
    by default SFA produces a single word per series (window_size=0)
    if a window is used, it forms a histogram of counts of words.

    Parameters
    ----------
    word_length : int, default = 8
        Length of word to shorten window to (using DFT).
    alphabet_size : int, default = 4
        Number of values to discretise each value to.
    window_size : int, default = 12
        Size of window for sliding. Input series length for whole series transform.
    norm : boolean, default = False
        Mean normalise words by dropping first fourier coefficient.
    binning_method : str, default="equi-depth"
        The binning method used to derive the breakpoints. One of {"equi-depth",
        "equi-width", "information-gain", "information-gain-mae", "kmeans"},
    anova : boolean, default = False
        If True, the Fourier coefficient selection is done via a one-way ANOVA test.
        If False, the first Fourier coefficients are selected. Only applicable if
        labels are given.
    variance : boolean, default = False
        If True, the Fourier coefficient selection is done via the largest variance.
        If False, the first Fourier coefficients are selected. Only applicable if
        labels are given.
    dilation : int, default = 0
        When set to dilation > 1, adds dilation to the sliding window operation.
    save_words : boolean, default = False
        whether to save the words generated for each series (default False)
    bigrams : boolean, default = False
        Whether to create bigrams of SFA words.
    feature_selection : {"chi2", "chi2_top_k", "none", "random"}, default: none
        Sets the feature selections strategy to be used. Large amounts of memory
        may be needed depending on the setting of bigrams (true is more) or
        alpha (larger is more).
        'chi2' reduces the number of words, keeping those above the 'p_threshold'.
        'chi2_top_k' reduces the number of words to at most 'max_feature_count',
        dropping values based on p-value.
        'random' reduces the number to at most 'max_feature_count',
        by randomly selecting features.
        'none' does not apply any feature selection and yields large bag of words,
    p_threshold :  int, default=0.05 (disabled by default)
        If feature_selection=chi2 is chosen, feature selection is applied based on
        the chi-squared test. This is the p-value threshold to use for chi-squared
        test on bag-of-words (lower means more strict). 1 indicates that the test
        should not be performed.
    max_feature_count :  int, default=256
        If feature_selection=random is chosen, this parameter defines the number of
        randomly chosen unique words used.
    skip_grams : boolean, default = False
        Whether to create skip-grams of SFA words.
    remove_repeat_words : boolean, default = False
       Whether to use numerosity reduction.
    lower_bounding_distances : boolean, default = None
       If set to True, the FFT is normed to allow for ED lower bounding.
    sampling_factor : float, default = None
       If set to a value <1.0, this percentage of samples are used to learn MCB bins.
    return_sparse :  boolean, default=True
        If set to true, a scipy sparse matrix will be returned as BOP model.
        If set to false a dense array will be returned as BOP model. Sparse
        arrays are much more compact.
    n_jobs : int, default = 1
        The number of jobs to run in parallel for both `transform`.
        ``-1`` means using all processors.

    Attributes
    ----------
    breakpoints: = []
    num_insts = 0
    num_atts = 0


    References
    ----------
    .. [1] Schäfer, Patrick, and Mikael Högqvist. "SFA: a symbolic fourier approximation
    and  index for similarity search in high dimensional datasets." Proceedings of the
    15th international conference on extending database technology. 2012.
    """

    _tags = {
        "requires_y": False,  # SFA is unsupervised for equi-depth and equi-width bins
        "capability:multithreading": True,
        "algorithm_type": "dictionary",
    }

    def __init__(
        self,
        word_length=8,
        alphabet_size=4,
        window_size=12,
        norm=False,
        binning_method="equi-depth",
        anova=False,
        variance=False,
        bigrams=False,
        skip_grams=False,
        remove_repeat_words=False,
        lower_bounding=True,
        lower_bounding_distances=None,
        save_words=False,
        dilation=0,
        first_difference=False,
        feature_selection="none",
        max_feature_count=256,
        p_threshold=0.05,
        sampling_factor=None,
        random_state=None,
        return_sparse=True,
        n_jobs=1,
    ):
        self.words = []
        self.breakpoints = []

        # we cannot select more than window_size many letters in a word
        self.word_length = word_length

        self.alphabet_size = alphabet_size
        self.window_size = window_size

        self.norm = norm
        self.lower_bounding = lower_bounding
        self.lower_bounding_distances = lower_bounding_distances

        self.inverse_sqrt_win_size = self.initialize_inverse_sqrt_win_size()

        self.remove_repeat_words = remove_repeat_words

        self.save_words = save_words

        self.binning_method = binning_method
        self.anova = anova
        self.variance = variance

        self.bigrams = bigrams
        self.skip_grams = skip_grams
        self.n_jobs = n_jobs

        self.n_cases = 0
        self.n_timepoints = 0
        self.letter_bits = 0

        self.dilation = dilation
        self.first_difference = first_difference
        self.sampling_factor = sampling_factor

        # Feature selection part
        self.feature_selection = feature_selection
        self.max_feature_count = max_feature_count
        self.feature_count = 0
        self.relevant_features = None

        # feature selection is applied based on the chi-squared test.
        self.p_threshold = p_threshold

        self.return_sparse = return_sparse

        self.random_state = random_state
        super().__init__()

    def _fit_transform(self, X, y=None, return_bag_of_words=True):
        """Fit to data, then transform it."""
        self._n_jobs = check_n_jobs(self.n_jobs)

        if self.alphabet_size < 2:
            raise ValueError("Alphabet size must be an integer greater than 2")

        if (
            self.binning_method == "information-gain"
            or self.binning_method == "information-gain-mae"
        ) and y is None:
            raise ValueError(
                "Class values must be provided for information gain binning"
            )

        if self.variance and self.anova:
            raise ValueError(
                "Please set either variance or anova Fourier coefficient selection"
            )

        if self.binning_method not in binning_methods:
            raise TypeError("binning_method must be one of: ", binning_methods)

        # If window_size was not set, assume whole series matching
        if self.window_size is None:
            self.window_size = X.shape[-1]

        offset = 2 if self.norm else 0
        self.word_length_actual = min(self.window_size - offset, self.word_length)

        if self.word_length > X.shape[-1] and self.word_length_actual > X.shape[-1]:
            raise ValueError(
                "Please set the word-length to a value smaller than or equal to "
                "the time series length and window-length."
            )

        if self.sampling_factor and self.sampling_factor > 1.0:
            raise ValueError(
                "Please set the sampling_factor to a value smaller than or equal to "
                "1 (equals 100%)."
            )

        self.inverse_sqrt_win_size = self.initialize_inverse_sqrt_win_size()

        self.dft_length = (
            self.window_size - offset
            if (self.anova or self.variance) is True
            else self.word_length_actual
        )
        # make dft_length an even number (same number of reals and imags)
        self.dft_length = self.dft_length + self.dft_length % 2
        self.word_length_actual = self.word_length_actual + self.word_length_actual % 2

        self.support = np.arange(self.word_length_actual)
        self.letter_bits = np.uint32(math.ceil(math.log2(self.alphabet_size)))
        # self.word_bits = self.word_length_actual * self.letter_bits
        X = X.squeeze(1)

        # subsample the samples
        if self.sampling_factor:
            rng = check_random_state(self.random_state)
            sampled_indices = rng.choice(
                X.shape[0],
                size=min(np.int32(X.shape[0] * self.sampling_factor), X.shape[0]),
                replace=False,
            )
            X = X[sampled_indices]

        if self.dilation >= 1 or self.first_difference:
            X2, self.X_index = _dilation(X, self.dilation, self.first_difference)
        else:
            X2, self.X_index = X, np.arange(X.shape[-1])

        self.n_cases, self.n_timepoints = X2.shape
        self.breakpoints = self._binning(X2, y)

        # fitting: learns the feature selection strategy, too
        if return_bag_of_words:
            words, dfts = _transform_case(
                X2,
                self.window_size,
                self.dft_length,
                self.word_length_actual,
                self.norm,
                self.remove_repeat_words,
                self.support,
                self.anova,
                self.variance,
                self.breakpoints,
                self.letter_bits,
                self.bigrams,
                self.skip_grams,
                self.inverse_sqrt_win_size,
                self.lower_bounding or self.lower_bounding_distances,
            )

            if self.remove_repeat_words:
                words = remove_repeating_words(words)

            if self.save_words:
                self.words = words

            return self.transform_to_bag(words, self.word_length_actual, y)
        else:
            return None

    def _fit(self, X, y=None):
        """Calculate word breakpoints using MCB or IGB.

        Parameters
        ----------
        X : 3d numpy array, input time series.
        y : array_like, target values (optional, ignored).

        Returns
        -------
        self: object
        """
        # with parallel_backend("loky", inner_max_num_threads=n_jobs):
        self._fit_transform(X, y, return_bag_of_words=self.return_sparse)
        return self

    def _transform(self, X, y=None):
        """Transform data into SFA words.

        Parameters
        ----------
        X : 3d numpy array, input time series.

        Returns
        -------
        List of dictionaries containing SFA words
        """
        X = X.squeeze(1)

        if self.dilation >= 1 or self.first_difference:
            X2, self.X_index = _dilation(X, self.dilation, self.first_difference)
        else:
            X2, self.X_index = X, np.arange(X.shape[-1])

        words, dfts = _transform_case(
            X2,
            self.window_size,
            self.dft_length,
            self.word_length_actual,
            self.norm,
            self.remove_repeat_words,
            self.support,
            self.anova,
            self.variance,
            self.breakpoints,
            self.letter_bits,
            self.bigrams,
            self.skip_grams,
            self.inverse_sqrt_win_size,
            self.lower_bounding or self.lower_bounding_distances,
        )

        # only save at fit
        # if self.save_words:
        #    self.words = words

        # transform: applies the feature selection strategy
        empty_dict = Dict.empty(
            key_type=types.uint32,
            value_type=types.uint32,
        )

        # transform
        bags = create_bag_transform(
            self.X_index,
            self.feature_count,
            self.feature_selection,
            self.relevant_features if self.relevant_features else empty_dict,
            words,
            self.remove_repeat_words,
        )[0]

        if self.return_sparse:
            bags = csr_matrix(bags, dtype=np.uint32)
        return bags

    def initialize_inverse_sqrt_win_size(self):
        """Initialize the inverse square root constant."""
        if self.window_size:
            return (
                1.0 / math.sqrt(self.window_size)
                if (not self.lower_bounding or self.lower_bounding_distances)
                else 1.0
            )
        return 1

    def transform_mft(self, X):
        """Transform data using the Fourier transform.

        Parameters
        ----------
        X : 3d numpy array, input time series.

        Returns
        -------
        Array of Fourier coefficients
        """
        # X = X.squeeze(1)

        if self.dilation >= 1 or self.first_difference:
            X2, self.X_index = _dilation(X, self.dilation, self.first_difference)
        else:
            X2, self.X_index = X, np.arange(X.shape[-1])

        return _mft(
            X2,
            self.window_size,
            self.dft_length,
            self.norm,
            self.support,
            self.anova,
            self.variance,
            self.inverse_sqrt_win_size,
            self.lower_bounding or self.lower_bounding_distances,
        )

    def transform_to_bag(self, words, word_len, y=None):
        """Transform words to bag-of-pattern and apply feature selection."""
        bag_of_words = None
        rng = check_random_state(self.random_state)

        if self.feature_selection == "none" and (
            self.breakpoints.shape[1] <= 2
            and not self.bigrams
            and self.word_length <= 8
        ):
            bag_of_words = create_bag_none(
                self.X_index,
                self.breakpoints,
                words.shape[0],
                words,
                word_len,  # self.word_length_actual,
                self.remove_repeat_words,
            )
        else:
            feature_names = create_feature_names(words)

            if self.feature_selection == "none":
                feature_count = len(list(feature_names))
                relevant_features_idx = np.arange(feature_count, dtype=np.uint32)
                bag_of_words, self.relevant_features = create_bag_feature_selection(
                    self.X_index,
                    words.shape[0],
                    relevant_features_idx,
                    np.array(list(feature_names)),
                    words,
                    self.remove_repeat_words,
                )

            # Random feature selection
            elif self.feature_selection == "random":
                feature_count = min(self.max_feature_count, len(feature_names))
                relevant_features_idx = rng.choice(
                    len(feature_names), replace=False, size=feature_count
                )
                bag_of_words, self.relevant_features = create_bag_feature_selection(
                    self.X_index,
                    words.shape[0],
                    relevant_features_idx,
                    np.array(list(feature_names)),
                    words,
                    self.remove_repeat_words,
                )

            # Chi-squared feature selection taking
            # a) the top-k features
            # b) a p-threshold
            elif (
                self.feature_selection == "chi2_top_k"
                or self.feature_selection == "chi2"
            ):
                feature_names_array = np.array(list(feature_names))
                feature_count = len(feature_names_array)
                relevant_features_idx = np.arange(feature_count, dtype=np.uint32)
                bag_of_words, _ = create_bag_feature_selection(
                    self.X_index,
                    words.shape[0],
                    relevant_features_idx,
                    feature_names_array,
                    words,
                    self.remove_repeat_words,
                )

                # apply chi2-based feature selection
                chi2_statistics, p = chi2(bag_of_words, y)

                # p-threshold using 'p_threshold'
                if self.feature_selection == "chi2":
                    relevant_features_idx = np.where(p <= self.p_threshold)[0]

                # top-k using 'max_feature_count'
                else:
                    relevant_features_idx = np.argsort(p)[: self.max_feature_count]

                self.relevant_features = create_dict(
                    feature_names_array[relevant_features_idx],
                    np.arange(len(relevant_features_idx), dtype=np.uint32),
                )
                # select subset of features
                bag_of_words = bag_of_words[:, relevant_features_idx]

        self.feature_count = bag_of_words.shape[1]
        if self.return_sparse:
            bag_of_words = csr_matrix(bag_of_words, dtype=np.uint32)
        return bag_of_words

    def _binning(self, X, y=None):
        dft = _binning_dft(
            X,
            self.window_size,
            self.n_timepoints,
            self.dft_length,
            self.norm,
            self.inverse_sqrt_win_size,
            self.lower_bounding or self.lower_bounding_distances,
        )

        if y is not None:
            y = np.repeat(y, dft.shape[0] / len(y))

        if self.variance:
            # determine variance
            dft_variance = np.var(dft, axis=0)

            # select word-length-many indices with the largest variance
            self.support = np.argsort(-dft_variance)[: self.word_length_actual]

            # sort remaining indices
            self.support = np.sort(self.support)

            # select the Fourier coefficients with highest f-score
            dft = dft[:, self.support]
            self.dft_length = np.max(self.support) + 1
            self.dft_length = self.dft_length + self.dft_length % 2  # even

        if self.anova and y is not None:
            non_constant = np.where(
                ~np.isclose(dft.var(axis=0), np.zeros_like(dft.shape[1]))
            )[0]

            # select word-length many indices with best f-score
            if self.word_length_actual <= non_constant.size:
                f, _ = f_classif(dft[:, non_constant], y)
                self.support = non_constant[np.argsort(-f)][: self.word_length_actual]

            # sort remaining indices
            self.support = np.sort(self.support)

            # select the Fourier coefficients with highest f-score
            dft = dft[:, self.support]
            self.dft_length = np.max(self.support) + 1
            self.dft_length = self.dft_length + self.dft_length % 2  # even

        if self.binning_method == "information-gain":
            return self._igb(dft, y)
        if self.binning_method == "information-gain-mae":
            return self._igb_mae(dft, y)
        elif self.binning_method == "kmeans" or self.binning_method == "quantile":
            return self._k_bins_discretizer(dft)
        else:
            return self._mcb(dft)

    def _k_bins_discretizer(self, dft):
        encoder = KBinsDiscretizer(
            n_bins=self.alphabet_size, strategy=self.binning_method
        )
        encoder.fit(dft)
        if encoder.bin_edges_.ndim == 1:
            breaks = encoder.bin_edges_.reshape((-1, 1))
        else:
            breaks = encoder.bin_edges_
        breakpoints = np.zeros((self.word_length_actual, self.alphabet_size))

        for letter in range(self.word_length_actual):
            for bp in range(1, len(breaks[letter]) - 1):
                breakpoints[letter, bp - 1] = breaks[letter, bp]

        breakpoints[:, self.alphabet_size - 1] = sys.float_info.max
        return breakpoints

    def _mcb(self, dft):
        breakpoints = np.zeros((self.word_length_actual, self.alphabet_size))

        dft = np.round(dft, 2)
        for letter in range(self.word_length_actual):
            column = np.sort(dft[:, letter])
            bin_index = 0

            # use equi-depth binning
            if self.binning_method == "equi-depth":
                target_bin_depth = len(dft) / self.alphabet_size

                for bp in range(self.alphabet_size - 1):
                    bin_index += target_bin_depth
                    breakpoints[letter, bp] = column[int(bin_index)]

            # use equi-width binning aka equi-frequency binning
            elif self.binning_method == "equi-width":
                target_bin_width = (column[-1] - column[0]) / self.alphabet_size

                for bp in range(self.alphabet_size - 1):
                    breakpoints[letter, bp] = (bp + 1) * target_bin_width + column[0]

        breakpoints[:, self.alphabet_size - 1] = sys.float_info.max
        return breakpoints

    def _igb(self, dft, y):
        breakpoints = np.zeros((self.word_length_actual, self.alphabet_size))
        clf = DecisionTreeClassifier(
            criterion="entropy",
            max_depth=np.uint32(np.log2(self.alphabet_size)),
            max_leaf_nodes=self.alphabet_size,
            random_state=self.random_state,
        )

        for i in range(self.word_length_actual):
            clf.fit(dft[:, i][:, None], y)
            threshold = clf.tree_.threshold[clf.tree_.children_left != -1]
            for bp in range(len(threshold)):
                breakpoints[i, bp] = threshold[bp]
            for bp in range(len(threshold), self.alphabet_size):
                breakpoints[i, bp] = np.inf

        return np.sort(breakpoints, axis=1)

    def _igb_mae(self, dft, y):
        breakpoints = np.zeros((self.word_length, self.alphabet_size))
        clf = DecisionTreeRegressor(
            criterion="friedman_mse",
            max_depth=int(np.floor(np.log2(self.alphabet_size))),
            max_leaf_nodes=self.alphabet_size,
            random_state=self.random_state,
        )

        for i in range(self.word_length):
            clf.fit(dft[:, i][:, None], y)
            threshold = clf.tree_.threshold[clf.tree_.children_left != -1]
            for bp in range(len(threshold)):
                breakpoints[i][bp] = threshold[bp]
            for bp in range(len(threshold), self.alphabet_size):
                breakpoints[i][bp] = sys.float_info.max

        return np.sort(breakpoints, axis=1)

    def _shorten_bags(self, word_len, y):
        if self.save_words is False:
            raise ValueError(
                "Words from transform must be saved using save_word to shorten bags."
            )
        if self.bigrams:
            raise ValueError("Bigrams are currently not supported.")
        if self.variance or self.anova:
            raise ValueError(
                "Variance or Anova based feature selection is currently not supported."
            )

        # determine the new word-length
        new_len = min(word_len, self.word_length_actual)

        # the difference in word-length to shorten the words to
        new_len_diff = self.word_length_actual - new_len

        if new_len_diff > 0:
            new_words = shorten_words(self.words, new_len_diff, self.letter_bits)
        else:
            new_words = self.words

        # retrain feature selection-strategy
        return self.transform_to_bag(new_words, new_len, y)

    def get_words(self):
        """Return the words generated for each series.

        Returns
        -------
        Array of words
        """
        words = np.squeeze(self.words)
        return np.array(
            [_get_chars(word, self.word_length, self.alphabet_size) for word in words]
        )

    def transform_words(self, X):
        """Return the words and dft coefficients generated for each series.

        Parameters
        ----------
        X : 3d numpy array, all input time series.

        Returns
        -------
        Array of words
        """
        if X.ndim == 3:
            X = X.squeeze(1)

        words, dfts = _transform_words_case(
            X,
            self.window_size,
            self.dft_length,
            self.norm,
            self.support,
            self.anova,
            self.variance,
            self.inverse_sqrt_win_size,
            self.lower_bounding or self.lower_bounding_distances,
            self.word_length,
            self.alphabet_size,
            self.breakpoints,
        )
        return words.squeeze(1), dfts.squeeze(1)

    @classmethod
    def _get_test_params(cls, parameter_set="default"):
        """Return testing parameter settings for the estimator.

        Parameters
        ----------
        parameter_set : str, default="default"
            Name of the set of test parameters to return, for use in tests. If no
            special parameters are defined for a value, will return `"default"` set.

        Returns
        -------
        params : dict or list of dict, default = {}
            Parameters to create testing instances of the class
            Each dict are parameters to construct an "interesting" test instance, i.e.,
            `MyClass(**params)` or `MyClass(**params[i])` creates a valid test instance.
        """
        # small window size for testing
        params = [
            {
                "word_length": 4,
                "window_size": 4,
                "return_sparse": False,
                "feature_selection": "chi2",
                "alphabet_size": 2,
            },
            {
                "word_length": 4,
                "window_size": 4,
                "return_sparse": True,
                "feature_selection": "chi2",
                "alphabet_size": 2,
            },
        ]
        return params

    def __getstate__(self):
        """Return state as dictionary for pickling, required for typed Dict objects."""
        state = self.__dict__.copy()

        if type(state["relevant_features"]) is Dict:
            state["relevant_features"] = dict(state["relevant_features"])
        return state

    def __setstate__(self, state):
        """Set current state using input pickling, required for typed Dict objects."""
        self.__dict__.update(state)
        if isinstance(self.relevant_features, dict):
            typed_dict = Dict.empty(key_type=types.uint32, value_type=types.uint32)
            for key, value in self.relevant_features.items():
                typed_dict[key] = value
            self.relevant_features = typed_dict


@njit(cache=True, fastmath=True)
def _get_chars(word, word_length, alphabet_size):
    chars = np.zeros(word_length, dtype=np.uint32)
    letter_bits = int(np.log2(alphabet_size))
    mask = (1 << letter_bits) - 1
    for i in range(word_length):
        # Extract the last bits
        char = word & mask
        chars[-i - 1] = char

        # Right shift by to move to the next group of bits
        word >>= letter_bits

    return chars


@njit(fastmath=True, cache=True)
def _binning_dft(
    X,
    window_size,
    n_timepoints,
    dft_length,
    norm,
    inverse_sqrt_win_size,
    lower_bounding,
):
    num_windows_per_inst = math.ceil(n_timepoints / window_size)

    # Windowing
    if num_windows_per_inst > 1:
        # Splits individual time series into windows and returns the DFT for each
        data = np.zeros((len(X), num_windows_per_inst, window_size))
        for i in prange(len(X)):
            for j in range(num_windows_per_inst - 1):
                data[i, j] = X[i, window_size * j : window_size * (j + 1)]

            start = n_timepoints - window_size
            data[i, -1] = X[i, start:n_timepoints]

        dft = np.zeros((len(X), num_windows_per_inst, dft_length))
        for i in prange(len(X)):
            return_val = _fast_fourier_transform(
                data[i], norm, dft_length, inverse_sqrt_win_size, True
            )
            dft[i] = return_val

        if lower_bounding:
            dft[:, :, 1::2] = dft[:, :, 1::2] * -1  # lower bounding

        return dft.reshape(dft.shape[0] * dft.shape[1], dft_length)

    # No Windowing (Whole Series)
    else:
        dft = _fast_fourier_transform(X, norm, dft_length, inverse_sqrt_win_size, False)

        if lower_bounding:
            dft[:, 1::2] = dft[:, 1::2] * -1  # lower bounding

        return dft


@njit(fastmath=True, cache=True)
def _fast_fourier_transform(X, norm, dft_length, inverse_sqrt_win_size, norm_std=True):
    """Perform a discrete fourier transform using the fast fourier transform.

    if self.norm is True, then the first term of the DFT is ignored

    Input
    -------
    X : The training input samples.  array-like or sparse matrix of
    shape = [n_samps, num_atts]

    Returns
    -------
    1D array of fourier term, real_0,imag_0, real_1, imag_1 etc, length
    num_atts or
    num_atts-2 if if self.norm is True
    """
    # first two are real and imaginary parts
    start = 2 if norm else 0
    length = start + dft_length
    dft = np.zeros((len(X), length))  # , dtype=np.float64

    with objmode(X_ffts="complex128[:,:]"):
        X_ffts = scipy.fft.rfft(X, axis=1, workers=-1).astype(np.complex128)

    reals = np.real(X_ffts)  # float64[]
    imags = np.imag(X_ffts)  # float64[]
    dft[:, 0::2] = reals[:, 0 : length // 2]
    dft[:, 1::2] = imags[:, 0 : length // 2]
    dft *= inverse_sqrt_win_size

    # apply z-normalization
    if norm_std:
        stds = np.zeros(len(X))
        for i in range(len(stds)):
            stds[i] = np.std(X[i])
        # stds = np.std(X, axis=1)  # not available in numba
        stds = np.where(stds < AEON_NUMBA_STD_THRESHOLD, 1, stds)
        dft /= stds.reshape(-1, 1)

    return dft[:, start:]


@njit(fastmath=True, cache=True)
def _transform_case(
    X,
    window_size,
    dft_length,
    word_length,
    norm,
    remove_repeat_words,
    support,
    anova,
    variance,
    breakpoints,
    letter_bits,
    bigrams,
    skip_grams,
    inverse_sqrt_win_size,
    lower_bounding,
):
    dfts = _mft(
        X,
        window_size,
        dft_length,
        norm,
        support,
        anova,
        variance,
        inverse_sqrt_win_size,
        lower_bounding,
    )

    words = generate_words(
        dfts,
        bigrams,
        skip_grams,
        window_size,
        breakpoints,
        word_length,
        letter_bits,
    )

    if remove_repeat_words:
        words = remove_repeating_words(words)

    return words, dfts


@njit(fastmath=True, cache=True)
def remove_repeating_words(words):
    for i in range(words.shape[0]):
        last_word = 0
        for j in range(words.shape[1]):
            if last_word == words[i, j]:
                # We encode the repeated words as 0 and remove them
                # This is implementged using np.nonzero in numba. Thus must be 0
                words[i, j] = 0
            last_word = words[i, j]

    return words


@njit(fastmath=True, cache=True)
def _calc_incremental_mean_std(series, end, window_size):
    stds = np.zeros(end)
    window = series[0:window_size]
    series_sum = np.sum(window)
    square_sum = np.sum(np.multiply(window, window))

    r_window_length = 1.0 / window_size
    mean = series_sum * r_window_length
    buf = math.sqrt(max(square_sum * r_window_length - mean * mean, 0.0))
    stds[0] = buf if buf > AEON_NUMBA_STD_THRESHOLD else 1

    for w in range(1, end):
        series_sum += series[w + window_size - 1] - series[w - 1]
        mean = series_sum * r_window_length
        square_sum += (
            series[w + window_size - 1] * series[w + window_size - 1]
            - series[w - 1] * series[w - 1]
        )
        buf = math.sqrt(max(square_sum * r_window_length - mean * mean, 0.0))
        stds[w] = buf if buf > AEON_NUMBA_STD_THRESHOLD else 1

    return stds


@njit(fastmath=True, cache=True)
def _get_phis(window_size, length):
    phis = np.zeros(length)
    i = np.arange(length // 2)
    const = 2 * np.pi / window_size
    phis[0::2] = np.cos((-i) * const)
    phis[1::2] = -np.sin((-i) * const)
    return phis


@njit(fastmath=True, cache=True)
def generate_words(
    dfts, bigrams, skip_grams, window_size, breakpoints, word_length, letter_bits
):
    needed_size = dfts.shape[1]
    if bigrams:
        # allocate memory for bigrams
        needed_size += max(0, dfts.shape[1] - window_size)
    if skip_grams:
        # allocate memory for 2- and 3-skip-grams
        needed_size += max(0, 2 * dfts.shape[1] - 5 * window_size)

    words = np.zeros((dfts.shape[0], needed_size), dtype=np.uint32)

    letter_bits = np.uint32(letter_bits)
    word_bits = word_length * letter_bits  # dfts.shape[2] * letter_bits

    # special case: binary breakpoints
    if breakpoints.shape[1] == 2:
        vector = np.zeros((breakpoints.shape[0]), dtype=np.float32)
        for i in range(breakpoints.shape[0]):
            vector[i] = breakpoints.shape[1] ** i

        for a in prange(dfts.shape[0]):
            match = (dfts[a] <= breakpoints[:, 0]).astype(np.float32)
            words[a, : dfts.shape[1]] = np.dot(match, vector).astype(np.uint32)

    # general case: alphabet-size many breakpoints
    else:
        for a in prange(dfts.shape[0]):
            for i in range(word_length):  # range(dfts.shape[2]):
                words[a, : dfts.shape[1]] = (
                    words[a, : dfts.shape[1]] << letter_bits
                ) | np.digitize(dfts[a, :, i], breakpoints[i], right=True)

    # add bigrams
    if bigrams:
        for a in prange(0, dfts.shape[1] - window_size):
            first_word = words[:, a]
            second_word = words[:, a + window_size]
            words[:, dfts.shape[1] + a] = (first_word << word_bits) | second_word

    # # add 2,3-skip-grams
    # if skip_grams:
    #     for s in range(2, 4):
    #         for a in range(0, dfts.shape[1] - s * window_size):
    #             first_word = words[:, a]
    #             second_word = words[:, a + s * window_size]
    #             words[:, dfts.shape[1] + a] = (first_word << word_bits) | second_word

    return words


@njit(fastmath=True, cache=True)
def _mft(
    X,
    window_size,
    dft_length,
    norm,
    support,
    anova,
    variance,
    inverse_sqrt_win_size,
    lower_bounding,
):
    start_offset = 2 if norm else 0
    length = dft_length + start_offset + dft_length % 2
    end = max(1, len(X[0]) - window_size + 1)

    #  compute mask for only those indices needed and not all indices
    if anova or variance:
        support = support + start_offset
        indices = np.full(length, False)
        mask = np.full(length, False)
        for s in support:
            indices[s] = True
            mask[s] = True
            if (s % 2) == 0:  # even
                indices[s + 1] = True
            else:  # uneven
                indices[s - 1] = True
        mask = mask[indices]
    else:
        indices = np.full(length, True)

    phis = _get_phis(window_size, length)
    transformed = np.zeros((X.shape[0], end, length))

    # 1. First run using DFT
    with objmode(X_ffts="complex128[:, :]"):
        X_ffts = scipy.fft.rfft(X[:, :window_size], axis=1, workers=-1).astype(
            np.complex128
        )

    reals = np.real(X_ffts)  # float64[]
    imags = np.imag(X_ffts)  # float64[]
    transformed[:, 0, 0::2] = reals[:, 0 : length // 2]
    transformed[:, 0, 1::2] = imags[:, 0 : length // 2]

    # 2. Other runs using MFT
    # X2 = X.reshape(X.shape[0], X.shape[1], 1)
    # Bugfix to allow for slices on original X like in TEASER
    X2 = X.copy().reshape(X.shape[0], X.shape[1], 1)

    # compute only those indices needed and not all
    phis2 = phis[indices]
    transformed2 = transformed[:, :, indices]
    for i in range(1, end):
        reals = transformed2[:, i - 1, 0::2] + X2[:, i + window_size - 1] - X2[:, i - 1]
        imags = transformed2[:, i - 1, 1::2]
        transformed2[:, i, 0::2] = (
            reals * phis2[:length:2] - imags * phis2[1 : (length + 1) : 2]
        )
        transformed2[:, i, 1::2] = (
            reals * phis2[1 : (length + 1) : 2] + phis2[:length:2] * imags
        )

    transformed2 = transformed2 * inverse_sqrt_win_size

    if lower_bounding:
        transformed2[:, :, 1::2] = transformed2[:, :, 1::2] * -1

    # STD-normalization only applied for subsequences
    if end > 1:
        # compute STDs
        stds = np.zeros((X.shape[0], end))
        for a in range(X.shape[0]):
            stds[a] = _calc_incremental_mean_std(X[a], end, window_size)

        # divide all by stds and use only the best indices
        if anova or variance:
            return transformed2[:, :, mask] / stds.reshape(
                stds.shape[0], stds.shape[1], 1
            )
        else:
            return (transformed2 / stds.reshape(stds.shape[0], stds.shape[1], 1))[
                :, :, start_offset:
            ]

    # Whole-Series
    else:
        # Do not norm
        if anova or variance:
            return transformed2[:, :, mask]
        else:
            return transformed2[:, :, start_offset:]


def _dilation(X, d, first_difference):
    padding = np.zeros((len(X), 10))
    X = np.concatenate((padding, X, padding), axis=1)

    # using only first order differences
    if first_difference:
        X = np.diff(X, axis=1, prepend=0)

    # adding dilation
    X_dilated = _dilation2(X, d)
    X_index = _dilation2(
        np.arange(X_dilated.shape[-1], dtype=np.float64).reshape(1, -1), d
    )[0]

    return (
        X_dilated,
        X_index,
    )


@njit(cache=True, fastmath=True)
def _dilation2(X, d):
    # dilation on actual data
    if d > 1:
        start = 0
        data = np.zeros(X.shape, dtype=np.float64)
        for i in range(0, d):
            curr = X[:, i::d]
            end = curr.shape[1]
            data[:, start : start + end] = curr
            start += end
        return data
    else:
        return X.astype(np.float64)


@njit(cache=True, fastmath=True)
def create_feature_names(sfa_words):
    feature_names = set()
    for t_words in sfa_words:
        for t_word in t_words:
            feature_names.add(t_word)
    return feature_names


@njit(cache=True, fastmath=True)
def create_bag_none(
    X_index, breakpoints, n_cases, sfa_words, word_length, remove_repeat_words
):
    feature_count = np.uint32(breakpoints.shape[1] ** word_length)
    all_win_words = np.zeros((n_cases, feature_count), dtype=np.uint32)

    for j in prange(sfa_words.shape[0]):
        # this mask is used to encode the repeated words
        if remove_repeat_words:
            masked = np.nonzero(sfa_words[j])
            all_win_words[j, :] = np.bincount(
                sfa_words[j][masked], minlength=feature_count
            )
        else:
            all_win_words[j, :] = np.bincount(sfa_words[j], minlength=feature_count)

    return all_win_words


@njit(cache=True, fastmath=True)
def create_bag_feature_selection(
    X_index,
    n_cases,
    relevant_features_idx,
    feature_names,
    sfa_words,
    remove_repeat_words,
):
    relevant_features = Dict.empty(key_type=types.uint32, value_type=types.uint32)
    for k, v in zip(
        feature_names[relevant_features_idx],
        np.arange(len(relevant_features_idx), dtype=np.uint32),
    ):
        relevant_features[k] = v

    if remove_repeat_words:
        if 0 in relevant_features:
            del relevant_features[0]

    all_win_words = np.zeros((n_cases, len(relevant_features_idx)), dtype=np.uint32)
    for j in range(sfa_words.shape[0]):
        for key in sfa_words[j]:
            if key in relevant_features:
                all_win_words[j, relevant_features[key]] += 1
    return all_win_words, relevant_features


@njit(cache=True, fastmath=True)
def create_bag_transform(
    X_index,
    feature_count,
    feature_selection,
    relevant_features,
    sfa_words,
    remove_repeat_words,
):
    all_win_words = np.zeros((len(sfa_words), feature_count), np.uint32)
    for j in prange(sfa_words.shape[0]):
        if len(relevant_features) == 0 and feature_selection == "none":
            # this mask is used to encode the repeated words
            if remove_repeat_words:
                masked = np.nonzero(sfa_words[j])
                all_win_words[j, :] = np.bincount(
                    sfa_words[j][masked], minlength=feature_count
                )
            else:
                all_win_words[j, :] = np.bincount(sfa_words[j], minlength=feature_count)
        else:
            if remove_repeat_words:
                if 0 in relevant_features:
                    del relevant_features[0]

            for _, key in enumerate(sfa_words[j]):
                if key in relevant_features:
                    o = relevant_features[key]
                    all_win_words[j, o] += 1

    return all_win_words, all_win_words.shape[1]


@njit(fastmath=True, cache=True)
def create_dict(feature_names, features_idx):
    relevant_features = Dict.empty(key_type=types.uint32, value_type=types.uint32)
    for k, v in zip(
        feature_names[features_idx],
        np.arange(len(features_idx), dtype=np.uint32),
    ):
        relevant_features[k] = v

    return relevant_features


@njit(fastmath=True, cache=True)
def shorten_words(words, amount, letter_bits):
    new_words = np.zeros((words.shape[0], words.shape[1]), dtype=np.uint32)

    # Unigrams
    shift_len = amount * letter_bits
    for j in prange(words.shape[1]):
        # shorten a word by set amount of letters
        new_words[:, j] = words[:, j] >> shift_len

    # TODO Bigrams
    # if bigrams:
    #     for a in range(0, n_cases):
    #         first_word = new_words[:, a]
    #         second_word = new_words[:, a + window_size]
    #         words[:, n_cases + a] = (first_word << word_bits) | second_word

    return new_words


@njit(fastmath=True, cache=True, parallel=True)
def _transform_words_case(
    X,
    window_size,
    dft_length,
    norm,
    support,
    anova,
    variance,
    inverse_sqrt_win_size,
    lower_bounding,
    word_length,
    alphabet_size,
    breakpoints,
):
    dfts = _mft(
        X,
        window_size,
        dft_length,
        norm,
        support,
        anova,
        variance,
        inverse_sqrt_win_size,
        lower_bounding,
    )

    words = np.zeros((dfts.shape[0], dfts.shape[1], word_length), dtype=np.int32)

    for x in prange(dfts.shape[0]):
        for window in prange(dfts.shape[1]):
            for i in prange(word_length):
                for bp in range(alphabet_size):
                    if dfts[x, window, i] <= breakpoints[i][bp]:
                        words[x, window, i] = bp
                        break

    return words, dfts
