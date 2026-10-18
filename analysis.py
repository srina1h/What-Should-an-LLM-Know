"""Analyze fresh trial JSONL; no archived experiment results are required.

RQ1--3 refuse incomplete successful repeat sets. Failure and coverage tables are
written before this refusal, so missing evidence remains visible. RQ4 explicitly
reports observed-attempt costs even when performance coverage is incomplete.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from stats.scott_knott import rank_methods

ROOT = Path(__file__).resolve().parent
METHODS = ('Random', 'EZR', 'RRP', 'BS-LLM', 'SynthCore', 'AMP-2', 'AMP-3',
           'AMP-4', 'DAPR', 'HKMA-scout', 'HKMA-rag', 'HKMA-combined')
METRICS = ('d2h', 'chebyshev')
COSTS = ('llm_calls', 'input_tokens', 'output_tokens', 'total_tokens',
         'api_cost_usd', 'wall_seconds')
SK = dict(seed=20261016, bootstrap_samples=512, bootstrap_alpha=.05, cliffs_delta=.147)


class AnalysisError(ValueError):
    """Input cannot support the requested analysis."""


def tier(n):
    return 'low' if n < 6 else 'medium' if n <= 11 else 'high'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_groups(manifest, cohort):
    groups = {}
    for dataset in manifest[cohort]:
        ident = dataset['id']
        for method in METHODS:
            groups[(ident, method, '')] = dataset
        if cohort == 'expert':
            tracks = dataset.get('knowledge_tracks', [])
            if not tracks and not manifest.get('_require_hdkp', True):
                continue
            if not tracks or len(tracks) > 2:
                raise AnalysisError(f'{ident}: RQ3 requires independently collected H-DKP trials from one or two expert tracks')
            for track in tracks:
                key = (ident, 'H-DKP', track['expert_id'])
                if key in groups:
                    raise AnalysisError(f'Duplicate expert track: {key}')
                groups[key] = dataset
    if len({d['id'] for d in manifest[cohort]}) != len(manifest[cohort]):
        raise AnalysisError(f'Duplicate dataset IDs in {cohort} manifest')
    if not groups:
        raise AnalysisError(f'Empty {cohort} cohort')
    return groups


def finite_number(value, name, nullable=False):
    if value is None and nullable:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise AnalysisError(f'{name} must be a finite nonnegative number' + (' or null' if nullable else ''))


def load_trials(path):
    records = []
    with Path(path).open() as stream:
        for lineno, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AnalysisError(f'Invalid JSON at line {lineno}: {exc}') from exc
            if not isinstance(record, dict):
                raise AnalysisError(f'Line {lineno} is not an object')
            record = dict(record)
            record['_line'] = lineno
            records.append(record)
    return records


def validate_trials(records, manifest, cohort, expected_repeats):
    if expected_repeats < 2:
        raise AnalysisError('At least two repeats are required for bootstrap variance estimates')
    expected = expected_groups(manifest, cohort)
    groups = defaultdict(list)
    seen = set()
    for record in records:
        if record.get('cohort') not in ('automated', 'expert'):
            raise AnalysisError(f"Unknown or missing cohort at line {record.get('_line', '?')}")
        if record['cohort'] != cohort:
            continue
        key = (record.get('dataset'), record.get('method'), record.get('expert_id', ''))
        if key not in expected:
            raise AnalysisError(f'Unexpected {cohort} group {key}')
        rep = record.get('rep')
        if isinstance(rep, bool) or not isinstance(rep, int) or not 0 <= rep < expected_repeats:
            raise AnalysisError(f'{key}: rep must be in 0..{expected_repeats - 1}')
        if record.get('feature_count') != expected[key]['feature_count']:
            raise AnalysisError(f'{key}: feature count disagrees with manifest')
        if record.get('status') not in ('success', 'failed'):
            raise AnalysisError(f'{key}: status must be success or failed')
        for field in COSTS:
            if field not in record:
                raise AnalysisError(f'{key}: missing telemetry field {field}; use null when unavailable')
            finite_number(record[field], field, nullable=True)
        counts = (record['input_tokens'], record['output_tokens'], record['total_tokens'])
        if all(value is not None for value in counts) and counts[0] + counts[1] != counts[2]:
            raise AnalysisError(f'{key} repeat {rep}: total_tokens differs from input_tokens + output_tokens')
        for field in ('llm_calls', 'input_tokens', 'output_tokens', 'total_tokens'):
            if record[field] is not None and int(record[field]) != record[field]:
                raise AnalysisError(f'{key}: {field} must be an integer count')
        if record['status'] == 'success':
            identity = (*key, rep)
            if identity in seen:
                raise AnalysisError(f'Duplicate successful repeat: {identity}')
            seen.add(identity)
            for field in METRICS:
                finite_number(record.get(field), field)
            if 'labeling_cost' not in record:
                raise AnalysisError(f'{key}: missing labeling_cost; use null when unavailable')
            finite_number(record['labeling_cost'], 'labeling_cost', nullable=True)
        groups[key].append(record)
    coverage = []
    for key in expected:
        attempts = groups[key]
        successes = {r['rep'] for r in attempts if r['status'] == 'success'}
        failed_reps = {r['rep'] for r in attempts if r['status'] == 'failed'}
        attempted = {r['rep'] for r in attempts}
        coverage.append(dict(cohort=cohort, dataset=key[0], method=key[1], expert_id=key[2],
                             expected_repeats=expected_repeats, successful_repeats=len(successes),
                             failed_attempts=sum(r['status'] == 'failed' for r in attempts),
                             failed_only_repeats=len(failed_reps - successes),
                             unattempted_repeats=expected_repeats - len(attempted),
                             missing_successes=expected_repeats - len(successes),
                             missing_rep_ids=';'.join(map(str, sorted(set(range(expected_repeats)) - successes)))))
    return groups, coverage


def require_complete(coverage):
    missing = [r for r in coverage if r['missing_successes']]
    if missing:
        raise AnalysisError(f"Incomplete cohort: {len(missing)} groups lack {sum(r['missing_successes'] for r in missing)} successful repeats. See coverage.csv; comparative tables were not generated.")


def successful(groups, key):
    return sorted((r for r in groups[key] if r['status'] == 'success'), key=lambda r: r['rep'])


def equal_dataset_means(groups, dataset_ids, methods=METHODS):
    return [dict(method=method, metric=metric, datasets=len(dataset_ids),
                 equal_dataset_mean=mean(mean(r[metric] for r in successful(groups, (dataset, method, '')))
                                         for dataset in dataset_ids))
            for method in methods for metric in METRICS]


def expert_track(dataset, expert_number):
    """Single-track tasks appear unchanged in both pools; dual-track tasks switch."""
    tracks = dataset['knowledge_tracks']
    if len(tracks) == 1:
        return tracks[0]['expert_id']
    ordered = sorted(t['expert_id'] for t in tracks)
    if not 1 <= expert_number <= len(ordered):
        raise AnalysisError(f"{dataset['id']}: expert pool index is out of range")
    return ordered[expert_number - 1]


def attach_expert_tracks(manifest, records, require_hdkp=True):
    """Track identities come from the replicator's new trials, not bundled study records."""
    manifest['_require_hdkp'] = require_hdkp
    for dataset in manifest['expert']:
        tracks = sorted({r.get('expert_id', '') for r in records
                         if r.get('cohort') == 'expert' and r.get('dataset') == dataset['id']
                         and r.get('method') == 'H-DKP'})
        if '' in tracks:
            raise AnalysisError('H-DKP trials require a nonempty expert_id')
        dataset['knowledge_tracks'] = [dict(expert_id=track) for track in tracks]


