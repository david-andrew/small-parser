"""
TBD implementation of GLL parser
should be the go-to approach for general regex/parsing needs
"""
from grammar import NonTerminal, Terminal, Sentence, Slot, Grammar
from trees import BSR, bsr_tree_str, find_roots, extractSPPF, sppf_tree_str


# def dedup(l:list) -> list:
#     return list(dict.fromkeys(l))


#implementation of the functional GLL parsing process from https://pure.royalholloway.ac.uk/portal/files/35434658/Accepted_Manuscript.pdf
#TODO: maybe look into the parsing combinators that they also discuss in the paper-->future work

#TODO: replace tau:str with tau:Sequence[T] where T could be strings, or any other token type


import pdb

#TODO: quality of life EBNF/notation for specifying grammar rules. probably put in a different file
# class MAST(ABC): ... #perhaps this should just be grammar? or something
# class EBNF(ABC): ... #this is the higher level grammar with extra notation


Commencement = tuple[NonTerminal, int]      #(X:NonTerminal, l:int)
Continuation = tuple[Slot, int]             #(g:Slot, l:int)
Descriptor = tuple[Slot, int, int]          #(g:Slot, l:int, k:int)


"""
Definitions:
  W:list[Descriptor]                        - worklist of descriptors. paper uses 𝓡, but replaced with W to avoid confusion with R for the set of right extents. TODO: replace with unicode R that doesn't decompose to U+0052
  R:set[int]                                - set of right extents
  U:set[Descriptor]                         - set that stores all the descriptors that have been added to the worklist previously. ensures no descriptor is added to worklist twice
  P:set[tuple[Commencement, int]]           - set of relations that records for all nonterminals the left and right extents that have been discovered so far
  G:set[tuple[Commencement, Continuation]]  - set of relations between commencements and continuations
  Y:set[BSR]                                - set of all BSRs that have been discovered so far. Records the parse forest for the sentence
"""


def fungll(Gamma:Grammar, tau:str, X:NonTerminal) -> tuple[set[Descriptor], set[BSR]]:
    return loop(Gamma, tau, descend(Gamma, X, 0), set(), set(), set(), set())


def descend(Gamma:Grammar, X:NonTerminal, l:int) -> list[Descriptor]:
    return [(Slot(X, rule, 0), l, l) for rule in Gamma.rules[X]]


def loop(Gamma:Grammar, tau:str, W:list[Descriptor], U:set[Descriptor], G:set[tuple[Commencement,Continuation]], P:set[tuple[Commencement, int]], Y:set[BSR]) -> tuple[set[Descriptor], set[BSR]]:
    if not W: return U, Y
    d = W[0]
    (Wp,Yp), Gp, Pp = process(Gamma, tau, d, G, P)
    Wpp = [r for r in W+Wp if r not in U|{d}] #is Wp guaranteed to be disjoint from W? otherwise we'd need to filter for duplicates...
    return loop(Gamma, tau, Wpp, U|{d}, G|Gp, P|Pp, Y|Yp)


def process(Gamma:Grammar, tau:str, d:Descriptor, G:set[tuple[Commencement,Continuation]], P:set[tuple[Commencement, int]]) -> tuple[tuple[list[Descriptor], set[BSR]], set[tuple[Commencement, Continuation]], set[tuple[Commencement, int]]]:
    g, l, k = d
    if len(g.beta) == 0:
        return process_eps(d, G, P)

    return process_sym(Gamma, tau, d, G, P)


def process_eps(d:Descriptor, G:set[tuple[Commencement, Continuation]], P:set[tuple[Commencement, int]]) -> tuple[tuple[list[Descriptor], set[BSR]], set[tuple[Commencement, Continuation]], set[tuple[Commencement, int]]]:
    g, l, k = d
    key = (g.X, l)
    K: set[Continuation] = {c for (cm, c) in G if cm == key}
    W, Y = ascend(k, K, k)                  # see bug #2 below
    Yp = {(g, l, l, l)} if len(g.rule) == 0 else set()
    return (W, Y | Yp), set(), {((g.X, l), k)}


def process_sym(Gamma:Grammar, tau:str, d:Descriptor, G:set[tuple[Commencement,Continuation]], P:set[tuple[Commencement, int]]) -> tuple[tuple[list[Descriptor], set[BSR]], set[tuple[Commencement, Continuation]], set[tuple[Commencement, int]]]:
    g, l, k = d
    s = g.s
    if isinstance(s, Terminal):
        return (match(tau, d), set(), set())

    assert isinstance(s, NonTerminal), f'Expected NonTerminal, got {s}'
    Gp = {((s,k),(g.next(), l))}
    R = {r for ((_s,_k),r) in P if _k==k and _s==s}

    if len(R) == 0:
        return ((descend(Gamma, s, k),set()), Gp, set())

    return (skip(k, (g.next(), l), R), Gp, set())


