"""Plan or execute fresh study trials. Planning never contacts a provider."""
import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from datasets import dataset_fingerprint
from study import METHODS, OPTIONAL_METHODS, PRIMARY_BUDGET, evaluation_budget, validate_budget, normalize_preparation
_INDICES = {}


def sha(path, normalize_newlines=False):
    content = Path(path).read_bytes()
    if normalize_newlines:
        content = content.replace(b'\r\n', b'\n')
    return hashlib.sha256(content).hexdigest()


def load_datasets():
    from datasets import load_datasets as load
    return load(ROOT)


def validate_inputs(manifest):
    checked = set()
    for item in manifest['automated'] + manifest['expert']:
        relative = item['path']
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f'Input escapes package: {relative}')
        if sha(path, normalize_newlines=True) != item['sha256']:
            raise ValueError(f'Dataset changed: {relative}')
        checked.add(relative)
    return len(checked)


def load_expert_rules(manifest, configuration, selected_datasets=None):
    """Load a researcher's own reviewed rules; never copy them into this repository."""
    configuration = Path(configuration).expanduser().resolve()
    supplied = json.loads(configuration.read_text())
    if not isinstance(supplied, dict):
        raise ValueError('Expert-rules configuration must map dataset IDs to track lists')
    available = {d['id']: d for d in manifest['expert']}
    if set(supplied) - set(available):
        raise ValueError('Expert-rules configuration contains unknown dataset IDs')
    selected = set(selected_datasets) if selected_datasets else set(available)
    for ident in selected:
        if ident not in available:
            raise ValueError(f'Unknown expert-study dataset: {ident}')
        tracks = supplied.get(ident, [])
        if not isinstance(tracks, list) or not 1 <= len(tracks) <= 2:
            raise ValueError(f'{ident}: supply one or two independently reviewed rule files')
        seen = set()
        prepared = []
        for track in tracks:
            ident_track = track.get('expert_id', '')
            if not re.fullmatch(r'[A-Za-z0-9_-]+', ident_track) or ident_track in seen:
                raise ValueError(f'{ident}: expert_id must be a unique simple identifier')
            seen.add(ident_track)
            path = Path(track['path']).expanduser()
            if not path.is_absolute():
                path = configuration.parent / path
            path = path.resolve()
            if not path.read_text().strip():
                raise ValueError(f'{ident}: reviewed rules must not be empty')
            entry = dict(expert_id=ident_track, path=str(path), sha256=sha(path))
            if 'preparation' in track:
                entry['preparation'] = normalize_preparation(track['preparation'])
            prepared.append(entry)
        available[ident]['knowledge_tracks'] = prepared


def make_jobs(manifest, cohort, methods, datasets=None):
    available = {d['id']: d for d in manifest[cohort]}
    selected = list(available) if datasets is None else datasets
    if set(selected) - set(available):
        raise ValueError('Unknown dataset ID')
    jobs = []
    for ident in selected:
        item = available[ident]
        for method in methods:
            evaluation_budget(method)
            if method == 'H-DKP':
                if not item.get('knowledge_tracks'):
                    raise ValueError(f'{ident}: H-DKP requires your own rules via --expert-rules')
                for track in item.get('knowledge_tracks', []):
                    jobs.append(dict(cohort=cohort, dataset=ident, method=method,
                                     expert_id=track['expert_id'], input=item, knowledge=track))
            else:
                jobs.append(dict(cohort=cohort, dataset=ident, method=method,
                                 expert_id='', input=item, knowledge=None))
    return jobs


def call_limit(job, repair=False):
    method = job['method']
    evaluation_budget(method)
    n = {'Random': 0, 'EZR': 0, 'RRP': 0, 'BS-LLM': 1, 'SynthCore-28': 3,
         'AMP-2': 2, 'AMP-3': 3, 'AMP-4': 7, 'H-DKP': 1,
         'HKMA-scout': 2, 'HKMA-rag': 1, 'HKMA-combined': 2}.get(method)
    if repair and method in ('AMP-2', 'AMP-3'):
        n += 2
    if repair and method.startswith('HKMA-'):
        n += 1
    return n


