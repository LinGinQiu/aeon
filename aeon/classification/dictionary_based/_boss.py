"""BOSS classifiers.

Dictionary based BOSS classifiers based on SFA transform.
Contains a single BOSS and a BOSS ensemble.
"""

__maintainer__ = []
__all__ = ["BOSSEnsemble", "IndividualBOSS", "pairwise_distances"]

from itertools import compress

import numpy as np
from joblib import Parallel, effective_n_jobs
from sklearn.metrics import pairwise
from sklearn.utils import check_random_state, gen_even_slices
from sklearn.utils.extmath import safe_sparse_dot
from sklearn.utils.parallel import delayed
from sklearn.utils.sparsefuncs_fast import csr_row_norms
from sklearn.utils.validation import _num_samples

from aeon.classification.base import BaseClassifier
from aeon.transformations.collection.dictionary_based import SFAFast
from aeon.utils.validation import check_n_jobs


class BOSSEnsemble(BaseClassifier):
    """
    Ensemble of Bag of Symbolic Fourier Approximation Symbols (BOSS).

    Implementation of BOSS Ensemble from [1]_.

    Overview: Input *n* series of length *m* and BOSS performs a grid search over
    a set of parameter values, evaluating each with a LOOCV. It then retains
    all ensemble members within 92% of the best by default for use in the ensemble.
    There are three primary parameters:
       - *alpha*: alphabet size
       - *w*: window length
       - *l*: word length.
    For any combination, a single BOSS slides a window length *w* along the
    series. The w length window is shortened to an *l* length word through
    taking a Fourier transform and keeping the first *l/2* complex coefficients.
    These *l* coefficients are then discretized into alpha possible values,
    to form a word length *l*. A histogram of words for each
    series is formed and stored.
    Fit involves finding "n" histograms.

    Predict uses 1 nearest neighbor with a bespoke BOSS distance function.

    Parameters
    ----------
    threshold : float, default=0.92
        Threshold used to determine which classifiers to retain. All classifiers
        within percentage `threshold` of the best one are retained.
    max_ensemble_size : int or None, default=500
        Maximum number of classifiers to retain. Will limit number of retained
        classifiers even if more than `max_ensemble_size` are within threshold.
    max_win_len_prop : int or float, default=1
        Maximum window length as a proportion of the series length.
    min_window : int, default=10
        Minimum window size.
    feature_selection : str, default: "none"
        Sets the feature selections strategy to be usedfrom  {"chi2", "none",
        "random"}. Chi2 reduces the number of words significantly and is thus much
        faster (preferred). Random also reduces the number significantly. None
        applies not feature selection and yields large bag of words, e.g. much memory
        may be needed.
    alphabet_size : default = 4
        Number of possible letters (values) for each word.
    use_boss_distance : bool, default=True
        The Boss-distance is an asymmetric distance measure. It provides higher
        accuracy, yet is signifaicantly slower to compute.
    n_jobs : int, default=1
        The number of jobs to run in parallel for both `fit` and `predict`.
        ``-1`` means using all processors.
    random_state : int, RandomState instance or None, default=None
        If `int`, random_state is the seed used by the random number generator;
        If `RandomState` instance, random_state is the random number generator;
        If `None`, the random number generator is the `RandomState` instance used
        by `np.random`.

    Attributes
    ----------
    n_cases_ : int
        Number of train instances in data passed to fit.
    n_timepoints_ : int
        Length of all series (assumed equal).
    n_estimators_ : int
        The final number of classifiers used. Will be <= `max_ensemble_size` if
        `max_ensemble_size` has been specified.
    estimators_ : list
       List of DecisionTree classifiers size n_estimators_.

    See Also
    --------
    IndividualBOSS, ContractableBOSS
        Variants of the single BOSS classifier.

    Notes
    -----
    For the Java version, see
    - `Original Publication <https://github.com/patrickzib/SFA>`_.
    - `TSML <https://github.com/uea-machine-learning/tsml/blob/master/src/main/java/
    tsml/classifiers/dictionary_based/BOSS.java>`_.

    References
    ----------
    .. [1] Patrick Schäfer, "The BOSS is concerned with time series classification
       in the presence of noise", Data Mining and Knowledge Discovery, 29(6): 2015
       https://link.springer.com/article/10.1007/s10618-014-0377-7

    Examples
    --------
    >>> from aeon.classification.dictionary_based import BOSSEnsemble
    >>> from aeon.datasets import load_unit_test
    >>> X_train, y_train = load_unit_test(split="train")
    >>> X_test, y_test = load_unit_test(split="test")
    >>> clf = BOSSEnsemble(max_ensemble_size=3)
    >>> clf.fit(X_train, y_train)
    BOSSEnsemble(...)
    >>> y_pred = clf.predict(X_test)
    """

    _tags = {
        "capability:train_estimate": True,
        "capability:multithreading": True,
        "algorithm_type": "dictionary",
    }

    def __init__(
        self,
        threshold=0.92,
        max_ensemble_size=500,
        max_win_len_prop=1,
        min_window=10,
        feature_selection="none",
        use_boss_distance=True,
        alphabet_size=4,
        n_jobs=1,
        random_state=None,
    ):
        self.threshold = threshold
        self.max_ensemble_size = max_ensemble_size
        self.max_win_len_prop = max_win_len_prop
        self.min_window = min_window
        self.n_jobs = n_jobs
        self.random_state = random_state
        self.use_boss_distance = use_boss_distance

        self.estimators_ = []
        self.n_estimators_ = 0
        self.n_timepoints_ = 0
        self.n_cases_ = 0
        self.feature_selection = feature_selection

        self._word_lengths = [16, 14, 12, 10, 8]
        self._norm_options = [True, False]
        self.alphabet_size = alphabet_size

        super().__init__()

    def _fit(self, X, y, keep_train_preds=False):
        """Fit a boss ensemble on cases (X,y), where y is the target variable.

        Build an ensemble of BOSS classifiers from the training set (X,
        y), through  creating a variable size ensemble of those within a
        threshold of the best.

        Parameters
        ----------
        X : 3D np.ndarray
            The training data shape = (n_cases, n_channels, n_timepoints).
        y : 1D np.ndarray
            The training labels, shape = (n_cases).

        Returns
        -------
        self :
            Reference to self.

        Notes
        -----
        Changes state by creating a fitted model that updates attributes
        ending in "_" and sets is_fitted flag to True.
        """
        self.n_cases_, _, self.n_timepoints_ = X.shape
        self._n_jobs = check_n_jobs(self.n_jobs)

        self.estimators_ = []

        # Window length parameter space dependent on series length
        max_window_searches = self.n_timepoints_ / 4
        max_window = int(self.n_timepoints_ * self.max_win_len_prop)
        win_inc = max(1, int((max_window - self.min_window) / max_window_searches))

        if self.min_window > max_window + 1:
            raise ValueError(
                f"Error in BOSSEnsemble, min_window ="
                f"{self.min_window} is bigger"
                f" than max_window ={max_window}."
                f" Try set min_window to be smaller than series length in "
                f"the constructor, but the classifier may not work at "
                f"all with very short series"
            )

        max_acc = -1
        min_max_acc = -1
        for normalise in self._norm_options:
            for win_size in range(self.min_window, max_window + 1, win_inc):
                # max_word_len = min(self.min_window - 2, self.word_lengths[0])
                boss = IndividualBOSS(
                    win_size,
                    self._word_lengths[0],
                    normalise,
                    self.alphabet_size,
                    save_words=True,
                    use_boss_distance=self.use_boss_distance,
                    feature_selection=self.feature_selection,
                    n_jobs=self._n_jobs,
                    random_state=self.random_state,
                )
                boss.fit(X, y)

                best_classifier_for_win_size = boss
                best_acc_for_win_size = -1

                # the used word length may be shorter
                best_word_len = boss._transformer.word_length

                for n, word_len in enumerate(self._word_lengths):
                    if n > 0 and word_len < boss._transformer.word_length:
                        boss = boss._shorten_bags(word_len, y)

                    boss._accuracy = self._individual_train_acc(
                        boss,
                        y,
                        self.n_cases_,
                        best_acc_for_win_size,
                        keep_train_preds,
                    )

                    if boss._accuracy >= best_acc_for_win_size:
                        best_acc_for_win_size = boss._accuracy
                        best_classifier_for_win_size = boss
                        best_word_len = word_len

                if self._include_in_ensemble(
                    best_acc_for_win_size,
                    max_acc,
                    min_max_acc,
                    len(self.estimators_),
                ):
                    best_classifier_for_win_size._clean()
                    best_classifier_for_win_size._set_word_len(X, y, best_word_len)
                    self.estimators_.append(best_classifier_for_win_size)

                    if best_acc_for_win_size > max_acc:
                        max_acc = best_acc_for_win_size
                        self.estimators_ = list(
                            compress(
                                self.estimators_,
                                [
                                    classifier._accuracy >= max_acc * self.threshold
                                    for classifier in self.estimators_
                                ],
                            )
                        )

                    min_max_acc, min_acc_ind = self._worst_ensemble_acc()

                    if (
                        len(self.estimators_) > self.max_ensemble_size
                        and min_acc_ind > -1
                    ):
                        del self.estimators_[min_acc_ind]
                        min_max_acc, min_acc_ind = self._worst_ensemble_acc()

        self.n_estimators_ = len(self.estimators_)

        return self

    def _predict(self, X) -> np.ndarray:
        """Predict class values of n instances in X.

        Parameters
        ----------
        X : 3D np.ndarray
            The data to make predictions for, shape = (n_cases, n_channels,
            n_timepoints).

        Returns
        -------
        y : 1D np.ndarray
            The predicted class labels, shape = (n_cases).
        """
        rng = check_random_state(self.random_state)
        return np.array(
            [
                self.classes_[int(rng.choice(np.flatnonzero(prob == prob.max())))]
                for prob in self.predict_proba(X)
            ]
        )

    def _predict_proba(self, X) -> np.ndarray:
        """Predict class probabilities for n instances in X.

        Parameters
        ----------
        X : 3D np.ndarray
            The data to make predictions for, shape = (n_cases, n_channels,
            n_timepoints).

        Returns
        -------
        y : 2D np.ndarray
            Predicted probabilities using the ordering in classes_ shape = (
            n_cases, n_classes_).
        """
        sums = np.zeros((X.shape[0], self.n_classes_))

        for clf in self.estimators_:
            preds = clf.predict(X)
            for i in range(X.shape[0]):
                sums[i, self._class_dictionary[preds[i]]] += 1
        return sums / (np.ones(self.n_classes_) * self.n_estimators_)

    def _fit_predict(self, X, y) -> np.ndarray:
        rng = check_random_state(self.random_state)
        return np.array(
            [
                self.classes_[int(rng.choice(np.flatnonzero(prob == prob.max())))]
                for prob in self._fit_predict_proba(X, y)
            ]
        )

    def _fit_predict_proba(self, X, y) -> np.ndarray:
        self._fit(X, y, keep_train_preds=True)

        results = np.zeros((self.n_cases_, self.n_classes_))
        divisors = np.zeros(self.n_cases_)

        for clf in self.estimators_:
            preds = clf._train_predictions
            for n, pred in enumerate(preds):
                results[n][self._class_dictionary[pred]] += 1
                divisors[n] += 1

        for i in range(self.n_cases_):
            results[i] = (
                np.ones(self.n_classes_) * (1 / self.n_classes_)
                if divisors[i] == 0
                else results[i] / (np.ones(self.n_classes_) * divisors[i])
            )

        return results

    def _include_in_ensemble(self, acc, max_acc, min_max_acc, size):
        if acc >= max_acc * self.threshold:
            if size >= self.max_ensemble_size:
                return acc > min_max_acc
            else:
                return True
        return False

    def _worst_ensemble_acc(self):
        min_acc = 1.0
        min_acc_idx = -1

        for c, classifier in enumerate(self.estimators_):
            if classifier._accuracy < min_acc:
                min_acc = classifier._accuracy
                min_acc_idx = c

        return min_acc, min_acc_idx

    def _individual_train_acc(self, boss, y, train_size, lowest_acc, keep_train_preds):
        correct = 0
        required_correct = int(lowest_acc * train_size)

        # there may be no words if feature selection is too aggressive
        if boss._transformed_data.shape[1] > 0:
            distance_matrix = pairwise_distances(
                boss._transformed_data,
                use_boss_distance=self.use_boss_distance,
                n_jobs=self.n_jobs,
            )

            for i in range(train_size):
                if correct + train_size - i < required_correct:
                    return -1

                c = boss._train_predict(i, distance_matrix)
                if c == y[i]:
                    correct += 1

                if keep_train_preds:
                    boss._train_predictions.append(c)

        return correct / train_size

    @classmethod
    def _get_test_params(cls, parameter_set="default"):
        """Return testing parameter settings for the estimator.

        Parameters
        ----------
        parameter_set : str, default="default"
            Name of the set of test parameters to return, for use in tests. If no
            special parameters are defined for a value, will return `"default"` set.
            BOSSEnsemble provides the following special sets:
                 "results_comparison" - used in some classifiers to compare against
                    previously generated results where the default set of parameters
                    cannot produce suitable probability estimates
                "train_estimate" - used in some classifiers that set the
                    "capability:train_estimate" tag to True to allow for more efficient
                    testing when relevant parameters are available

        Returns
        -------
        params : dict or list of dict, default={}
            Parameters to create testing instances of the class.
            Each dict are parameters to construct an "interesting" test instance, i.e.,
            `MyClass(**params)` or `MyClass(**params[i])` creates a valid test instance.
        """
        if parameter_set == "results_comparison":
            return {
                "max_ensemble_size": 5,
                "feature_selection": "none",
                "use_boss_distance": False,
                "alphabet_size": 4,
            }
        else:
            return {
                "max_ensemble_size": 2,
                "feature_selection": "none",
                "use_boss_distance": False,
            }


