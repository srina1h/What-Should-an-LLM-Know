"""Offline execution checks using synthetic configurations and model replies."""
import contextlib
import io
import json
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import rerun


def examples():
    return {'better_examples':[{'features':[1,2,3,4]},{'features':[2,3,4,5]}],
            'poorer_examples':[{'features':[7,8,9,1]},{'features':[8,9,1,2]}]}


class FakeModel:
    def __init__(self,method):
        self.method=method;self.calls=0

    def invoke(self,messages):
        self.calls+=1
        if self.method in ('BS-LLM','SynthCore'):
            content='|A|B|C|D|Class|\n|---|---|---|---|---|\n|1|2|3|4|Best|\n|2|3|4|5|Best|\n|7|8|9|1|Rest|\n|8|9|1|2|Rest|'
        elif self.method=='DAPR':
            text=str(messages)
            if 'reduced feature subspace' in text:
                size=int(re.search(r'exactly (\d+) values',text)[1])
                content=json.dumps({'candidates':[[i+1]*size for i in range(4)]})
            else:
                content='BETTER:\n- A=1, B=2, C=3, D=4\n- A=2, B=3, C=4, D=5\nWORSE:\n- A=7, B=8, C=9, D=1\n- A=8, B=9, C=1, D=2'
        elif self.method.startswith('AMP-'):
            n=int(self.method[-1])
            if self.calls==1:content='A and B describe feature relationships.'
            elif self.calls==2 and n>=3:content='Use numeric values in the listed feature domains.'
            elif self.calls==(2 if n==2 else 3):content=json.dumps(examples())
            else:content='{"status":"VALID"}'
        elif self.method.startswith('HKMA-') and self.method!='HKMA-rag' and self.calls==1:
            content='A=1 appears in lower-scoring observed configurations than A=8.'
        else:
            content=json.dumps(examples())
        return SimpleNamespace(content=content)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.data=self.root/'task.csv'
        self.data.write_text('A,B,C,D,Score-\n'+''.join(
            f'{i%9+1},{(i*2)%9+1},{(i*3)%9+1},{(i*4)%9+1},{i+1}\n' for i in range(60)))
        self.item=dict(id='task',path='task.csv',feature_count=4,
                       corpus_root='notes',corpus_dataset_id='task')
        self.patch=patch.object(rerun,'ROOT',self.root);self.patch.start()

    def tearDown(self):
        self.patch.stop();self.temp.cleanup()

    def trial(self,method):
        model=FakeModel(method)
        knowledge=None
        if method=='H-DKP':
            (self.root/'rules.md').write_text('A must be positive.')
            knowledge=dict(path='rules.md')
        job=dict(method=method,input=self.item,knowledge=knowledge)
        with contextlib.redirect_stdout(io.StringIO()):
            result=rerun.run_trial(job,self.root,42,model)
        self.assertTrue(0<=result['d2h']<=1)
        self.assertTrue(0<=result['chebyshev']<=1)
        return result,model.calls

    def test_modern_amp_and_expert_cost_twenty_labels(self):
        for method,calls in [('AMP-2',2),('AMP-3',3),('H-DKP',1)]:
            with self.subTest(method=method):
                result,n=self.trial(method)
                self.assertEqual(result['labeling_cost'],20)
                self.assertEqual(n,calls)

    def test_legacy_warm_start_counts_extra_mapped_rows(self):
        for method,calls in [('BS-LLM',1),('AMP-4',7)]:
            with self.subTest(method=method):
                result,n=self.trial(method)
                self.assertEqual(result['labeling_cost'],24)
                self.assertEqual(n,calls)

    def test_legacy_positional_rejection_is_preserved(self):
        text=self.data.read_text().splitlines()
        rows=[line.split(',') for line in text[1:]]
        self.data.write_text('Score-,A,B,C,D\n'+''.join(','.join([row[-1]]+row[:-1])+'\n' for row in rows))
        result,n=self.trial('AMP-4')
        self.assertEqual(result['generated_candidates_dropped'],4)
        self.assertEqual(result['labeling_cost'],20)
        self.assertEqual(n,7)

    def test_dapr_intermediate_evaluations_are_additional(self):
        result,n=self.trial('DAPR')
        self.assertEqual(result['intermediate_labeling_cost'],8)
        self.assertEqual(result['labeling_cost'],32)
        self.assertEqual(n,3)

    def test_synthcore_retains_its_own_schedule(self):
        result,n=self.trial('SynthCore')
        self.assertEqual(result['nominal_labeling_budget'],30)
        self.assertEqual(result['labeling_cost'],34)
        self.assertEqual(n,1)

    def test_scouting_is_charged_inside_hkma_budget(self):
        result,n=self.trial('HKMA-scout')
        self.assertEqual(result['scout_evaluations'],10)
        self.assertEqual(result['labeling_cost'],20)
        self.assertEqual(n,2)

    def test_retrieval_variants_use_local_notes_without_extra_labels(self):
        import numpy as np
        from experiments.remaining_methods import hkma_pilot
        notes=self.root/'notes/task';notes.mkdir(parents=True)
        (notes/'source.md').write_text('A is a numeric input. B is another numeric input.')
        def embed(texts):
            return np.array([[len(t),sum(map(ord,t))%13,1,2] for t in texts],dtype=float)
        with patch.object(hkma_pilot,'embed_texts',embed):
            for method,calls in [('HKMA-rag',1),('HKMA-combined',2)]:
                result,n=self.trial(method)
                self.assertEqual(result['labeling_cost'],20)
                self.assertEqual(n,calls)

    def test_missing_response_cost_is_unknown(self):
        path=self.root/'call_01.response.json'
        path.write_text(json.dumps({'usage':dict(prompt_tokens=10,completion_tokens=5,total_tokens=15)}))
        usage=rerun.token_usage(self.root,1)
        self.assertIsNone(usage['api_cost_usd'])
        self.assertEqual(usage['total_tokens'],15)
        self.assertIsNone(rerun.token_usage(self.root,2)['total_tokens'])

    def test_no_calls_has_zero_api_cost(self):
        self.assertEqual(rerun.token_usage(self.root,0)['api_cost_usd'],0)

    def test_split_charges_are_summed_without_a_tariff(self):
        for n,cost in [(1,.001),(2,.002)]:
            (self.root/f'call_{n:02d}.response.json').write_text(json.dumps(
                {'usage':dict(prompt_tokens=10,completion_tokens=5,total_tokens=15,cost=cost)}))
        usage=rerun.token_usage(self.root,2)
        self.assertAlmostEqual(usage['api_cost_usd'],.003)
        self.assertEqual(usage['total_tokens'],30)

    def test_packaged_correction_helpers_import(self):
        from experiments.remaining_methods import dapr_repair2,amp_generation_repair_v6
        self.assertTrue(callable(dapr_repair2.RepairingModelV2))
        self.assertTrue(callable(amp_generation_repair_v6.with_fresh_amp_generation_repair))


if __name__=='__main__':
    unittest.main()
