"""Synthetic-only tests; never call a model or load archived experiment scores."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analysis as a
from stats.scott_knott import rank_methods


def dataset(ident='task', tracks=1, features=4):
    return dict(id=ident, display_name=ident, feature_count=features,
                knowledge_tracks=[dict(expert_id=f'expert_{i:02d}') for i in range(1, tracks + 1)])


def record(dataset='task', method='Random', rep=0, cohort='automated', expert_id='', score=.2,
           status='success', api_cost=.01):
    return dict(dataset=dataset, method=method, rep=rep, cohort=cohort, expert_id=expert_id,
                status=status, feature_count=4, d2h=score, chebyshev=score, labeling_cost=24,
                llm_calls=1, input_tokens=10, output_tokens=5, total_tokens=15,
                api_cost_usd=api_cost, wall_seconds=2.)


def trials(manifest, cohort='automated', repeats=2):
    return [record(dataset=ds, method=method, expert_id=track, rep=rep, cohort=cohort)
            for ds, method, track in a.expected_groups(manifest, cohort) for rep in range(repeats)]


class StatisticalTests(unittest.TestCase):
    def test_identical_constants_share_group(self):
        self.assertEqual(rank_methods({'a': [.2]*20, 'b': [.2]*20}, 1), {'a': 0, 'b': 0})

    def test_separated_constants_split(self):
        self.assertEqual(rank_methods({'bad': [1.]*20, 'good': [0.]*20}, 1), {'good': 0, 'bad': 1})

    def test_recursive_three_groups_and_reproducibility(self):
        samples = {name: [base + x*.001 for x in range(20)]
                   for name, base in [('best', 0), ('middle', .4), ('worst', .9)]}
        expected = {'best': 0, 'middle': 1, 'worst': 2}
        self.assertEqual(rank_methods(samples, 123), expected)
        self.assertEqual(rank_methods(samples, 123), expected)


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.manifest = dict(automated=[dataset()], expert=[dataset()])
        self.records = trials(self.manifest)

    def test_complete_cohort(self):
        groups, coverage = a.validate_trials(self.records, self.manifest, 'automated', 2)
        a.require_complete(coverage)
        self.assertEqual(len(groups), 12)

    def test_missing_success_rejected_and_failure_reported(self):
        self.records[0]['status'] = 'failed'
        self.records.pop(1)
        _, coverage = a.validate_trials(self.records, self.manifest, 'automated', 2)
        random = next(r for r in coverage if r['method'] == 'Random')
        self.assertEqual((random['failed_attempts'], random['missing_successes'], random['unattempted_repeats']), (1, 2, 1))
        with self.assertRaisesRegex(a.AnalysisError, 'Incomplete cohort'):
            a.require_complete(coverage)

    def test_duplicate_success_rejected(self):
        self.records.append(dict(self.records[0]))
        with self.assertRaisesRegex(a.AnalysisError, 'Duplicate successful'):
            a.validate_trials(self.records, self.manifest, 'automated', 2)

    def test_failed_attempt_then_success_allowed_and_counted(self):
        self.records.append(dict(self.records[0], status='failed'))
        _, coverage = a.validate_trials(self.records, self.manifest, 'automated', 2)
        a.require_complete(coverage)
        self.assertEqual(sum(r['failed_attempts'] for r in coverage), 1)

    def test_token_inconsistency_rejected(self):
        self.records[0]['total_tokens'] = 9
        with self.assertRaisesRegex(a.AnalysisError, 'total_tokens differs'):
            a.validate_trials(self.records, self.manifest, 'automated', 2)

    def test_extra_expert_track_rejected(self):
        records = trials(self.manifest, 'expert')
        records.append(record(cohort='expert', method='H-DKP', expert_id='expert_02'))
        with self.assertRaisesRegex(a.AnalysisError, 'Unexpected expert group'):
            a.validate_trials(records, self.manifest, 'expert', 2)

    def test_cohorts_are_not_mixed(self):
        expert = trials(self.manifest, 'expert')
        for row in expert:
            row['d2h'] = .9
        groups, _ = a.validate_trials(self.records + expert, self.manifest, 'automated', 2)
        self.assertEqual([r['d2h'] for r in groups[('task', 'Random', '')]], [.2, .2])

    def test_unknown_labeling_cost_preserved(self):
        for row in self.records:
            if row['method'] == 'RRP':
                row['labeling_cost'] = None
        groups, coverage = a.validate_trials(self.records, self.manifest, 'automated', 2)
        a.require_complete(coverage)
        row = next(r for r in a.cost_summary(groups) if r['method'] == 'RRP')
        self.assertIsNone(row['labeling_cost_mean'])
        self.assertIsNone(row['labeling_cost_min'])
        self.assertEqual(row['labeling_cost_missing_successes'], 2)

    def test_nonfinite_score_rejected(self):
        self.records[0]['d2h'] = float('nan')
        with self.assertRaises(a.AnalysisError):
            a.validate_trials(self.records, self.manifest, 'automated', 2)


class AggregationTests(unittest.TestCase):
    def test_equal_task_weight_not_pooled_repeat_weight(self):
        groups = {('a', 'Random', ''): [record(dataset='a', rep=i, score=0) for i in range(2)],
                  ('b', 'Random', ''): [record(dataset='b', rep=i, score=1) for i in range(8)]}
        summary = a.equal_dataset_means(groups, ['a', 'b'], methods=('Random',))
        self.assertEqual([r['equal_dataset_mean'] for r in summary], [.5, .5])

    def test_expert_pool_switches_only_dual_track_task(self):
        manifest = dict(expert=[dataset('single'), dataset('dual', tracks=2)])
        rows = trials(manifest, 'expert', repeats=20)
        for r in rows:
            if r['method'] == 'H-DKP':
                r['d2h'] = 0 if r['expert_id'] == 'expert_01' else 1
        groups, coverage = a.validate_trials(rows, manifest, 'expert', 20)
        a.require_complete(coverage)
        pools = {n: a.memberships(groups, manifest['expert'], f'expert_{n}', metrics=('d2h',)) for n in (1, 2)}
        for n, result in pools.items():
            self.assertEqual(len(result), 26)
            self.assertEqual(len({r['dataset'] for r in result}), 2)
        rank = lambda n, ds: next(r['scott_knott_rank'] for r in pools[n] if r['method'] == 'H-DKP' and r['dataset'] == ds)
        self.assertEqual(rank(1, 'single'), rank(2, 'single'))
        self.assertEqual(rank(1, 'dual'), 0)
        self.assertGreater(rank(2, 'dual'), 0)

    def test_unknown_cost_is_not_zero_and_retry_overhead_is_separate(self):
        rows = [record(rep=0, api_cost=.01), record(rep=1, api_cost=.03),
                record(rep=1, status='failed', api_cost=None)]
        result = a.cost_summary({('task', 'Random', ''): rows})[0]
        self.assertEqual(result['api_cost_usd_per_successful_repeat'], .02)
        self.assertIsNone(result['api_cost_usd_all_attempts_per_success'])
        self.assertEqual(result['llm_calls_per_successful_repeat'], 1)
        self.assertEqual(result['llm_calls_all_attempts_per_success'], 1.5)
        rows[0]['api_cost_usd'] = None
        self.assertIsNone(a.cost_summary({('task', 'Random', ''): rows})[0]['api_cost_usd_per_successful_repeat'])

    def test_tier_boundaries(self):
        self.assertEqual([a.tier(n) for n in (5, 6, 11, 12)], ['low', 'medium', 'medium', 'high'])

    def test_outputs_label_unknown_and_escape_latex(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            a.write_table(output, 'example', [dict(method='expert_01', cost=None)])
            self.assertIn('unavailable', (output/'example.csv').read_text())
            self.assertIn(r'expert\_01', (output/'example.tex').read_text())


if __name__ == '__main__':
    unittest.main()
