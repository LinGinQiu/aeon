"""TEASER early classifier.

An early classifier using a one class SVM's to determine decision safety with a
time series classifier.
"""

__maintainer__ = []
__all__ = ["TEASER"]

import copy

import numpy as np
from joblib import Parallel, delayed
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, cross_val_predict
from sklearn.svm import OneClassSVM
from sklearn.utils import check_random_state

from aeon.base._base import _clone_estimator
from aeon.classification.dictionary_based import MUSE, WEASEL
from aeon.classification.early_classification.base import BaseEarlyClassifier
from aeon.utils.validation import check_n_jobs


class TEASER(BaseEarlyClassifier):
    """
    Two-tier Early and Accurate Series Classifier (TEASER).

    An early classifier which uses one class SVM's trained on prediction probabilities
    to determine whether an early prediction is safe or not.

    Overview:
        Build n classifiers, where n is the number of classification_points.
        For each classifier, train a one class svm used to determine prediction safety
        at that series length.
        Tune the number of consecutive safe svm predictions required to consider the
        prediction safe.

        While a prediction is still deemed unsafe:
            Make a prediction using the series length at classification point i.
            Decide whether the predcition is safe or not using decide_prediction_safety.

    Parameters
    ----------
    estimator : aeon classifier, default=None
        An aeon estimator to be built at each of the classification_points time
        stamps. Defaults to a WEASEL classifier.
    one_class_classifier : one-class sklearn classifier, default=None
        An sklearn one-class classifier used to determine whether an early decision is
        safe. Defaults to a tuned one-class SVM classifier.
    one_class_param_grid : dict or list of dict, default=None
        The hyper-parameters for the one-class classifier to learn using grid-search.
        Dictionary with parameters names (`str`) as keys and lists of parameter settings
        to try as values, or a list of such dictionaries.
    classification_points : List or None, default=None
        List of integer time series time stamps to build classifiers and allow
        predictions at. Early predictions must have a series length that matches a value
        in the _classification_points List. Duplicate values will be removed, and the
        full series length will be appended if not present.
        If None, will use 20 thresholds linearly spaces from 0 to the series length.
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
    n_classes_ : int
        The number of classes.
    n_cases_ : int
        The number of train cases.
    n_channels_ : int
        The number of dimensions per case.
    n_timepoints_ : int
        The full length of each series.
    classes_ : list
        The unique class labels.
    state_info : 2d np.ndarray (4 columns)
        Information stored about input instances after the decision-making process in
        update/predict methods. Used in update methods to make decisions based on
        the results of previous method calls.
        Records in order: the time stamp index, the number of consecutive decisions
        made, the predicted class and the series length.

    References
    ----------
    .. [1] Schäfer, Patrick, and Ulf Leser. "TEASER: early and accurate time series
        classification." Data mining and knowledge discovery 34, no. 5 (2020)

    Examples
    --------
    >>> from aeon.classification.early_classification import TEASER
    >>> from aeon.classification.interval_based import TimeSeriesForestClassifier
    >>> from aeon.datasets import load_unit_test
    >>> X_train, y_train = load_unit_test(split="train")
    >>> X_test, y_test = load_unit_test(split="test")
    >>> clf = TEASER(
    ...     classification_points=[6, 16, 24],
    ...     estimator=TimeSeriesForestClassifier(n_estimators=5),
    ... )
    >>> clf.fit(X_train, y_train)
    TEASER(...)
    >>> y_pred, decisions = clf.predict(X_test)
    """

    _tags = {
        "capability:multivariate": True,
        "capability:multithreading": True,
    }

    def __init__(
        self,
        estimator=None,
        one_class_classifier=None,
        one_class_param_grid=None,
        classification_points=None,
        n_jobs=1,
        random_state=None,
    ):
        self.estimator = estimator
        self.one_class_classifier = one_class_classifier
        self.one_class_param_grid = one_class_param_grid
        self.classification_points = classification_points

        self.n_jobs = n_jobs
        self.random_state = random_state

        self._estimators = []
        self._one_class_classifiers = []
        self._classification_points = []
        self._consecutive_predictions = 0

        self.n_cases_ = 0
        self.n_channels_ = 0
        self.n_timepoints_ = 0

        self._svm_gammas = [100, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1.5, 1]
        self._svm_nu = 0.05
        self._svm_tol = 1e-4

        super().__init__()

    def _fit(self, X, y):
        self.n_cases_, self.n_channels_, self.n_timepoints_ = X.shape
        self._n_jobs = check_n_jobs(self.n_jobs)

        self._estimator = (
            (
                MUSE(support_probabilities=True, alphabet_size=4)
                if self.n_channels_ > 1
                else WEASEL(support_probabilities=True, alphabet_size=4)
            )
            if self.estimator is None
            else self.estimator
        )

        m = getattr(self._estimator, "predict_proba", None)
        if not callable(m):
            raise ValueError("Base estimator must have a predict_proba method.")

        self._classification_points = (
            copy.deepcopy(self.classification_points)
            if self.classification_points is not None
            else [round(self.n_timepoints_ / i) for i in range(1, 21)]
        )
        # remove duplicates
        self._classification_points = list(set(self._classification_points))
        self._classification_points.sort()
        # remove classification points that are less than 3 time stamps
        min_length = 8 if self.estimator is None else 3
        self._classification_points = [
            i for i in self._classification_points if i >= min_length
        ]
        # make sure the full series length is included
        if self._classification_points[-1] != self.n_timepoints_:
            self._classification_points.append(self.n_timepoints_)
        # create dictionary of classification point indices
        self._classification_point_dictionary = {}
        for index, classification_point in enumerate(self._classification_points):
            self._classification_point_dictionary[classification_point] = index

        # avoid nested parallelism
        m = getattr(self._estimator, "n_jobs", None)
        threads = self._n_jobs if m is None else 1

        rng = check_random_state(self.random_state)

        fit = Parallel(n_jobs=threads, prefer="threads")(
            delayed(self._fit_estimator)(
                X,
                y,
                i,
                check_random_state(rng.randint(np.iinfo(np.int32).max)),
            )
            for i in range(len(self._classification_points))
        )

        self._estimators, self._one_class_classifiers, X_oc, train_preds = zip(*fit)

        # tune consecutive predictions required to best harmonic mean
        best_hm = -1
        for g in range(2, min(6, len(self._classification_points))):
            state_info, _ = self._predict_oc_classifier_n_timestamps(
                train_preds,
                X_oc,
                g,
                0,
                len(self._classification_points),
            )

            # calculate harmonic mean from finished state info
            hm, acc, earl = self.compute_harmonic_mean(state_info, y)

            if hm > best_hm:
                best_hm = hm
                self._train_accuracy = acc
                self._train_earliness = earl
                self._consecutive_predictions = g

        return self

    def _predict(self, X) -> tuple[np.ndarray, np.ndarray]:
        out = self._predict_proba(X)
        return self._proba_output_to_preds(out)

    def _update_predict(self, X) -> tuple[np.ndarray, np.ndarray]:
        out = self._update_predict_proba(X)
        return self._proba_output_to_preds(out)

    def _predict_proba(self, X) -> tuple[np.ndarray, np.ndarray]:
        n_cases, _, n_timepoints = X.shape

        # maybe use the largest index that is smaller than the series length
        next_idx = self._get_next_idx(n_timepoints) + 1

        # if the input series length is invalid
        if next_idx == 0:
            raise ValueError(
                f"Input series length does not match the classification points produced"
                f" in fit. Input series length must be greater then the first point. "
                f"Current classification points: {self._classification_points}"
            )

        # avoid nested parallelism
        m = getattr(self._estimator, "n_jobs", None)
        threads = self._n_jobs if m is None else 1

        rng = check_random_state(self.random_state)

        # compute all new updates since then
        out = Parallel(n_jobs=threads, prefer="threads")(
            delayed(self._predict_proba_for_estimator)(
                X,
                i,
                check_random_state(rng.randint(np.iinfo(np.int32).max)),
            )
            for i in range(0, next_idx)
        )

        X_oc, probas, preds = zip(*out)
        new_state_info, accept_decision = self._predict_oc_classifier_n_timestamps(
            preds,
            X_oc,
            self._consecutive_predictions,
            0,
            next_idx,
        )

        probas = np.array(
            [
                (
                    probas[new_state_info[i][0]][i]
                    if accept_decision[i]
                    else [-1 for _ in range(self.n_classes_)]
                )
                for i in range(n_cases)
            ]
        )

        self.state_info = new_state_info

        return probas, accept_decision

    def _update_predict_proba(self, X) -> tuple[np.ndarray, np.ndarray]:
        n_cases, _, n_timepoints = X.shape

        # maybe use the largest index that is smaller than the series length
        next_idx = self._get_next_idx(n_timepoints) + 1

        # remove cases where a positive decision has been made
        state_info = self.state_info[
            self.state_info[:, 1] < self._consecutive_predictions
        ]

        # determine last index used
        last_idx = np.max(state_info[0][0]) + 1

        # if the input series length is invalid
        if next_idx == 0:
            raise ValueError(
                f"Input series length does not match the classification points produced"
                f" in fit. Input series length must be greater then the first point. "
                f"Current classification points: {self._classification_points}"
            )
        # check state info and X have the same length
        if len(X) > len(state_info):
            raise ValueError(
                f"Input number of instances does not match the length of recorded "
                f"state_info: {len(state_info)}. Cases with positive decisions "
                f"returned should be removed from the array with the row ordering "
                f"preserved, or the state information should be reset if new data is "
                f"used."
            )
        # check if series length has increased from last time
        elif last_idx >= next_idx:
            raise ValueError(
                f"All input instances must be from a larger classification point time "
                f"stamp than the recorded state information. Required series length "
                f"for current state information: "
                f">={self._classification_points[last_idx]}"
            )

        # avoid nested parallelism
        m = getattr(self._estimator, "n_jobs", None)
        threads = self._n_jobs if m is None else 1

        rng = check_random_state(self.random_state)

        # compute all new updates since then
        out = Parallel(n_jobs=threads, prefer="threads")(
            delayed(self._predict_proba_for_estimator)(
                X,
                i,
                check_random_state(rng.randint(np.iinfo(np.int32).max)),
            )
            for i in range(last_idx, next_idx)
        )

        X_oc, probas, preds = zip(*out)
        new_state_info, accept_decision = self._predict_oc_classifier_n_timestamps(
            preds,
            X_oc,
            self._consecutive_predictions,
            last_idx,
            next_idx,
            state_info=state_info,
        )

        probas = np.array(
            [
                (
                    probas[max(0, new_state_info[i][0] - last_idx)][i]
                    if accept_decision[i]
                    else [-1 for _ in range(self.n_classes_)]
                )
                for i in range(n_cases)
            ]
        )

        self.state_info = new_state_info

        return probas, accept_decision

    def _score(self, X, y) -> tuple[float, float, float]:
        self._predict(X)
        hm, acc, earl = self.compute_harmonic_mean(self.state_info, y)

        return hm, acc, earl

    def _get_next_idx(self, n_timepoints):
        """Return the largest index smaller than the series length."""
        next_idx = -1
        for idx, offset in enumerate(np.sort(self._classification_points)):
            if offset <= n_timepoints:
                next_idx = idx
        return next_idx

    def _fit_estimator(self, X, y, i, rng):
        estimator = _clone_estimator(
            self._estimator,
            rng,
        )

        m = getattr(estimator, "n_jobs", None)
        if m is not None:
            estimator.n_jobs = self._n_jobs

        # fit estimator for this threshold
        estimator.fit(X[:, :, : self._classification_points[i]], y)

        # get train set probability estimates for this estimator
        if callable(getattr(estimator, "_get_train_probs", None)) and (
            getattr(estimator, "_save_transformed_data", False)
            or getattr(estimator, "_save_train_predictions", False)
        ):
            train_probas = estimator._get_train_probs(X, y)
        else:
            cv_size = 5
            _, counts = np.unique(y, return_counts=True)
            min_class = np.min(counts)
            if min_class < cv_size:
                cv_size = min_class

            train_probas = cross_val_predict(
                estimator, X, y=y, cv=cv_size, method="predict_proba"
            )

        train_preds = [
            int(rng.choice(np.flatnonzero(prob == prob.max()))) for prob in train_probas
        ]

        # create train set for the one class classifier using train probas with the
        # minimum difference to the predicted probability
        train_probas = self._generate_one_class_features(X, train_preds, train_probas)
        X_oc = []
        for i in range(len(X)):
            if train_preds[i] == self._class_dictionary[y[i]]:
                X_oc.append(train_probas[i])

        # fit one class classifier and grid search parameters if a grid is provided
        one_class_classifier = None
        if len(X_oc) > 1:
            one_class_classifier = (
                OneClassSVM(tol=self._svm_tol, nu=self._svm_nu)
                if self.one_class_classifier is None
                else _clone_estimator(self.one_class_classifier, random_state=rng)
            )
            param_grid = (
                {"gamma": self._svm_gammas}
                if self.one_class_classifier is None
                and self.one_class_param_grid is None
                else self.one_class_param_grid
            )

            cv_size = min(len(X_oc), 10)
            gs = GridSearchCV(
                estimator=one_class_classifier,
                param_grid=param_grid,
                scoring="accuracy",
                cv=cv_size,
            )
            gs.fit(X_oc, np.ones(len(X_oc)))
            one_class_classifier = gs.best_estimator_

        return estimator, one_class_classifier, train_probas, train_preds

    def _predict_proba_for_estimator(self, X, i, rng):
        probas = self._estimators[i].predict_proba(
            X[:, :, : self._classification_points[i]]
        )
        preds = np.array(
            [int(rng.choice(np.flatnonzero(prob == prob.max()))) for prob in probas]
        )

        # create data set for the one class classifier using predicted probas with the
        # minimum difference to the predicted probability
        X_oc = self._generate_one_class_features(X, preds, probas)

        return X_oc, probas, preds

    def _generate_one_class_features(self, X, preds, probas):
        # create data set for the one class classifier using predicted probas with the
        # minimum difference to the predicted probability
        X_oc = np.hstack((probas, np.ones((len(X), 1))))
        for i in range(len(X)):
            for n in range(self.n_classes_):
                if n != preds[i]:
                    X_oc[i][self.n_classes_] = min(
                        X_oc[i][self.n_classes_], X_oc[i][preds[i]] - X_oc[i][n]
                    )
        return X_oc

    def _predict_oc_classifier_n_timestamps(
        self,
        estimator_preds,
        X_oc,
        n_consecutive_predictions,
        last_idx,
        next_idx,
        state_info=None,
    ):
        # a List containing the state info for case, edited at each time stamp.
        # contains 1. the index of the time stamp, 2. the number of consecutive
        # positive decisions made, and 3. the prediction made
        if state_info is None:
            state_info = np.zeros((len(estimator_preds[0]), 4), dtype=int)

        # only compute new indices
        for i in range(last_idx, next_idx):
            finished, state_info = self._predict_oc_classifier(
                X_oc[i - last_idx],
                n_consecutive_predictions,
                i,
                estimator_preds[i - last_idx],
                state_info,
            )

        return state_info, finished

    def _predict_oc_classifier(
        self, X_oc, n_consecutive_predictions, idx, estimator_preds, state_info
    ):
        # stores whether we have made a final decision on a prediction, if true
        # state info won't be edited in later time stamps
        finished = state_info[:, 1] >= n_consecutive_predictions
        n_cases = len(X_oc)

        full_length_ts = idx == len(self._classification_points) - 1
        if full_length_ts:
            accept_decision = np.ones(n_cases, dtype=bool)
        elif self._one_class_classifiers[idx] is not None:
            offsets = np.argwhere(finished == 0).flatten()
            accept_decision = np.ones(n_cases, dtype=bool)
            if len(offsets) > 0:
                decisions_subset = (
                    self._one_class_classifiers[idx].predict(X_oc[offsets]) == 1
                )
                accept_decision[offsets] = decisions_subset

        else:
            accept_decision = np.zeros(n_cases, dtype=bool)

        # record consecutive class decisions
        state_info = np.array(
            [
                (
                    self._update_state_info(
                        accept_decision, estimator_preds, state_info, i, idx
                    )
                    if not finished[i]
                    else state_info[i]
                )
                for i in range(n_cases)
            ]
        )

        # check safety of decisions
        if full_length_ts:
            # Force prediction at last time stamp
            accept_decision = np.ones(n_cases, dtype=bool)
        else:
            accept_decision = state_info[:, 1] >= n_consecutive_predictions

        return accept_decision, state_info

    def _update_state_info(self, accept_decision, preds, state_info, idx, time_stamp):
        # consecutive predictions, add one if positive decision and same class
        if accept_decision[idx] and preds[idx] == state_info[idx][2]:
            return (
                time_stamp,
                state_info[idx][1] + 1,
                preds[idx],
                self._classification_points[time_stamp],
            )
        # set to 0 if the decision is negative, 1 if its positive but different class
        else:
            return (
                time_stamp,
                1 if accept_decision[idx] else 0,
                preds[idx],
                self._classification_points[time_stamp],
            )

    def _proba_output_to_preds(self, out):
        rng = check_random_state(self.random_state)
        preds = np.array(
            [
                (
                    self.classes_[
                        int(rng.choice(np.flatnonzero(out[0][i] == out[0][i].max())))
                    ]
                    if out[1][i]
                    else -1
                )
                for i in range(len(out[0]))
            ]
        )
        return preds, out[1]

    def compute_harmonic_mean(self, state_info, y) -> tuple[float, float, float]:
        """Calculate harmonic mean from a state info matrix and array of class labeles.

        Parameters
        ----------
        state_info : 2d np.ndarray of int
            The state_info from a TEASER object after a prediction or update. It is
            assumed the state_info is complete, and a positive decision has been
            returned for all cases.
        y : 1D np.array of int
            Actual class labels for predictions. indices correspond to instance indices
            in state_info.

        Returns
        -------
        harmonic_mean : float
            Harmonic Mean represents the balance between accuracy and earliness for a
            set of early predictions.
        accuracy : float
            Accuracy for the predictions made in the state_info.
        earliness : float
            Average time taken to make a classification. The earliness for a single case
            is the number of time points required divided by the total series length.
        """
        accuracy = np.average(
            [
                state_info[i][2] == self._class_dictionary[y[i]]
                for i in range(len(state_info))
            ]
        )
        earliness = np.average(
            [
                self._classification_points[state_info[i][0]] / self.n_timepoints_
                for i in range(len(state_info))
            ]
        )
        return (
            (2 * accuracy * (1 - earliness)) / (accuracy + (1 - earliness)),
            accuracy,
            earliness,
        )

    @classmethod
    def _get_test_params(cls, parameter_set="default"):
        """Return testing parameter settings for the estimator.

        Parameters
        ----------
        parameter_set : str, default="default"
            Name of the set of test parameters to return, for use in tests. If no
            special parameters are defined for a value, will return `"default"` set.
            TEASER provides the following special sets:
                 "results_comparison" - used in some classifiers to compare against
                    previously generated results where the default set of parameters
                    cannot produce suitable probability estimates

        Returns
        -------
        params : dict or list of dict, default={}
            Parameters to create testing instances of the class.
            Each dict are parameters to construct an "interesting" test instance, i.e.,
            `MyClass(**params)` or `MyClass(**params[i])` creates a valid test instance.
        """
        from aeon.classification.feature_based import SummaryClassifier
        from aeon.classification.interval_based import TimeSeriesForestClassifier

        if parameter_set == "results_comparison":
            return {
                "classification_points": [6, 10, 16, 24],
                "estimator": TimeSeriesForestClassifier(n_estimators=10),
            }
        else:
            return {
                "classification_points": [3, 5],
                "estimator": SummaryClassifier(
                    estimator=RandomForestClassifier(n_estimators=2)
                ),
            }