class IndividualBOSS(BaseClassifier):
    """
    Single bag of Symbolic Fourier Approximation Symbols (IndividualBOSS).

    Bag of SFA Symbols Ensemble: implementation of a single BOSS Schaffer, the base
    classifier for the boss ensemble.

    Implementation of single BOSS model from Schäfer (2015). [1]_

    This is the underlying classifier for each classifier in the BOSS ensemble.

    Overview: input "n" series of length "m" and IndividualBoss performs a SFA
    transform to form a sparse dictionary of discretised words. The resulting
    dictionary is used with the BOSS distance function in a 1-nearest neighbor.

    Fit involves finding "n" histograms.

    Predict uses 1 nearest neighbor with a bespoke BOSS distance function.

    Parameters
    ----------
    window_size : int
        Size of the window to use in BOSS algorithm.
    word_length : int
        Length of word to use to use in BOSS algorithm.
    norm : bool, default = False
        Whether to normalize words by dropping the first Fourier coefficient.
    alphabet_size : default = 4
        Number of possible letters (values) for each word.
    save_words : bool, default = True
        Whether to keep NumPy array of words in SFA transformation even after
        the dictionary of words is returned. If True, the array is saved, which
        can shorten the time to calculate dictionaries using a shorter
        `word_length` (since the last "n" letters can be removed).
    feature_selection : str, default: "none"
        Sets the feature selections strategy to be usedfrom  {"chi2", "none",
        "random"}. Chi2 reduces the number of words significantly and is thus much
        faster (preferred). Random also reduces the number significantly. None
        applies not feature selection and yields large bag of words, e.g. much memory
        may be needed.
    alphabet_size : default = 4
        Number of possible letters (values) for each word.
    use_boss_distance : bool, default=True
         The Boss-distance is an asymmetric distance measure. It provides higher
         accuracy, yet is signifaicantly slower to compute.
    n_jobs : int, default=1
         The number of jobs to run in parallel for both `fit` and `predict`.
         ``-1`` means using all processors.
    random_state : int or None, default=None
        Seed for random, integer.

    Attributes
    ----------
    n_classes_ : int
        Number of classes. Extracted from the data.
    classes_ : list
        The classes labels.

    See Also
    --------
    BOSSEnsemble, ContractableBOSS
        Variants on the BOSS classifier.

    Notes
    -----
    For the Java version, see
    `TSML <https://github.com/uea-machine-learning/tsml/blob/master/src/main/java/
    tsml/classifiers/dictionary_based/IndividualBOSS.java>`_.

    References
    ----------
    .. [1] Patrick Schäfer, "The BOSS is concerned with time series classification
       in the presence of noise", Data Mining and Knowledge Discovery, 29(6): 2015
       https://link.springer.com/article/10.1007/s10618-014-0377-7

    Examples
    --------
    >>> from aeon.classification.dictionary_based import IndividualBOSS
    >>> from aeon.datasets import load_unit_test
    >>> X_train, y_train = load_unit_test(split="train")
    >>> X_test, y_test = load_unit_test(split="test")
    >>> clf = IndividualBOSS()
    >>> clf.fit(X_train, y_train)
    IndividualBOSS(...)
    >>> y_pred = clf.predict(X_test)
    """

    _tags = {
        "capability:multithreading": True,
    }

    def __init__(
        self,
        window_size=10,
        word_length=8,
        norm=False,
        alphabet_size=4,
        save_words=False,
        use_boss_distance=True,
        feature_selection="none",
        n_jobs=1,
        random_state=None,
    ):
        self.window_size = window_size
        self.word_length = word_length
        self.norm = norm
        self.alphabet_size = alphabet_size
        self.feature_selection = feature_selection
        self.use_boss_distance = use_boss_distance

        self.save_words = save_words
        self.n_jobs = n_jobs
        self.random_state = random_state

        self._transformer = None
        self._transformed_data = []
        self._class_vals = []
        self._accuracy = 0
        self._subsample = []
        self._train_predictions = []

        super().__init__()

    def _fit(self, X, y):
        """Fit a single boss classifier on n_cases cases (X,y).

        Parameters
        ----------
        X : 3D np.ndarray of shape = [n_cases, n_channels, n_timepoints]
            The training data.
        y : array-like, shape = [n_cases]
            The class labels.

        Returns
        -------
        self :
            Reference to self.

        Notes
        -----
        Changes state by creating a fitted model that updates attributes
        ending in "_" and sets is_fitted flag to True.
        """
        self._n_jobs = check_n_jobs(self.n_jobs)
        self._transformer = SFAFast(
            word_length=self.word_length,
            alphabet_size=self.alphabet_size,
            window_size=self.window_size,
            norm=self.norm,
            bigrams=False,
            remove_repeat_words=True,
            save_words=self.save_words,
            n_jobs=self._n_jobs,
            feature_selection=self.feature_selection,
            random_state=self.random_state,
        )

        self._transformed_data = self._transformer.fit_transform(X, y)
        self._class_vals = y

        return self

    def _predict(self, X):
        """Predict class values of all instances in X.

        Parameters
        ----------
        X : 3D np.ndarray of shape = [n_cases, n_channels, n_timepoints]
            The data to make predictions for.

        Returns
        -------
        y : array-like, shape = [n_cases]
            Predicted class labels.
        """
        test_bags = self._transformer.transform(X)
        data_type = type(self._class_vals[0])
        if data_type in [np.str_, str]:
            data_type = "object"

        classes = np.zeros(test_bags.shape[0], dtype=data_type)

        if self._transformed_data.shape[1] > 0:
            distance_matrix = pairwise_distances(
                test_bags,
                self._transformed_data,
                use_boss_distance=self.use_boss_distance,
                n_jobs=self.n_jobs,
            )

            for i in range(test_bags.shape[0]):
                min_pos = np.argmin(distance_matrix[i])
                classes[i] = self._class_vals[min_pos]
        else:
            # set to most frequent element
            counts = np.bincount(self._class_vals)
            classes[:] = np.argmax(counts)

        return classes

    def _train_predict(self, train_num, distance_matrix):
        distance_vector = distance_matrix[train_num]
        min_pos = np.argmin(distance_vector)
        return self._class_vals[min_pos]

    def _shorten_bags(self, word_len, y):
        new_boss = IndividualBOSS(
            self.window_size,
            word_len,
            self.norm,
            self.alphabet_size,
            save_words=self.save_words,
            use_boss_distance=self.use_boss_distance,
            feature_selection=self.feature_selection,
            n_jobs=self.n_jobs,
            random_state=self.random_state,
        )
        new_boss._transformer = self._transformer
        new_bag = new_boss._transformer._shorten_bags(word_len, y)
        new_boss._transformed_data = new_bag
        new_boss._class_vals = self._class_vals
        new_boss.n_classes_ = self.n_classes_
        new_boss.classes_ = self.classes_
        new_boss._class_dictionary = self._class_dictionary
        new_boss.metadata_ = self.metadata_
        new_boss.is_fitted = True

        return new_boss

    def _clean(self):
        if self._transformer is None:
            return
        self._transformer.words = None
        self._transformer.save_words = False

    def _set_word_len(self, X, y, word_len):
        self.word_length = word_len

        # we have to retrain feature selection for now
        # might be optimized by remembering feature_dicts
        self._transformer.word_length = min(self._transformer.word_length, word_len)
        self._transformed_data = self._transformer.fit_transform(X, y)