def token_usage(directory, calls):
    """Missing provider charges stay null; failed calls are never free by assumption."""
    responses = sorted(directory.glob('call_*.response.json'))
    fields = {'input_tokens': 'prompt_tokens', 'output_tokens': 'completion_tokens',
              'total_tokens': 'total_tokens', 'api_cost_usd': 'cost'}
    result = {'llm_calls': calls}
    for output, source in fields.items():
        values = [(json.loads(p.read_text()).get('usage') or {}).get(source) for p in responses]
        result[output] = (sum(values) if len(responses) == calls and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            for v in values) else None)
    if calls == 0:
        result.update({name: 0 for name in fields})
    if all(result[x] is not None for x in ('input_tokens', 'output_tokens', 'total_tokens')):
        if result['input_tokens'] + result['output_tokens'] != result['total_tokens']:
            raise ValueError('Provider token totals disagree')
    return result


def run_trial(job, directory, seed, model, repair=False):
    """Dispatch to the retained study implementations, using the selected study dataset."""
    from src.utils.ezr import DATA, csv, d2h, chebyshev, the
    from experiments.evaluation import run
    method, item = job['method'], job['input']
    budget = evaluation_budget(method)
    path = ROOT / item['path']
    data = DATA(csv(str(path)))
    the.Last, the.label, the.GuessFaster = budget, 4, True
    random.seed(seed)
    metadata = dict(dataset_path=str(path.relative_to(ROOT)), dataset_sha256=sha(path, normalize_newlines=True),
                    actual_feature_count=len(data.cols.x))
    if method == 'Random':
        indices = random.sample(range(len(data.rows)), budget)
        row = min((data.rows[ix] for ix in indices), key=lambda r: d2h(data, r))
        result = dict(selected_row=list(row), evaluated_row_indices=indices,
                      oracle_evaluations=budget, nominal_labeling_budget=budget,
                      labeling_cost=len({tuple(data.rows[ix]) for ix in indices}))
    elif method == 'EZR':
        result = run.optimize(data, None, budget, seed, 'equal-oracle')
        row = result['selected_row']
    elif method == 'RRP':
        result = run.rrp(data, budget)
        row = result['selected_row']
    elif method == 'SynthCore-28':
        from src.models.synthcore import run_ensemble, SOURCE
        _, audit, rows = run_ensemble(data, model, SOURCE, seed)
        row = rows[0]
        result = dict(selected_row=list(row),
                      labeling_cost=audit['objective_access']['unique_scored_rows'],
                      labeling_count_basis='distinct full observed-row tuples scored during the ensemble',
                      nominal_labeling_budget=budget,
                      oracle_evaluations=audit['evaluation_requests'],
                      initial_representatives=audit['initial_representatives'],
                      generation_sessions=len(audit['sessions']),
                      selection_metric='d2h', downstream_smo=False,
                      objective_access=audit['objective_access'])
        (directory/'synthcore_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    else:
        if method.startswith('HKMA-'):
            from experiments.evaluation.hkma import HKMA, CorpusIndex
            corpus_root = ROOT/item['corpus_root']
            index = None
            if method != 'HKMA-scout':
                index_key = (str(corpus_root), item['corpus_dataset_id'])
                if index_key not in _INDICES:
                    _INDICES[index_key] = CorpusIndex(corpus_root, item['corpus_dataset_id'])
                index = _INDICES[index_key]
            hkma_strategy = HKMA(data, method, model, ROOT/item['corpus_root'],
                              item['corpus_dataset_id'], index=index)
            generate = hkma_strategy.generate
            scout = hkma_strategy.scout if method != 'HKMA-rag' else None
            if repair:
                generate = run.with_one_generation_repair(data, method, model, generate)
        else:
            knowledge = ROOT/job['knowledge']['path'] if job['knowledge'] else None
            generate = run.make_generator(data, 'LLM' if method == 'BS-LLM' else method, model, path, str(knowledge) if knowledge else None)
            scout = None
            if repair and method in ('AMP-2', 'AMP-3'):
                from experiments.evaluation.amp_retry import with_fresh_amp_generation_repair
                generate = with_fresh_amp_generation_repair(data, method, model, generate)
        result = run.optimize(data, generate, budget, seed, 'equal-oracle', scout=scout)
        row = result['selected_row']
    if 'evaluated_row_indices' in result:
        result['labeling_cost'] = len({tuple(data.rows[ix]) for ix in result['evaluated_row_indices']})
    validate_budget(method, result)
    result.update(d2h=d2h(data, row), chebyshev=chebyshev(data, row), **metadata)
    return result


def identity(row):
    return tuple(row[k] for k in ('cohort', 'dataset', 'method', 'expert_id', 'rep'))


def execute(jobs, args, manifest):
    from experiments.evaluation.run import LoggedModel
    import fcntl
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    # The study algorithms mutate global settings; execute serially and reject concurrent writers.
    with (output/'.lock').open('a') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another process is writing this run directory')
        config = dict(datasets_sha256=dataset_fingerprint(manifest), runner_sha256=sha(Path(__file__)),
                      repeats=args.repeats,
                      seed=args.seed, repair_invalid=args.repair_invalid, model=manifest['model'],
                      per_call_transport_retries=0,
                      external_rule_hashes={j['dataset']+'/'+j['expert_id']: j['knowledge']['sha256']
                                            for j in jobs if j['knowledge']},
                      external_preparation={j['dataset']+'/'+j['expert_id']: j['knowledge'].get('preparation')
                                            for j in jobs if j['knowledge']})
        config_path = output/'config.json'
        if config_path.exists():
            previous = json.loads(config_path.read_text())
            external = ('external_rule_hashes', 'external_preparation')
            if {k:v for k,v in previous.items() if k not in external} != {k:v for k,v in config.items() if k not in external}:
                raise ValueError('Run configuration changed; select a new output directory')
            # Add new expert tracks after comparators, preserving every existing
            # frozen rule identity and its one-time preparation measurements.
            for field in external:
                existing_values = previous.get(field, {})
                added_values = config[field]
                if any(existing_values[key] != value for key, value in added_values.items() if key in existing_values):
                    raise ValueError('Frozen expert rules or preparation configuration changed; select a new output directory')
                config[field] = {**existing_values, **added_values}
        config_path.write_text(json.dumps(config, indent=2)+'\n')
        ledger = output/'trials.jsonl'
        existing = [json.loads(x) for x in ledger.read_text().splitlines() if x.strip()] if ledger.exists() else []
        completed = {identity(r) for r in existing if r['status'] == 'success'}
        failures = 0
        for job in jobs:
            for rep in range(args.repeats):
                base = {k: job[k] for k in ('cohort', 'dataset', 'method', 'expert_id')}
                base.update(rep=rep, feature_count=job['input']['feature_count'])
                if job['knowledge']:
                    base['rules_sha256'] = job['knowledge']['sha256']
                    if 'preparation' in job['knowledge']:
                        base['preparation'] = job['knowledge']['preparation']
                key = identity(base)
                if key in completed:
                    continue
                attempts = [r for r in existing if identity(r) == key]
                if attempts and not args.retry_failed:
                    failures += 1
                    continue
                attempt = len(attempts)
                directory = output/'attempts'/job['cohort']/job['dataset']/job['method']/(job['expert_id'] or 'baseline')/f'rep_{rep:02d}_attempt_{attempt:02d}'
                if directory.exists():
                    raise ValueError(f'Interrupted attempt preserved at {directory}; inspect before continuing')
                directory.mkdir(parents=True)
                seed = args.seed + rep + int(hashlib.md5(Path(job['input']['path']).name.encode()).hexdigest()[:8],16)%1000000 + attempt*1000003
                # Explicit reasoning settings for each generation method.
                effort = 'low' if job['method'] in ('AMP-2','AMP-3','SynthCore-28') or job['method'].startswith('HKMA-') else None
                model = LoggedModel(directory, seed, call_limit(job, args.repair_invalid), reasoning_effort=effort)
                base.update(seed=seed, attempt=attempt, repair_invalid=args.repair_invalid,
                            reasoning_effort=effort)
                start = time.monotonic()
                try:
                    with (directory/'local_output.txt').open('w') as local, contextlib.redirect_stdout(local):
                        result = run_trial(job, directory, seed, model, args.repair_invalid)
                    row = {**base, **result, 'status': 'success'}
                except Exception as error:
                    row = {**base, 'status': 'failed', 'error_type': type(error).__name__}
                    failures += 1
                row.update(wall_seconds=time.monotonic()-start,
                           **token_usage(directory, model.calls))
                (directory/'result.json').write_text(json.dumps(row, indent=2, allow_nan=False)+'\n')
                with ledger.open('a') as stream:
                    stream.write(json.dumps(row, allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno())
                existing.append(row)
                print(f"{job['cohort']} {job['dataset']} {job['method']} {job['expert_id']} repeat {rep}: {row['status']}", flush=True)
        print(f'Trial ledger: {ledger}; failed/preserved attempts: {failures}')
        return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', choices=('automated','expert'), default='automated')
    parser.add_argument('--datasets', nargs='+', help='Dataset IDs; default all in cohort')
    parser.add_argument('--methods', nargs='+', choices=METHODS+OPTIONAL_METHODS+('H-DKP',))
    parser.add_argument('--expert-rules', type=Path, help='External JSON mapping dataset IDs to your own reviewed rule files')
    parser.add_argument('--repeats', type=int, default=20)
    parser.add_argument('--seed', type=int, default=12345)
    parser.add_argument('--output', default=str(ROOT/'results/fresh'))
    parser.add_argument('--execute', action='store_true', help='Execute trials; otherwise print a plan')
    parser.add_argument('--allow-paid', action='store_true', help='Explicitly enable requests for LLM methods')
    parser.add_argument('--retry-failed', action='store_true', help='Make a new attempt after a recorded failure')
    parser.add_argument('--repair-invalid', action='store_true', help='Enable the retained bounded correction helpers; counted calls')
    args = parser.parse_args(argv)
    if args.repeats < 1 or args.repeats > 20:
        parser.error('repeats must be 1..20')
    methods = args.methods or list(METHODS)+(['H-DKP'] if args.cohort=='expert' and args.expert_rules else [])
    if args.cohort=='automated' and 'H-DKP' in methods:
        parser.error('H-DKP belongs to the expert cohort')
    if len(set(methods)) != len(methods):
        parser.error('methods must be unique')
    manifest=load_datasets(); checked=validate_inputs(manifest)
    if args.expert_rules and args.cohort != 'expert':
        parser.error('--expert-rules is for the expert cohort')
    if args.expert_rules:
        load_expert_rules(manifest, args.expert_rules, args.datasets)
    jobs=make_jobs(manifest,args.cohort,methods,args.datasets)
    calls=args.repeats*sum(call_limit(j,args.repair_invalid) for j in jobs)
    plan=dict(methods=methods, cohort=args.cohort,datasets=len({j['dataset'] for j in jobs}),jobs=len(jobs),
              repeats=args.repeats,maximum_model_calls=calls,verified_dataset_files=checked,
              evaluation_budgets={m:evaluation_budget(m) for m in methods},
              model=manifest['model'],repair_invalid=args.repair_invalid,
              retrieval_model=manifest['embedding'],execute=args.execute)
    print(json.dumps(plan,indent=2))
    if not args.execute:
        return 0
    if calls and not args.allow_paid:
        parser.error('LLM execution requires --allow-paid; planning and model-free methods do not')
    if calls and not os.environ.get('OPENROUTER_API_KEY'):
        parser.error('Set OPENROUTER_API_KEY in the environment for paid execution')
    return execute(jobs,args,manifest)


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except ValueError as exc:
        raise SystemExit(str(exc))
