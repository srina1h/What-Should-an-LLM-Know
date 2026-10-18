"""Public package contains datasets; independently supplied expert inputs stay external."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analysis
import rerun

class PublicInputsTests(unittest.TestCase):
    def test_only_current_dataset_versions_are_bundled(self):
        manifest=rerun.load_manifest()
        self.assertEqual(len(manifest['automated']),49)
        self.assertEqual(len(manifest['expert']),8)
        paths={d['path'] for cohort in ('automated','expert') for d in manifest[cohort]}
        self.assertEqual(len(paths),54)
        self.assertEqual({str(p.relative_to(rerun.ROOT)) for p in (rerun.ROOT/'data').rglob('*.csv')},paths)
        for cohort in ('automated','expert'):
            for d in manifest[cohort]:
                self.assertNotIn('knowledge_tracks',d)
                self.assertFalse(any(k.startswith('legacy') for k in d))
        self.assertFalse((rerun.ROOT/'knowledge/expert').exists())
        self.assertFalse((rerun.ROOT/'API_COST_PROVENANCE.md').exists())

    def test_hdkp_requires_replicators_rules(self):
        manifest={'expert':[dict(id='task')]}
        with self.assertRaisesRegex(ValueError,'your own rules'):
            rerun.make_jobs(manifest,'expert',['H-DKP'])

    def test_external_rule_config_accepts_new_reviewer_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'rules.md').write_text('Synthetic fixture rule.')
            config=p/'configuration.json'
            config.write_text(json.dumps({'task':[dict(expert_id='new_reviewer',path='rules.md')]}))
            manifest={'expert':[dict(id='task')]}
            rerun.load_expert_rules(manifest,config)
            jobs=rerun.make_jobs(manifest,'expert',['H-DKP'])
            self.assertEqual(jobs[0]['expert_id'],'new_reviewer')
            self.assertEqual(jobs[0]['knowledge']['path'],str((p/'rules.md').resolve()))

    def test_analysis_discovers_new_expert_tracks(self):
        manifest={'expert':[dict(id='task')]}
        records=[dict(cohort='expert',dataset='task',method='H-DKP',expert_id=n) for n in ('reviewer_b','reviewer_a')]
        analysis.attach_expert_tracks(manifest,records)
        self.assertEqual(analysis.expert_track(manifest['expert'][0],1),'reviewer_a')
        self.assertEqual(analysis.expert_track(manifest['expert'][0],2),'reviewer_b')

    def test_cost_analysis_allows_expert_comparator_runs_without_hdkp(self):
        manifest={'expert':[dict(id='task')]}
        analysis.attach_expert_tracks(manifest,[],require_hdkp=False)
        self.assertEqual(len(analysis.expected_groups(manifest,'expert')),12)

if __name__=='__main__':
    unittest.main()
