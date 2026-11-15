"""Budget guards exercised before objective evaluation, using artificial data."""
import unittest
import random
from types import SimpleNamespace
from unittest.mock import patch
from experiments.evaluation import run
from src.models.synthcore import run_ensemble, SOURCE
from src.utils import ezr
from study import METHODS, evaluation_budget
import analysis
from test_analysis import dataset, record
from test_synthcore import Model


class BudgetTests(unittest.TestCase):
    def data(self):
        return ezr.DATA([['A', 'Score-']] + [[i, i] for i in range(128)])

    def test_rrp_stops_before_a_twenty_fifth_label(self):
        data = self.data()
        scored = []
        d2h = ezr.d2h
        def counting(i, row):
            scored.append(row)
            self.assertLessEqual(len(scored), 24)
            return d2h(i, row)
        def slow_split(i, region, sortp, before, score):
            # Make many splits so the budget, rather than leaf size, stops RRP.
            score(i, region[0]); score(i, region[1])
            return region[2:], region[:2], region[2], region[0]
        with patch.object(ezr, 'd2h', counting), patch.object(ezr, 'half', slow_split):
            result = run.rrp(data)
        self.assertTrue(result['budget_exhausted'])
        self.assertEqual(len(scored), 24)
        self.assertEqual(result['oracle_evaluations'], 24)
        self.assertIn(result['selected_row'], scored)

    def test_rrp_reuses_pole_labels(self):
        data = self.data()
        def repeated_split(i, region, sortp, before, score):
            score(i, data.rows[0]); score(i, data.rows[1])
            return region[:len(region)//2], [], data.rows[0], data.rows[1]
        with patch.object(ezr, 'half', repeated_split):
            result = run.rrp(data)
        self.assertEqual(result['oracle_evaluations'], 2)

    def test_rrp_preserves_selection_when_budget_is_not_exhausted(self):
        for seed in range(5):
            data = self.data()
            random.seed(seed)
            expected, _, _ = ezr.branch(data, data.rows, 4)
            random.seed(seed)
            result = run.rrp(data)
            self.assertFalse(result['budget_exhausted'])
            self.assertEqual(result['selected_row'], expected[0])

    def test_cli_rejects_out_of_scope_schedules(self):
        import contextlib
        import io
        import rerun
        for method in ('unknown-method', 'SynthCore'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                rerun.main(['--methods', method])
            self.assertEqual(error.exception.code, 2)

    def test_scouting_requires_capacity_before_it_is_called(self):
        from unittest.mock import Mock
        scout, generate = Mock(), Mock()
        with self.assertRaisesRegex(ValueError, '18 initial'):
            run.optimize(self.data(), generate, budget=16, scout=scout)
        scout.assert_not_called(); generate.assert_not_called()

    def test_optimize_rejects_over_budget_or_legacy_schedules(self):
        for kwargs in ({'budget': 25}, {'budget': True}, {'policy': 'legacy-20-plus-warm'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run.optimize(self.data(), None, **kwargs)

    def test_oversized_warm_start_is_rejected_before_new_labels(self):
        data = self.data()
        scored = []
        d2h = ezr.d2h
        def counting(i, row):
            scored.append(tuple(row))
            return d2h(i, row)
        with patch.object(ezr, 'd2h', counting), self.assertRaisesRegex(ValueError, 'exactly four'):
            run.optimize(data, lambda best, rest: [[i] for i in range(100)])
        self.assertEqual(len(set(scored)), 4)

    def test_synthcore_oversized_reply_fails_before_candidate_evaluation(self):
        data = self.data()
        text = '|A|Class|\n|---|---|\n' + '\n'.join(f'|{i}|Best|' for i in range(100))
        model = Model(text)
        scored = set()
        d2h, chebyshev = ezr.d2h, ezr.chebyshev
        def observe(fn):
            def score(i, row):
                scored.add(tuple(row))
                return fn(i, row)
            return score
        with patch.object(ezr, 'd2h', observe(d2h)), patch.object(ezr, 'chebyshev', observe(chebyshev)):
            with self.assertRaisesRegex(ValueError, 'at most four'):
                run_ensemble(data, model, SOURCE, 42)
        self.assertEqual(len(scored), 16)
        self.assertEqual(model.calls, 1)

    def test_synthcore_full_ensemble_is_not_an_execution_option(self):
        model = Model('unused')
        with self.assertRaisesRegex(ValueError, 'exactly three'):
            run_ensemble(self.data(), model, SOURCE, 42, sessions=15)
        self.assertEqual(model.calls, 0)

    def test_synthcore_checks_representatives_before_scoring(self):
        data = self.data()
        with patch.object(ezr, 'chebyshev', side_effect=AssertionError('Must not score')):
            with self.assertRaisesRegex(ValueError, '16 initial'):
                run_ensemble(data, Model('unused'), SOURCE, 42,
                             leaf_override=lambda *args, **kwargs: data.rows[:17])

    def test_analysis_rejects_excessive_or_missing_counts_for_every_method(self):
        for method in METHODS + ('H-DKP', 'SynthCore-28'):
            cohort = 'expert' if method == 'H-DKP' else 'automated'
            item = dataset()
            for requests in (None, True, evaluation_budget(method) + 1):
                with self.subTest(method=method, requests=requests):
                    row = record(method=method, cohort=cohort,
                                 expert_id='expert_01' if method == 'H-DKP' else '')
                    row['oracle_evaluations'] = requests
                    with self.assertRaisesRegex(analysis.AnalysisError, 'evaluation count'):
                        analysis.validate_trials([row], {cohort: [item]}, cohort, 2,
                                                 methods=METHODS + ('SynthCore-28',))

    def test_analysis_accepts_capped_rrp_and_partial_synthcore(self):
        for method, requests in (('RRP', 7), ('SynthCore-28', 16)):
            row = record(method=method)
            row.update(oracle_evaluations=requests, labeling_cost=requests)
            analysis.validate_trials([row], {'automated': [dataset()]}, 'automated', 2,
                                     methods=METHODS + ('SynthCore-28',))


if __name__ == '__main__':
    unittest.main()
