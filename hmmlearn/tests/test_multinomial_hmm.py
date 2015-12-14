from __future__ import absolute_import

import numpy as np
import pytest

from hmmlearn import hmm
from hmmlearn.utils import normalize

from ._test_common import fit_hmm_and_monitor_log_likelihood


class TestMultinomialHMM(object):
    """Using examples from Wikipedia

    - http://en.wikipedia.org/wiki/Hidden_Markov_model
    - http://en.wikipedia.org/wiki/Viterbi_algorithm
    """
    def setup_method(self, method):
        self.prng = np.random.RandomState(9)
        self.n_components = 2   # ('Rainy', 'Sunny')
        self.n_features = 3      # ('walk', 'shop', 'clean')
        self.emissionprob = np.array([[0.1, 0.4, 0.5], [0.6, 0.3, 0.1]])
        self.startprob = np.array([0.6, 0.4])
        self.transmat = np.array([[0.7, 0.3], [0.4, 0.6]])

        self.h = hmm.MultinomialHMM(self.n_components)
        self.h.startprob_ = self.startprob
        self.h.transmat_ = self.transmat
        self.h.emissionprob_ = self.emissionprob

    def test_set_emissionprob(self):
        h = hmm.MultinomialHMM(self.n_components)
        emissionprob = np.array([[0.8, 0.2, 0.0], [0.7, 0.2, 1.0]])
        h.emissionprob = emissionprob
        assert np.allclose(emissionprob, h.emissionprob)

    def test_wikipedia_viterbi_example(self):
        # From http://en.wikipedia.org/wiki/Viterbi_algorithm:
        # "This reveals that the observations ['walk', 'shop', 'clean']
        # were most likely generated by states ['Sunny', 'Rainy',
        # 'Rainy'], with probability 0.01344."
        X = [[0], [1], [2]]
        logprob, state_sequence = self.h.decode(X)
        assert round(np.exp(logprob), 5) == 0.01344
        assert np.allclose(state_sequence, [1, 0, 0])

    def test_decode_map_algorithm(self):
        X = [[0], [1], [2]]
        h = hmm.MultinomialHMM(self.n_components, algorithm="map")
        h.startprob_ = self.startprob
        h.transmat_ = self.transmat
        h.emissionprob_ = self.emissionprob
        _logprob, state_sequence = h.decode(X)
        assert np.allclose(state_sequence, [1, 0, 0])

    def test_predict(self):
        X = [[0], [1], [2]]
        state_sequence = self.h.predict(X)
        posteriors = self.h.predict_proba(X)
        assert np.allclose(state_sequence, [1, 0, 0])
        assert np.allclose(posteriors, [
            [0.23170303, 0.76829697],
            [0.62406281, 0.37593719],
            [0.86397706, 0.13602294],
        ])

    def test_attributes(self):
        h = hmm.MultinomialHMM(self.n_components)
        h.startprob_ = self.startprob
        h.transmat_ = self.transmat

        with pytest.raises(ValueError):
            h.emissionprob_ = []
            h._check()
        with pytest.raises(ValueError):
            h.emissionprob_ = np.zeros((self.n_components - 2,
                                        self.n_features))
            h._check()

    def test_score_samples(self):
        idx = np.repeat(np.arange(self.n_components), 10)
        n_samples = len(idx)
        X = np.atleast_2d(
            (self.prng.rand(n_samples) * self.n_features).astype(int)).T

        ll, posteriors = self.h.score_samples(X)

        assert posteriors.shape == (n_samples, self.n_components)
        assert np.allclose(posteriors.sum(axis=1), np.ones(n_samples))

    def test_sample(self, n=1000):
        X, state_sequence = self.h.sample(n, random_state=self.prng)
        assert X.ndim == 2
        assert len(X) == len(state_sequence) == n
        assert len(np.unique(X)) == self.n_features

    def test_fit(self, params='ste', n_iter=5, **kwargs):
        h = self.h
        h.params = params

        lengths = np.array([10] * 10)
        X, _state_sequence = h.sample(lengths.sum(), random_state=self.prng)

        # Mess up the parameters and see if we can re-learn them.
        h.startprob_ = normalize(self.prng.rand(self.n_components))
        h.transmat_ = normalize(self.prng.rand(self.n_components,
                                               self.n_components), axis=1)
        h.emissionprob_ = normalize(
            self.prng.rand(self.n_components, self.n_features), axis=1)

        trainll = fit_hmm_and_monitor_log_likelihood(
            h, X, lengths=lengths, n_iter=n_iter)

        # Check that the log-likelihood is always increasing during training.
        diff = np.diff(trainll)
        assert np.all(diff >= -1e-6), \
            "Decreasing log-likelihood: {0}".format(diff)

    def test_fit_emissionprob(self):
        self.test_fit('e')

    def test_fit_with_init(self, params='ste', n_iter=5, verbose=False,
                           **kwargs):
        h = self.h
        learner = hmm.MultinomialHMM(self.n_components, params=params,
                                     init_params=params)

        lengths = [10] * 10
        X, _state_sequence = h.sample(sum(lengths), random_state=self.prng)

        # use init_function to initialize paramerters
        learner._init(X, lengths=lengths)

        trainll = fit_hmm_and_monitor_log_likelihood(learner, X, n_iter=n_iter)

        # Check that the loglik is always increasing during training
        assert np.all(np.diff(trainll) <= 0)

    def test__check_input_symbols(self):
        assert self.h._check_input_symbols([[0, 0, 2, 1, 3, 1, 1]])
        assert not self.h._check_input_symbols([[0, 0, 3, 5, 10]])
        assert not self.h._check_input_symbols([[0]])
        assert not self.h._check_input_symbols([[0., 2., 1., 3.]])
        assert not self.h._check_input_symbols([[0, 0, -2, 1, 3, 1, 1]])