def _dist_wrapper(dist_matrix, X, Y, s, XX_all=None, XY_all=None):
    """Write in-place to a slice of a distance matrix."""
    for i in range(s.start, s.stop):
        dist_matrix[i] = boss_distance(X, Y, i, XX_all, XY_all)


def pairwise_distances(X, Y=None, use_boss_distance=False, n_jobs=1):
    """Find the euclidean distance between all pairs of bop-models."""
    if use_boss_distance:
        if Y is None:
            Y = X

        XX_row_norms = csr_row_norms(X)
        XY = safe_sparse_dot(X, Y.T, dense_output=True)

        distance_matrix = np.zeros((X.shape[0], Y.shape[0]))

        if effective_n_jobs(n_jobs) > 1:
            Parallel(n_jobs=n_jobs, prefer="threads")(
                delayed(_dist_wrapper)(distance_matrix, X, Y, s, XX_row_norms, XY)
                for s in gen_even_slices(_num_samples(X), effective_n_jobs(n_jobs))
            )
        else:
            for i in range(len(distance_matrix)):
                distance_matrix[i] = boss_distance(X, Y, i, XX_row_norms, XY)

    else:
        distance_matrix = pairwise.pairwise_distances(X, Y, n_jobs=n_jobs)

    if X is Y or Y is None:
        np.fill_diagonal(distance_matrix, np.inf)

    return distance_matrix


def boss_distance(X, Y, i, XX_all=None, XY_all=None):
    """Find the distance between two histograms.

    This returns the distance between first and second dictionaries, using a non-
    symmetric distance measure. It is used to find the distance between histograms
    of words.

    This distance function is designed for sparse matrix, represented as either a
    dictionary or an array. It only measures the distance between counts present in
    the first dictionary and the second. Hence dist(a,b) does not necessarily equal
    dist(b,a).

    Parameters
    ----------
    X : sparse matrix
        Base dictionary used in distance measurement.
    Y : sparse matrix
        Second dictionary that will be used to measure distance from `first`.
    i : int
        index of current element

    Returns
    -------
    dist : float
        The boss distance between the first and second dictionaries.
    """
    mask = X[i].nonzero()[1]
    if XX_all is None:
        XX = csr_row_norms(X[i])
    else:
        XX = XX_all[i]
    if XY_all is None:
        XY = safe_sparse_dot(X[i], Y.T, dense_output=True)
    else:
        XY = XY_all[i]

    YY = csr_row_norms(Y[:, mask])
    A = XX - 2 * XY + YY
    np.maximum(A, 0, out=A)
    return A
