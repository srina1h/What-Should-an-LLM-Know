"""Offline behavioral checks for the corrected ensemble endpoint."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.models.synthcore import run_ensemble, SOURCE
from src.utils import ezr

class Model:
    def __init__(self, text): self.calls=0; self.text=text
    def invoke(self, messages):
        self.calls+=1
        return SimpleNamespace(content=self.text)

class EnsembleTests(unittest.TestCase):
    def data(self):
        return ezr.DATA([['Score-','A','kind']]+[[i+1,i%7,'x' if i%2 else 'y'] for i in range(64)])
    def test_empty_generations_keep_initial_context_without_search(self):
        data=self.data(); model=Model('|A|kind|Class|\n|---|---|---|')
        with patch.object(ezr,'smo',side_effect=AssertionError('No downstream SMO')):
            scores,audit,rows=run_ensemble(data,model,SOURCE,42)
        self.assertEqual(model.calls,15)
        self.assertEqual(len(audit['sessions']),15)
        self.assertTrue(all(s['generated_count']==0 for s in audit['sessions']))
        self.assertTrue(all(s['retained'] for s in audit['sessions']))
        self.assertEqual(scores['d2h'],min(ezr.d2h(data,r) for r in rows))
        self.assertEqual(scores['chebyshev'],ezr.chebyshev(data,rows[0]))
    def test_interleaved_objective_columns_map_features_by_position(self):
        data=self.data(); model=Model('|A|kind|Class|\n|---|---|---|\n|1e0|x|Best|\n|-2|y|Rest|')
        _,audit,_=run_ensemble(data,model,SOURCE,42)
        self.assertEqual(model.calls,15)
        for session in audit['sessions']:
            self.assertEqual(session['generated_count'],2)
            self.assertEqual(session['generated'][0],['?',1.0,'x'])
            self.assertEqual(session['generated'][1],['?',-2.0,'y'])
            self.assertTrue(all(tuple(row) in {tuple(r) for r in data.rows} for row in session['mapped']))

if __name__=='__main__': unittest.main()
