import pytest
from src.encoding import encode_routes, decode_vector, route_based_crossover, cut_and_fill, swap_mutation, insert_mutation


def test_encode_decode_roundtrip():
    routes = [[1,2,3],[4,5]]
    v = encode_routes(routes)
    assert v[0]==0 and v[-1]==0
    dec = decode_vector(v)
    assert dec == routes


def test_rbx_and_mutations():
    a = [0,1,2,3,0,4,5,0]
    b = [0,4,2,1,0,3,5,0]
    child = route_based_crossover(a,b)
    assert isinstance(child, list)
    # cut_and_fill returns valid vector
    cf = cut_and_fill(a,b)
    assert isinstance(cf, list)
    sm = swap_mutation(cf)
    it = insert_mutation(cf)
    assert isinstance(sm, list) and isinstance(it, list)
