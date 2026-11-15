"""Public benchmark datasets and model settings."""
import csv
import hashlib
from pathlib import Path

AUTOMATED = [('apache_allmeasurements', 'data/config/Apache_AllMeasurements.csv', 'apache_allmeasurements'),
 ('ss_a', 'data/config/SS-A.csv', 'ss_a'),
 ('ss_b', 'data/config/SS-B.csv', 'ss_b'),
 ('ss_c', 'data/config/SS-C.csv', 'ss_c'),
 ('ss_d', 'data/config/SS-D.csv', 'ss_d'),
 ('ss_e', 'data/config/SS-E.csv', 'ss_e'),
 ('ss_f', 'data/config/SS-F.csv', 'ss_f'),
 ('ss_g', 'data/config/SS-G.csv', 'ss_g'),
 ('ss_h', 'data/config/SS-H.csv', 'ss_h'),
 ('ss_i', 'data/config/SS-I.csv', 'ss_i'),
 ('ss_j', 'data/config/SS-J.csv', 'ss_j'),
 ('ss_k', 'data/config/SS-K.csv', 'ss_k'),
 ('ss_l', 'data/config/SS-L.csv', 'ss_l'),
 ('ss_m', 'data/config/SS-M.csv', 'ss_m'),
 ('ss_n', 'data/config/SS-N.csv', 'ss_n'),
 ('ss_o', 'data/config/SS-O.csv', 'ss_o'),
 ('ss_p', 'data/config/SS-P.csv', 'ss_p'),
 ('ss_q', 'data/config/SS-Q.csv', 'ss_q'),
 ('ss_r', 'data/config/SS-R.csv', 'ss_r'),
 ('ss_s', 'data/config/SS-S.csv', 'ss_s'),
 ('ss_t', 'data/config/SS-T.csv', 'ss_t'),
 ('ss_u', 'data/config/SS-U.csv', 'ss_u'),
 ('ss_v', 'data/config/SS-V.csv', 'ss_v'),
 ('ss_w', 'data/config/SS-W.csv', 'ss_w'),
 ('ss_x', 'data/config/SS-X.csv', 'ss_x'),
 ('x264_allmeasurements', 'data/config/X264_AllMeasurements.csv', 'x264_allmeasurements'),
 ('healthcloseisses12mths0001_hard',
  'data/hpo/healthCloseIsses12mths0001-hard.csv',
  'healthcloseisses12mths0001_hard'),
 ('healthcloseisses12mths0011_easy',
  'data/hpo/healthCloseIsses12mths0011-easy.csv',
  'healthcloseisses12mths0011_easy'),
 ('hsmgp_num', 'data/misc/HSMGP_num.csv', 'hsmgp_num'),
 ('wine_quality', 'data/misc/Wine_quality.csv', 'wine_quality'),
 ('auto93', 'data/misc/auto93.csv', 'auto93'),
 ('rs_6d_c3_obj1', 'data/misc/rs-6d-c3_obj1.csv', 'rs_6d_c3_obj1'),
 ('rs_6d_c3_obj2', 'data/misc/rs-6d-c3_obj2.csv', 'rs_6d_c3_obj2'),
 ('sol_6d_c2_obj1', 'data/misc/sol-6d-c2-obj1.csv', 'sol_6d_c2_obj1'),
 ('wc_rs_3d_c4_obj1', 'data/misc/wc+rs-3d-c4-obj1.csv', 'wc_rs_3d_c4_obj1'),
 ('wc_sol_3d_c4_obj1', 'data/misc/wc+sol-3d-c4-obj1.csv', 'wc_sol_3d_c4_obj1'),
 ('wc_wc_3d_c4_obj1', 'data/misc/wc+wc-3d-c4-obj1.csv', 'wc_wc_3d_c4_obj1'),
 ('pom3a', 'data/process/pom3a.csv', 'pom3a'),
 ('pom3b', 'data/process/pom3b.csv', 'pom3b'),
 ('pom3c', 'data/process/pom3c.csv', 'pom3c'),
 ('pom3d', 'data/process/pom3d.csv', 'pom3d'),
 ('xomo_flight', 'data/process/xomo_flight.csv', 'xomo_flight'),
 ('xomo_ground', 'data/process/xomo_ground.csv', 'xomo_ground'),
 ('xomo_osp', 'data/process/xomo_osp.csv', 'xomo_osp'),
 ('xomo_osp2', 'data/process/xomo_osp2.csv', 'xomo_osp2'),
 ('wc_6d_c1_obj1', 'data/misc/wc-6d-c1-obj1.csv', 'wc_6d_c1_obj1'),
 ('sql_allmeasurements', 'data/config/SQL_AllMeasurements.csv', 'sql_allmeasurements'),
 ('coc1000', 'data/process/coc1000.csv', 'coc1000'),
 ('nasa93dem', 'data/process/nasa93dem.csv', 'nasa93dem')]

EXPERT = [('postgresql', 'data/systems/PostgreSQL.csv', 'PostgreSQL'),
 ('health_closed_issues', 'data/hpo/Health-ClosedIssues0001.csv', 'Project health'),
 ('xomo_flight', 'data/process/xomo_flight.csv', 'XOMO Flight'),
 ('pom3a', 'data/process/pom3a.csv', 'POM3a'),
 ('auto93', 'data/misc/auto93.csv', 'auto93'),
 ('life_expectancy', 'data/health_data/Life_Expectancy_Data.csv', 'Life Expectancy'),
 ('a2c_cartpole', 'data/rl/A2C_CartPole.csv', 'A2C CartPole'),
 ('llvm', 'data/systems/LLVM.csv', 'LLVM')]

MODEL = {'name': 'openrouter/openai/gpt-oss-120b', 'temperature': 0.7, 'top_p': 1.0, 'max_tokens': 4000}
EMBEDDING = {'model': 'sentence-transformers/all-MiniLM-L6-v2', 'revision': '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'}


def load_datasets(root):
    """Read schema and content hashes from the distributed benchmark tables."""
    root = Path(root)
    cache = {}
    def describe(entry):
        ident, relative, display = entry
        if relative not in cache:
            path = root / relative
            content = path.read_bytes().replace(b'\r\n', b'\n')
            with path.open(newline='') as stream:
                reader = csv.reader(stream)
                columns = [c.strip() for c in next(reader)]
                rows = sum(bool(row) for row in reader)
            cache[relative] = dict(path=relative, sha256=hashlib.sha256(content).hexdigest(),
                feature_count=sum(not c.endswith(('+', '-', '!', 'X')) for c in columns),
                objective_count=sum(c.endswith(('+', '-', '!')) for c in columns), rows=rows)
        return dict(cache[relative], id=ident, display_name=display, sk_dataset=display,
                    corpus_root='knowledge/documents', corpus_dataset_id=ident)
    return dict(automated=[describe(e) for e in AUTOMATED], expert=[describe(e) for e in EXPERT],
                model=dict(MODEL), embedding=dict(EMBEDDING))


def dataset_fingerprint(datasets):
    import json
    # Private rule files are tracked separately; public tables remain fixed across cohorts.
    public = {key: ([{k: v for k, v in entry.items() if k != 'knowledge_tracks'}
                     for entry in value] if key in ('automated', 'expert') else value)
              for key, value in datasets.items() if key in ('automated', 'expert', 'model', 'embedding')}
    return hashlib.sha256(json.dumps(public, sort_keys=True).encode()).hexdigest()
