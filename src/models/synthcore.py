"""Pinned SynthCore Diversity ensemble used by the current paper.

Upstream commit eaec7012a1928c36e73ffcf7ec894c5e3e28bfe3 (clusters).
The upstream ensemble, partitioning and prompt definitions below are executed
unchanged. Provider transport, feature-column projection, numeric parsing and
removal of the unconditional sleep match the study adapter. No downstream SMO.
"""
import ast
import math
from pathlib import Path
import random
from types import SimpleNamespace
from src.utils import ezr

SOURCE = Path(__file__).with_name('_synthcore_upstream')

def extract(path, names, namespace):
    tree = ast.parse(Path(path).read_text())
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    if {n.name for n in nodes} != set(names):
        raise ValueError(f'Missing pinned functions in {path}: {set(names) - {n.name for n in nodes}}')
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)

def parse_markdown(data, text):
    """Upstream positional/class parser, with numeric and c.at portability fixes.

    Preserve upstream removal of first header and second separator lines, exact
    Best/Rest labels, permissive row counts (including zero), unknown symbolic
    tokens, and Best-then-Rest output ordering. Do not repair or reprompt.
    """
    if not isinstance(text, str):
        raise ValueError('Provider returned no text')
    lines = text.strip().split('\n')
    if len(lines) < 2:
        raise ValueError('Upstream markdown parser requires at least two lines')
    lines.pop(1)
    records = [[value.strip() for value in line.strip('|').split('|')] for line in lines][1:]
    best, rest = [], []
    for values in records:
        if values[-1] not in ('Best', 'Rest'):
            continue
        if len(values) - 1 < len(data.cols.x):
            raise ValueError('Generated class row has too few feature positions')
        full = ['?'] * len(data.cols.names)
        for c, value in zip(data.cols.x, values[:-1]):
            if value == '?':
                parsed = '?'
            elif c.this is ezr.NUM:
                try:
                    parsed = float(value)
                except ValueError:
                    raise ValueError(f'Non-numeric generated value for {c.txt}')
                if not math.isfinite(parsed):
                    raise ValueError(f'Non-finite generated value for {c.txt}')
            else:
                # Preserve upstream numeric coercion even in symbolic columns.
                # Other, possibly unseen, symbolic values remain unchanged.
                parsed = float(value) if value.replace('.', '', 1).isdigit() else value
            full[c.at] = parsed
        (best if values[-1] == 'Best' else rest).append(full)
    return best + rest

def run_ensemble(data, model, source, seed, leaf_override=None):
    """Return scores of upstream selected row, selection audit, and ranked pool."""
    random.seed(seed)
    namespace = dict(vars(ezr))
    # Upstream depth-based dendogram is not the local size-threshold variant.
    extract(source / 'src/utils/ezr.py', ['dendogram', 'leafs'], namespace)
    extract(source / 'src/prompts/synthetic.py', ['rows_to_markdown', 'SYNTHETIC'], namespace)
    extract(source / 'src/models/warm_start.py', ['warm_smo_plus'], namespace)
    counts = {'d2h_calls': 0, 'chebyshev_calls': 0}
    unique = set()
    def measured(name, fn):
        def wrapped(i, row):
            counts[name + '_calls'] += 1
            unique.add(tuple(row))
            return fn(i, row)
        return wrapped
    namespace['d2h'] = measured('d2h', ezr.d2h)
    namespace['chebyshev'] = measured('chebyshev', ezr.chebyshev)
    namespace['DATA'] = lambda _: data
    namespace['csv'] = lambda _: None
    if leaf_override:
        namespace['leafs'] = leaf_override
    audit = {'sessions': []}
    def warm(i, args, todo, done, method='LLM', iscombined=True):
        random.shuffle(i.rows)
        done = sorted(done, key=lambda row: namespace['d2h'](i,row))
        cut = int(.5 + len(done) ** .5)
        # Preserve upstream prompt prose but project features by actual columns.
        prompt = namespace['SYNTHETIC'](i, [], [])
        prompt.best = [[r[c.at] for c in i.cols.x] for r in done[:cut]]
        prompt.rest = [[r[c.at] for c in i.cols.x] for r in done[cut:]]
        prompt.x, prompt.dff = len(i.cols.x), 0
        # get_template_markdown reads i.cols.names[:x]; use a shallow schema view
        # so feature names remain correct when objective/ignored cols interleave.
        prompt.i = SimpleNamespace(cols=SimpleNamespace(names=[c.txt for c in i.cols.x], x=i.cols.x))
        messages = [{'role':'user' if role == 'human' else role, 'content':content}
                    for role, content in prompt.get_template_markdown()]
        generated = parse_markdown(i, model.invoke(messages).content)
        new = []
        for record in generated:
            random.shuffle(todo)
            todo = sorted(todo, key=lambda row: ezr.dists(i,record,row))
            if not todo:
                raise ValueError('Observed candidate pool exhausted')
            new.append(todo.pop(0))
        combined = sorted(done + new, key=lambda row: namespace['d2h'](i,row))
        retained = [combined[0],combined[1],combined[-1],combined[-2]] if iscombined else new
        audit['sessions'].append({'initial':done, 'generated':generated,'generated_count':len(generated),'mapped':new,'retained':retained,
                                  'warning':None if len(generated)==4 else f'Upstream parser accepted {len(generated)} generated rows'})
        return done,retained,todo
    namespace['WARM_FEW_API'] = warm
    rows = namespace['warm_smo_plus'](SimpleNamespace(dataset='',llm='openrouter/openai/gpt-oss-120b'), method='LLM',start='Diversity')
    counts['unique_scored_rows'] = len(unique)
    audit['objective_access'] = counts
    scores = {'d2h': ezr.d2h(data,rows[0]),'chebyshev':ezr.chebyshev(data,rows[0])}
    return scores,audit,rows
