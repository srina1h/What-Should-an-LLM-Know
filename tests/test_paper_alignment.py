"""Behavioral checks against the November 13 draft, with synthetic evidence."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import analysis as a
import rerun
from study import METHODS, PROTOCOL_VERSION, SENSITIVITY_METHODS
from test_analysis import dataset, record
from test_synthcore import Model
from src.models.synthcore import run_ensemble, SOURCE
from src.utils import ezr


class PaperAlignmentTests(unittest.TestCase):
    def test_default_runner_uses_ten_primary_methods(self):
        self.assertEqual(len(rerun.METHODS), 10)
        self.assertNotIn('SynthCore', rerun.METHODS)
        self.assertNotIn('DAPR', rerun.METHODS)
        self.assertEqual(a.METRICS, ('chebyshev',))

    def test_old_protocol_cannot_be_silently_relabelled(self):
        manifest = dict(automated=[dataset()])
        old = record()
        old.pop('protocol_version', None)
        with self.assertRaisesRegex(a.AnalysisError, 'protocol'):
            a.validate_trials([old], manifest, 'automated', 2)

    def test_synthcore28_is_exact_three_session_prefix(self):
        text='|A|kind|Class|\n|---|---|---|\n|1|x|Best|\n|2|y|Best|\n|3|x|Rest|\n|4|y|Rest|'
        data=lambda: ezr.DATA([['Score-','A','kind']]+[[i+1,i%7,'x' if i%2 else 'y'] for i in range(64)])
        _, full, _ = run_ensemble(data(), Model(text), SOURCE, 42)
        scores, short, rows = run_ensemble(data(), Model(text), SOURCE, 42, sessions=3)
        self.assertEqual(short['sessions'], full['sessions'][:3])
        self.assertEqual(short['evaluation_requests'], short['initial_representatives']+12)
        self.assertEqual(scores['chebyshev'], ezr.chebyshev(data(), rows[0]))

    def test_all_observations_survive_and_repeated_mappings_count_once(self):
        from experiments.remaining_methods.run import optimize
        data=ezr.DATA([['A','Score-']]+[[i,i] for i in range(60)])
        result=optimize(data, lambda best,rest: [[0]]*4, 24, 42, 'equal-oracle')
        self.assertEqual(result['oracle_evaluations'],24)
        self.assertEqual(result['smo_evaluations'],16)
        self.assertEqual(len(set(result['evaluated_row_indices'])),21)
        self.assertTrue(set(result['initial_row_indices']+[0]).issubset(result['handoff_row_indices']))
        self.assertEqual(result['selected_row'],[0,0])

    def test_offline_preparation_is_counted_once_per_rule_set(self):
        preparation=dict(expert_contacts=9,generation_exchanges=7)
        rows=[dict(record(method='H-DKP',expert_id='reviewer'),preparation=preparation,
                   rules_sha256='frozen-rule-hash') for _ in range(20)]
        summary=a.preparation_summary(rows)
        self.assertEqual(len(summary),1)
        self.assertEqual(summary[0]['nominal_benchmark_accesses'],42)
        self.assertIsNone(summary[0]['distinct_labels'])
        self.assertEqual(summary[0]['rules_sha256'],'frozen-rule-hash')
        rows[-1]['preparation']=dict(expert_contacts=9,generation_exchanges=6)
        with self.assertRaisesRegex(a.AnalysisError,'Conflicting'):
            a.preparation_summary(rows)

    def test_metadata_includes_objective_directions(self):
        from btp.prompts.warm_start import warm_start_messages
        from btp.methods.amp import AMP_Strategy
        from types import SimpleNamespace
        data=ezr.DATA([['A','Loss-','Gain+']]+[[i,i,9-i] for i in range(10)])
        prompt=str(warm_start_messages(data,data.rows[:2],data.rows[-2:]))
        self.assertIn('Loss- (Minimize)',prompt)
        self.assertIn('Gain+ (Maximize)',prompt)
        class Capture:
            messages=[]
            def invoke(self,messages):
                self.messages.append(messages)
                return SimpleNamespace(content='{"better_examples":[{"features":[1]},{"features":[2]}],"poorer_examples":[{"features":[7]},{"features":[8]}]}')
        capture=Capture()
        AMP_Strategy(data,SimpleNamespace(pipeline=capture,amp_mode='AMP-2')).generate_examples(data.rows[:2],data.rows[-2:])
        self.assertIn('Gain+ (Objective - Maximize)',str(capture.messages[0]))

    def test_primary_latex_table_matches_compact_paper_columns(self):
        rows=[dict(method='AMP-4',datasets=49,best_group_count=44,percent=89.8,
                   low_best=13,low_datasets=15,medium_best=15,medium_datasets=17,
                   high_best=16,high_datasets=17,mean_chebyshev=.1862)]
        headings,cells=a.paper_layout('primary_low_label',rows)
        self.assertEqual(len(headings),6)
        self.assertEqual(cells[0][-1],'0.1862')
        self.assertIn('44',str(cells[0][1]))

    def test_external_rule_config_preserves_optional_preparation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'rule.md').write_text('Only qualitative reviewed rules.')
            path=root/'input.json'
            path.write_text(json.dumps({'task':[dict(expert_id='reviewer',path='rule.md',
                                                    preparation=dict(expert_contacts=9,generation_exchanges=7))]}))
            manifest=dict(expert=[dict(id='task')])
            rerun.load_expert_rules(manifest,path)
            track=manifest['expert'][0]['knowledge_tracks'][0]
            self.assertEqual(track['preparation']['nominal_benchmark_accesses'],42)
            self.assertEqual(track['sha256'],rerun.sha(root/'rule.md'))

    def test_offline_generation_exchanges_are_bounded_without_contact_count(self):
        from study import normalize_preparation
        for exchanges in (10,100):
            with self.subTest(exchanges=exchanges), self.assertRaisesRegex(ValueError,'nine'):
                normalize_preparation(dict(generation_exchanges=exchanges))
        self.assertEqual(normalize_preparation(dict(generation_exchanges=9))['nominal_benchmark_accesses'],54)

    def test_expert_trials_can_follow_comparators_without_changing_frozen_rules(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'manifest.json').write_text('{}')
            args=SimpleNamespace(output=str(root/'out'),repeats=1,seed=12345,
                                 repair_invalid=False,retry_failed=False)
            manifest=dict(model={'name':'fixture'})
            base=dict(cohort='expert',dataset='task',method='Random',expert_id='',
                      input=dict(path='task.csv',feature_count=4),knowledge=None)
            expert=dict(base,method='H-DKP',expert_id='reviewer',
                        knowledge=dict(path='rule.md',sha256='hash-a',
                                       preparation=dict(expert_contacts=9,generation_exchanges=7)))
            result=dict(selected_row=[1,2],labeling_cost=24,chebyshev=.2,d2h=.2)
            with patch.object(rerun,'ROOT',root), patch.object(rerun,'run_trial',return_value=result), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rerun.execute([base],args,manifest),0)
                self.assertEqual(rerun.execute([expert],args,manifest),0)
                self.assertEqual(rerun.execute([base],args,manifest),0)
                changed=dict(expert,knowledge=dict(expert['knowledge'],sha256='hash-b'))
                with self.assertRaisesRegex(ValueError,'configuration|rules'):
                    rerun.execute([changed],args,manifest)
            saved=json.loads((root/'out/config.json').read_text())
            self.assertEqual(saved['external_rule_hashes'],{'task/reviewer':'hash-a'})
            rows=[json.loads(x) for x in (root/'out/trials.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[-1]['preparation']['generation_exchanges'],7)

    def run_rq(self, rq, include_sensitivity=True, complete=True):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        manifest=dict(automated=[dataset()],expert=[dataset(tracks=2)])
        (root/'manifest.json').write_text(json.dumps(manifest))
        (root/'stats').mkdir(); (root/'stats/scott_knott.py').write_text('fixture')
        cohort='expert' if rq==3 else 'automated'
        methods=list(METHODS)+(['SynthCore-28'] if include_sensitivity and rq==4 else [])
        rows=[record(method=m, rep=n, cohort=cohort, score=.5) for m in methods for n in range(2)]
        for row in rows:
            row['protocol_version']=PROTOCOL_VERSION
            row['d2h']=.1
            if row['method']=='AMP-4': row['chebyshev']=0.
        if rq==3:
            rows += [dict(record(method='H-DKP',rep=n,cohort=cohort,expert_id=track),
                          protocol_version=PROTOCOL_VERSION, d2h=.9, chebyshev=0.)
                     for track in ('expert_01','expert_02') for n in range(2)]
        if not complete: rows.pop()
        ledger=root/'trials.jsonl'
        ledger.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        with patch.object(a,'ROOT',root), contextlib.redirect_stdout(io.StringIO()):
            a.run(rq,['--trials',str(ledger),'--output',str(root/'out'),'--expected-repeats','2'])
        return root/'out'

    def test_rq1_primary_table_has_tiers_and_chebyshev_mean(self):
        output=self.run_rq(1)
        text=(output/'primary_low_label.csv').read_text()
        self.assertIn('mean_chebyshev',text)
        self.assertNotIn('d2h',text)
        self.assertNotIn('DAPR',text)
        self.assertNotIn('SynthCore',text)
        self.assertEqual(len(text.splitlines()),11)

    def test_rq3_reports_both_baseline_medians_in_chebyshev(self):
        output=self.run_rq(3)
        text=(output/'expert_median_comparison.csv').read_text()
        self.assertIn('ezr_median_chebyshev',text)
        self.assertIn('bs_llm_median_chebyshev',text)
        self.assertIn('hdkp_median_chebyshev',text)
        self.assertNotIn('d2h',text)
        self.assertEqual(len(text.splitlines()),3)

    def test_rq4_recomputes_eleven_method_scope(self):
        output=self.run_rq(4)
        text=(output/'synthcore28_sensitivity.csv').read_text()
        self.assertIn('SynthCore-28',text)
        self.assertEqual(len(text.splitlines()),12)
        self.assertEqual(json.loads((output/'metadata.json').read_text())['methods'],list(SENSITIVITY_METHODS))

    def test_rq4_incomplete_performance_still_reports_observed_costs(self):
        output=self.run_rq(4,include_sensitivity=False)
        self.assertTrue((output/'operational_cost.csv').exists())
        self.assertFalse((output/'synthcore28_sensitivity.csv').exists())
        self.assertFalse(json.loads((output/'metadata.json').read_text())['complete'])


if __name__=='__main__': unittest.main()