def memberships(groups, datasets, pool='full', metrics=METRICS):
    methods = tuple(m for m in METHODS if pool != 'without_dapr' or m != 'DAPR')
    expert_number = int(pool.split('_')[1]) if pool.startswith('expert_') else None
    if expert_number:
        methods += ('H-DKP',)
    result = []
    for dataset in sorted(datasets, key=lambda d: d['id']):
        for metric in metrics:
            samples = {}
            for method in methods:
                track = expert_track(dataset, expert_number) if method == 'H-DKP' else ''
                samples[method] = [r[metric] for r in successful(groups, (dataset['id'], method, track))]
            seed_dataset = dataset.get('sk_dataset', dataset.get('display_name', dataset['id']))
            context = f"{SK['seed']}:{pool}/{metric}/{seed_dataset}"
            seed = int(hashlib.sha256(context.encode()).hexdigest()[:16], 16)
            ranks = rank_methods(samples, seed, bootstrap_samples=SK['bootstrap_samples'],
                                 alpha=SK['bootstrap_alpha'], delta=SK['cliffs_delta'])
            for method in methods:
                result.append(dict(pool=pool, metric=metric, dataset=dataset['id'], method=method,
                                   tier=tier(dataset['feature_count']), scott_knott_rank=ranks[method],
                                   sk_best=ranks[method] == 0))
    return result