def match(tau:str, d:Descriptor) -> tuple[list[Descriptor], set[BSR]]:
    g, l, k = d
    assert isinstance(g.s, Terminal), f'Cannot match because {g.s} is not a terminal.'
    if k < len(tau) and tau[k] == g.s.t:
        new_g = g.next()
        return ([(new_g,l,k+1)], {(new_g,l,k,k+1)})
    else:
        return ([], set())


def skip(k:int, c:Continuation, R:set[int]) -> tuple[list[Descriptor], set[BSR]]:
    return nmatch(k, {c}, R)


def ascend(k:int, K:set[Continuation], r:int) -> tuple[list[Descriptor], set[BSR]]:
    return nmatch(k, K, {r})


def nmatch(k:int, K:set[Continuation], R:set[int]) -> tuple[list[Descriptor], set[BSR]]:
    W: list[Descriptor] = []
    Y: set[BSR] = set()
    for c in K:
        g, l = c
        for r in R:
            if k < l: continue#raise Exception(f'k ({k}) must be equal to or larger than l ({l})')
            if k > r: continue#raise Exception(f'k ({k}) must be equal to or smaller than r ({r})')
            W.append((g, l, r))
            Y.add((g, l, k, r))
    return W, Y


def complete_parser_for(Gamma:Grammar, X:NonTerminal):
    def parse(tau:str):
        U, Y = fungll(Gamma, tau, X)
        return Y
    return parse



#tasks
# check if a parse was a success by finding the top level BSR node
# nice printing of BSR
# seq[T] instead of str for tau


def parse_str(Y:set[BSR]):
    s = [f'    ({g}, {l}, {k}, {r})\n' for g, l, k, r in Y]
    return '{\n' + ''.join(s) + '}'


# for debugging
def check_invariants(Y, n):
    ok = True
    for g,l,k,r in Y:
        if not (0 <= l <= k <= r <= n):
            print("BAD:", (g,l,k,r))
            ok = False
    if ok:
        print("Invariants OK.")






