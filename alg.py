from math import log
from read import Read
from graph import Graph
from random import choice
from copy import copy
from itertools import permutations
from typing import Dict, List, NamedTuple


CONFIDENCE = 0.5


class Phase(NamedTuple):
    haplotypes: List[Dict[int, int]]  # A (SNP ID -> Allele) dict for each haplotype
    score: float


def read_val_tail(
    haplotypes: List[Dict[int, int]],
    pair_threshold: float,
    error: float,
    relevant_reads: List[Read],
    last_snp: int,
    prev_snp: int
) -> float:
    """
    we extend a phasing and then calculating how likely that extension is
    this looks at the prob of a particular phasing generating the Set of reads
    which cover "end" ( = "last_snp") and for which "end" is not the smallest SNP
    in the read (relevant reads for the extension).
    this log prob gets added to the log prob of the non-extended phasing.
    """

    a = (1 - error) / (1 - (2 * error / 3.0))
    b = (error / 3.0) / (1 - (2 * error / 3.0))
    val, val2 = 0.0, 0.0
    for read in relevant_reads:
        probs, probs2 = 0.0, 0.0
        for hi, haplo in enumerate(haplotypes):
            prob = (CONFIDENCE * read.rates[hi]) + (0.5 * (1 - CONFIDENCE))
            for snp in read.snps:
                if snp <= last_snp:
                    prob *= (a if read.snps[snp] == haplo[snp] else b)
            probs2 += prob / (a if read.snps[last_snp] == haplo[last_snp] else b)
            probs += prob
        if probs == 0:
            val = -float("inf")
        else:
            val += log(probs) * read.count
            if not last_snp == read.special_snp:
                val2 += log(probs2) * read.count

    # pair_threshold is some measure of likelihood of adjacent mutations occuring \
    # together since we've know extended the haplotype we need to update the prior
    if len(haplotypes[0]) > 1:
        assert prev_snp != -1
        val += log(
            pair_threshold
            if haplotypes[0][last_snp] == haplotypes[0][prev_snp]
            else (1 - pair_threshold)
        )
    return val - val2


def branch(
    phases: List[Phase],
    snp: int,
    prev_snp: int,
    relevant_reads: List[Read],
    threshold: float,
    pair_threshold: float,
    error: float,
    ploidy: int
) -> List[Phase]:
    """
    Branch all solutions to highly probable solutions on one additional SNP
    lists include all current solutions.
    """

    new_phases = []
    configs = list(permutations(range(ploidy))), 
    costs = [0.0] * len(configs)
    for partial, score in phases:
        for i, config in enumerate(configs):
            for j in len(config):
                partial[j][snp] = config[j]
            costs[i] = read_val_tail(
                partial, pair_threshold, error, relevant_reads, snp, prev_snp
            )
        t, used = threshold + max(costs), False
        for i, config in enumerate(configs):
            if costs[i] >= t:
                extended = partial
                if used:
                    extended = [copy(partial[0]), copy(partial[1])]
                else:
                    used = True
                for j in len(config):
                    extended[j][snp] = config[j]
                new_phases.append(Phase(extended, score - costs[i]))
    return new_phases


def prune(
    phases: List[Phase],
    is_last: bool
) -> List[Phase]:
    # prune solutions based on number of solutions and thresholds
    threshold = 1.0
    if is_last:
        threshold = 1.0
    elif len(phases) > 1000:
        threshold = 0.1
    elif len(phases) > 500:
        threshold = 0.05
    elif len(phases) > 100:
        threshold = 0.01
    else:
        threshold = 0.001
    threshold = abs(log(threshold)) + 0.0001

    min_val = min(p.score for p in phases)
    nphases = [p for p in phases if abs(p.score - min_val) < threshold]
    if is_last:
        nphases = [choice(nphases)]
    return nphases


def parallel(
    graph: Graph,
    root: int,
    threshold: float,
    pair_threshold: float,
    error: float,
    allow_allele_permutations: bool = True
) -> Phase:
    phases = [Phase([{}] * graph.ploidy, 0.0)]
    skipped = True  # set to allow allele permutations
    prev_snp = -1
    for snp in graph.components[root].nodes:
        if allow_allele_permutations:
            phases = branch(
                phases, snp, prev_snp, graph.snp_reads[snp], threshold, pair_threshold,
                error, graph.ploidy
            )
            phases = prune(phases, snp == graph.components[root].nodes[-1])
        else:  # specify beginning to remove allele permutations
            allow_allele_permutations = True
        prev_snp = snp
    return phases[0]


def phase(
    graph: Graph,
    threshold: float,
    pair_threshold: float,
    error: float
) -> Dict[int, Phase]:
    threshold = log(threshold / (1 - threshold))
    print(f'Phasing {len(graph.components)} components...')
    result = {}
    for root in graph.components:
        result[root] = parallel(graph, root, threshold, pair_threshold, error)
    return result