def summarize_memberships(rows, by_tier=False):
    groups = defaultdict(list)
    for r in rows:
        groups[(r['pool'], r['metric'], r['tier'] if by_tier else 'overall', r['method'])].append(r)
    return [dict(pool=key[0], metric=key[1], tier=key[2], method=key[3], datasets=len(values),
                 scott_knott_count=sum(r['sk_best'] for r in values),
                 percent=100 * sum(r['sk_best'] for r in values) / len(values))
            for key, values in sorted(groups.items(), key=lambda item: (
                item[0][0], item[0][1], ('overall','low','medium','high').index(item[0][2]), item[0][3]))]


def complete_mean(records, field):
    """Unknown telemetry remains unknown, including when only one value is absent."""
    values = [r.get(field) for r in records]
    return mean(values) if values and all(v is not None for v in values) else None


def cost_summary(groups):
    pooled = defaultdict(list)
    for (dataset, method, expert_id), attempts in groups.items():
        pooled[(method, expert_id)].extend(attempts)
    rows = []
    for (method, expert_id), attempts in sorted(pooled.items()):
        successes = [r for r in attempts if r['status'] == 'success']
        row = dict(method=method, expert_id=expert_id, datasets_observed=len({r['dataset'] for r in attempts}),
                   attempts=len(attempts), successful_repeats=len(successes),
                   failed_attempts=len(attempts) - len(successes))
        for field in COSTS:
            row[field + '_per_successful_repeat'] = complete_mean(successes, field)
            total = sum(r[field] for r in attempts) if all(r.get(field) is not None for r in attempts) else None
            row[field + '_all_attempts_per_success'] = total / len(successes) if total is not None and successes else None
            row[field + '_missing_attempts'] = sum(r.get(field) is None for r in attempts)
        labels = [r['labeling_cost'] for r in successes]
        labels_available = bool(labels) and all(v is not None for v in labels)
        row.update(labeling_cost_mean=mean(labels) if labels_available else None,
                   labeling_cost_min=min(labels) if labels_available else None,
                   labeling_cost_max=max(labels) if labels_available else None,
                   labeling_cost_missing_successes=sum(v is None for v in labels))
        rows.append(row)
    return rows


def latex_escape(value):
    mapping = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#',
               '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(mapping.get(c, c) for c in str(value))


def format_value(value):
    if value is None:
        return 'unavailable'
    return f'{value:.8g}' if isinstance(value, float) else str(value)


