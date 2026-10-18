"""Recursive Scott--Knott partitioning with bootstrap and Cliff effect gates.

Order methods by sample mean and maximize between-group sum of squares.
Accept a split only when BOTH |delta| >= .147 and bootstrap p < .05.
Bootstrap uses a pooled-mean null and a studentized difference of means.
No Cohen gate, KS test, or leader-only admission rule is applied.
"""
import numpy as np


def cliffs_delta(x, y):
    x, y = np.asarray(x), np.sort(y)
    less = np.searchsorted(y, x, side='left').sum()
    greater = (len(y) - np.searchsorted(y, x, side='right')).sum()
    return float((less-greater)/(len(x)*len(y)))


def bootstrap_p(x, y, rng, samples=512):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    def statistic(a, b, axis=None):
        diff = np.abs(a.mean(axis=axis)-b.mean(axis=axis))
        scale = np.sqrt(a.var(axis=axis, ddof=1)/a.shape[-1]
                        + b.var(axis=axis, ddof=1)/b.shape[-1])
        return diff/(scale+1e-30)
    observed = statistic(x, y)
    if observed == 0:
        return 1.0
    pooled_mean = (x.sum()+y.sum())/(len(x)+len(y))
    xnull, ynull = x-x.mean()+pooled_mean, y-y.mean()+pooled_mean
    a = rng.choice(xnull, size=(samples,len(x)), replace=True)
    b = rng.choice(ynull, size=(samples,len(y)), replace=True)
    statistics = statistic(a,b,axis=1)
    # Add-one correction prevents a simulated p-value of zero.
    return float((1+np.count_nonzero(statistics >= observed))/(samples+1))


def rank_methods(samples, seed, bootstrap_samples=512, alpha=.05, delta=.147):
    ordered = sorted(samples, key=lambda m: (np.mean(samples[m]), m))
    rng = np.random.default_rng(seed)
    ranks = {}
    def divide(methods, rank):
        if len(methods) == 1:
            ranks[methods[0]] = rank
            return rank
        all_values = np.concatenate([samples[m] for m in methods])
        overall = all_values.mean()
        candidates = []
        for cut in range(1,len(methods)):
            left = np.concatenate([samples[m] for m in methods[:cut]])
            right = np.concatenate([samples[m] for m in methods[cut:]])
            gain = len(left)*(left.mean()-overall)**2 + len(right)*(right.mean()-overall)**2
            candidates.append((gain,cut,left,right))
        gain,cut,left,right = max(candidates,key=lambda item:item[0])
        if gain > 0 and abs(cliffs_delta(left,right)) >= delta:
            if bootstrap_p(left,right,rng,bootstrap_samples) < alpha:
                last = divide(methods[:cut],rank)
                return divide(methods[cut:],last+1)
        for method in methods:
            ranks[method]=rank
        return rank
    divide(ordered,0)
    return ranks