if __name__ == '__main__':

    # trivial literal
    S = NonTerminal('S'); G = Grammar()
    G.add_rule(S, Sentence((Terminal('h'), Terminal('i'))))
    parse = complete_parser_for(G, S)
    inp = 'hi'; Y = parse(inp)
    print('roots:', parse_str(find_roots(S, Y, len(inp))))
    check_invariants(Y, len(inp))


    # pure epsilon
    S = NonTerminal('S'); G = Grammar()
    G.add_rule(S, Sentence())   # epsilon
    parse = complete_parser_for(G, S)
    for inp in ['', 'x']:
        Y = parse(inp)
        print(inp, parse_str(find_roots(S, Y, len(inp))))
        check_invariants(Y, len(inp))


    # left recursion, nullable
    E = NonTerminal('E'); G = Grammar()
    G.add_rule(E, Sentence((E, E, E)))
    G.add_rule(E, Sentence((Terminal('1'),)))
    G.add_rule(E, Sentence())
    parse = complete_parser_for(G, E)
    for inp in ['', '1']:
        Y = parse(inp)
        print(inp, parse_str(find_roots(E, Y, len(inp))))
        check_invariants(Y, len(inp))


    # Balanced parens with ε
    P = NonTerminal('P'); G = Grammar()
    G.add_rule(P, Sentence((Terminal('('), P, Terminal(')'), P)))
    G.add_rule(P, Sentence())
    parse = complete_parser_for(G, P)
    for inp in ['', '()', '()()', ')(']:
        Y = parse(inp)
        print(inp, parse_str(find_roots(P, Y, len(inp))))
        check_invariants(Y, len(inp))


    # Simple repetition (Kleene-like, nullable)
    A = NonTerminal('A'); G = Grammar()
    G.add_rule(A, Sentence((Terminal('a'), A)))
    G.add_rule(A, Sentence())
    parse = complete_parser_for(G, A)
    for inp in ['', 'a', 'aaa', 'b']:
        Y = parse(inp)
        print(inp, parse_str(find_roots(A, Y, len(inp))))
        check_invariants(Y, len(inp))


    # Small local ambiguity
    S = NonTerminal('S'); G = Grammar()
    G.add_rule(S, Sentence((Terminal('a'),)))
    G.add_rule(S, Sentence((Terminal('a'), Terminal('a'))))
    parse = complete_parser_for(G, S)
    for inp in ['a', 'aa']:
        Y = parse(inp)
        print(inp, parse_str(find_roots(S, Y, len(inp))))
        check_invariants(Y, len(inp))


    exit(1)



    # # super simple test grammar S ::= 'h' 'e' 'l' 'l' 'o'
    # S = NonTerminal('S')
    # G = Grammar()
    # G.add_rule(S, Sentence((Terminal('h'), Terminal('e'), Terminal('l'), Terminal('l'), Terminal('o'))))

    # parse = complete_parser_for(G, S)
    # print('------------------------------------------------------------')
    # print(G)
    # input = 'hello'
    # print(f'input: {input}')
    # result = parse(input)
    # print(parse_str(result))
    # roots = find_roots(S, result, input)
    # print(f'roots: {parse_str(roots)}')
    # print(f"bsr tree: {bsr_tree_str(result, input)}")
    # sppf = extractSPPF(result, G)
    # print(f'sppf: {sppf}')
    # print(sppf_tree_str(sppf, G, input))


    # test with example from the paper
    # Tuple ::= '(' As ')'
    # As ::= ϵ | a' More
    # More ::= ϵ | ',' 'a' More
    Tuple = NonTerminal('Tuple')
    As = NonTerminal('As')
    More = NonTerminal('More')
    G = Grammar()
    G.add_rule(Tuple, Sentence((Terminal('('), As, Terminal(')'))))
    G.add_rule(As, Sentence((Terminal('a'), More)))
    G.add_rule(As, Sentence())
    G.add_rule(More, Sentence((Terminal(','), Terminal('a'), More)))
    G.add_rule(More, Sentence())

    parse = complete_parser_for(G, Tuple)
    print('------------------------------------------------------------')
    print(G)
    input = '(a,a)'
    print(f'input: {input}')
    result = parse(input)
    print(parse_str(result))
    roots = find_roots(Tuple, result, len(input))
    print(f'roots: {parse_str(roots)}')
    print(f"bsr tree: {bsr_tree_str(Tuple, result, len(input))}")
    sppf = extractSPPF(result, G)
    print(f'sppf: {sppf}')
    print(sppf_tree_str(sppf, G, input))

    exit(1)


    # test with example from paper: E ::= E E E | "1" | eps
    E = NonTerminal('E')
    G = Grammar()
    G.add_rule(E, Sentence((E,E,E)))
    G.add_rule(E, Sentence((Terminal('1'),)))
    G.add_rule(E, Sentence())

    parser = complete_parser_for(G, E)
    print('------------------------------------------------------------')
    print(G)
    input = '1'
    print(f'input: {input}')
    result = parser(input)
    print(parse_str(result))
    roots = find_roots(E, result, input)
    print(f'roots: {parse_str(roots)}')
    print(f"bsr tree: {bsr_tree_str(E, result, input)}")
    sppf = extractSPPF(result, G)
    print(f'sppf: {sppf}')
    print(sppf_tree_str(sppf, G, input))


    # custom test example
    #S = 'a' | 'b' #B #S #S | ϵ;
    #B = ϵ;
    S = NonTerminal('S')
    B = NonTerminal('B')
    G = Grammar()
    G.add_rule(S, Sentence((Terminal('a'),)))
    G.add_rule(S, Sentence((Terminal('b'), B, S, S,)))
    G.add_rule(S, Sentence())
    G.add_rule(B, Sentence())

    parser = complete_parser_for(G, S)
    print('------------------------------------------------------------')
    print(G)
    input = 'bb'
    print(f'input: {input}')
    result = parser(input)
    print(parse_str(result))
    roots = find_roots(S, result, input)
    print(f'roots: {parse_str(roots)}')
    print(f"bsr tree: {bsr_tree_str(S, result, input)}")
    sppf = extractSPPF(result, G)
    print(f'sppf: {sppf}')
    print(sppf_tree_str(sppf, G, input))


    #simple arithmetic grammar
    #E ::= E + E | E * E | (E) | 1
    E = NonTerminal('E')
    G = Grammar()
    G.add_rule(E, Sentence((E, Terminal('+'), E)))
    G.add_rule(E, Sentence((E, Terminal('*'), E)))
    G.add_rule(E, Sentence((Terminal('('), E, Terminal(')'))))
    G.add_rule(E, Sentence((Terminal('1'),)))

    parser = complete_parser_for(G, E)
    print('------------------------------------------------------------')
    print(G)
    input = '1+1'
    print(f'input: {input}')
    result = parser(input)
    print(parse_str(result))
    roots = find_roots(E, result, input)
    print(f'roots: {parse_str(roots)}')
    print(f"bsr tree: {bsr_tree_str(E, result, input)}")
    sppf = extractSPPF(result, G)
    print(f'sppf: {sppf}')
    print(sppf_tree_str(sppf, G, input))