def paper_layout(name, rows):
    """Keep CSV evidence long-form; render manuscript tables in readable columns."""
    if name in ('table3_best_group', 'table5_without_dapr'):
        methods = sorted({r['method'] for r in rows}, key=lambda m: (
            -next(r['scott_knott_count'] for r in rows if r['method']==m and r['metric']=='d2h'), m))
        def cell(method, metric):
            r=next(x for x in rows if x['method']==method and x['metric']==metric)
            return f"{r['scott_knott_count']} ({r['percent']:.1f}%)" if name=='table3_best_group' else r['scott_knott_count']
        return ['Method','d2h','Chebyshev'], [[m,cell(m,'d2h'),cell(m,'chebyshev')] for m in methods]
    if name=='table4_equal_dataset_means':
        methods=sorted({r['method'] for r in rows})
        return ['Method','d2h','Chebyshev'], [[m]+[f"{next(r['equal_dataset_mean'] for r in rows if r['method']==m and r['metric']==metric):.4f}" for metric in METRICS] for m in methods]
    if name=='table6_dimensionality':
        methods=sorted({r['method'] for r in rows})
        return ['Method','d2h low','d2h medium','d2h high','Chebyshev low','Chebyshev medium','Chebyshev high'], [
            [m]+[next(r['scott_knott_count'] for r in rows if r['method']==m and r['metric']==metric and r['tier']==band)
                  for metric in METRICS for band in ('low','medium','high')] for m in methods]
    if name=='table7_expert_best_group':
        methods=sorted({r['method'] for r in rows})
        pools=sorted({r['pool'] for r in rows})
        return ['Method']+[f'Expert pool {i+1}' for i in range(len(pools))], [[m]+[
            f"{next(r['scott_knott_count'] for r in rows if r['method']==m and r['pool']==pool)}/{next(r['datasets'] for r in rows if r['method']==m and r['pool']==pool)}"
            for pool in pools] for m in methods]
    if name=='table8_operational_cost':
        def num(value,digits): return 'unavailable' if value is None else f'{value:.{digits}f}'
        return ['Method','LLM calls','Tokens','API cost (USD)','Wall (s)'], [[
            r['method']+(' '+r['expert_id'] if r['expert_id'] else ''),
            num(r['llm_calls_per_successful_repeat'],2),num(r['total_tokens_per_successful_repeat'],0),
            num(r['api_cost_usd_per_successful_repeat'],6),num(r['wall_seconds_per_successful_repeat'],4)] for r in rows]
    if name=='table1_expert_cohort':
        return ['Dataset','Inputs','Objectives','Tier','Tracks'], [[r['display_name'],r['feature_count'],r['objective_count'],r['tier'],r['expert_tracks']] for r in rows]
    return list(rows[0]), [[format_value(r[k]) for k in rows[0]] for r in rows]


def write_table(output, name, rows):
    if not rows:
        return
    fields = list(rows[0])
    with (output / f'{name}.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: 'unavailable' if v is None else v for k, v in row.items()} for row in rows)
    headings, cells = paper_layout(name, rows)
    tex = ['% Generated from fresh trials. Requires no LaTeX packages.',
           r'\begin{tabular}{' + 'l' * len(headings) + '}',
           ' & '.join(map(latex_escape, headings)) + r' \\', r'\hline']
    tex += [' & '.join(latex_escape(format_value(value)) for value in row) + r' \\' for row in cells]
    tex += [r'\end{tabular}', '']
    (output / f'{name}.tex').write_text('\n'.join(tex))
    print(f'{name}: {len(rows)} rows -> {output / (name + ".csv")}')
    if name.startswith('table'):
        print(' | '.join(fields))
        for row in rows:
            print(' | '.join(format_value(row[f]) for f in fields))


def run(rq, argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=Path, required=True, help='Fresh runner JSONL')
    parser.add_argument('--output', type=Path, required=True, help='New or empty output directory')
    parser.add_argument('--expected-repeats', type=int, default=20)
    if rq == 2:
        parser.add_argument('--without-dapr', action='store_true', help='Also produce reduced-pool tier supplement')
    if rq == 4:
        parser.add_argument('--cohort', choices=('automated', 'expert'), default='automated')
    args = parser.parse_args(argv)
    output = args.output
    try:
        if output.exists() and any(output.iterdir()):
            raise AnalysisError('Use a new or empty output directory to prevent stale tables')
        output.mkdir(parents=True, exist_ok=True)
        manifest_path = ROOT / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        cohort = 'expert' if rq == 3 else getattr(args, 'cohort', 'automated')
        records = load_trials(args.trials)
        if cohort == 'expert':
            attach_expert_tracks(manifest, records, require_hdkp=(rq == 3))
        groups, coverage = validate_trials(records, manifest, cohort, args.expected_repeats)
        write_table(output, 'coverage', coverage)
        metadata = dict(rq=rq, cohort=cohort, trials_sha256=sha256(args.trials),
                        manifest_sha256=sha256(manifest_path),
                        analysis_sha256=sha256(Path(__file__)),
                        scott_knott_sha256=sha256(ROOT / 'stats/scott_knott.py'),
                        expected_repeats=args.expected_repeats, statistical_settings=SK,
                        ignored_other_cohort_attempts=sum(r['cohort'] != cohort for r in records),
                        complete=not any(r['missing_successes'] for r in coverage),
                        failed_attempts=sum(r['failed_attempts'] for r in coverage),
                        missing_successes=sum(r['missing_successes'] for r in coverage),
                        score_estimand='equal weight per dataset; successful final-optimizer trials',
                        cost_estimand='observed attempts; successful-repeat mean and all-attempt spend per success',
                        seed_context='seed:pool/metric/sk_dataset (or display_name or id)')
        (output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
        print(f"Coverage: {metadata['failed_attempts']} failed attempts; {metadata['missing_successes']} missing successful repeats.")
        if rq != 4:
            require_complete(coverage)
        datasets = manifest[cohort]
        if rq == 1:
            full = memberships(groups, datasets)
            reduced = memberships(groups, datasets, 'without_dapr')
            write_table(output, 'membership', full + reduced)
            write_table(output, 'table3_best_group', summarize_memberships(full))
            write_table(output, 'table4_equal_dataset_means', equal_dataset_means(groups, [d['id'] for d in datasets]))
            write_table(output, 'table5_without_dapr', summarize_memberships(reduced))
        elif rq == 2:
            full = memberships(groups, datasets)
            write_table(output, 'membership', full)
            write_table(output, 'table6_dimensionality', summarize_memberships(full, by_tier=True))
            if args.without_dapr:
                reduced = memberships(groups, datasets, 'without_dapr')
                write_table(output, 'supplement_without_dapr_membership', reduced)
                write_table(output, 'supplement_without_dapr_tiers', summarize_memberships(reduced, by_tier=True))
        elif rq == 3:
            ranks, medians = [], []
            pools = range(1, max(len(d['knowledge_tracks']) for d in datasets) + 1)
            for expert in pools:
                ranks += memberships(groups, datasets, f'expert_{expert}', metrics=('d2h',))
                for dataset in datasets:
                    track = expert_track(dataset, expert)
                    hdkp = median(r['d2h'] for r in successful(groups, (dataset['id'], 'H-DKP', track)))
                    baseline = median(r['d2h'] for r in successful(groups, (dataset['id'], 'BS-LLM', '')))
                    medians.append(dict(pool=f'expert_{expert}', dataset=dataset['id'], expert_id=track,
                                        hdkp_median_d2h=hdkp, bs_llm_median_d2h=baseline,
                                        comparison='lower' if hdkp < baseline else 'higher' if hdkp > baseline else 'equal'))
            write_table(output, 'membership', ranks)
            write_table(output, 'table7_expert_best_group', summarize_memberships(ranks))
            write_table(output, 'expert_median_comparison', medians)
            for expert in pools:
                selected = [r for r in medians if r['pool'] == f'expert_{expert}']
                print(f"Expert {expert} H-DKP median vs BS-LLM: " + ', '.join(f"{kind}={sum(r['comparison'] == kind for r in selected)}" for kind in ('lower', 'equal', 'higher')))
            write_table(output, 'table1_expert_cohort', [dict(dataset=d['id'], display_name=d.get('display_name', d['id']),
                        feature_count=d['feature_count'], objective_count=d.get('objective_count'), tier=tier(d['feature_count']),
                        expert_tracks=len(d['knowledge_tracks'])) for d in datasets])
        else:
            from experiments.remaining_methods.run import METHOD_CALLS
            write_table(output, 'table2_amp_design', [dict(condition=m, analysis='Yes',
                        constraints='No' if m=='AMP-2' else 'Yes',
                        validation='Yes' if m=='AMP-4' else 'No', calls=METHOD_CALLS[m])
                        for m in ('AMP-2','AMP-3','AMP-4')])
            write_table(output, 'table8_operational_cost', cost_summary(groups))
            labeling = []
            for (dataset, method, expert_id), attempts in groups.items():
                values = [r['labeling_cost'] for r in attempts if r['status'] == 'success']
                available = bool(values) and all(v is not None for v in values)
                labeling.append(dict(dataset=dataset, method=method, expert_id=expert_id,
                                     successful_repeats=len(values), missing_labeling_cost=sum(v is None for v in values),
                                     mean=mean(values) if available else None,
                                     minimum=min(values) if available else None, maximum=max(values) if available else None))
            write_table(output, 'labeling_cost_by_dataset', labeling)
            if not metadata['complete']:
                print('Incomplete cohort: costs describe observed attempts only; inspect coverage.csv.')
    except (AnalysisError, OSError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(2, f'error: {exc}\n')
