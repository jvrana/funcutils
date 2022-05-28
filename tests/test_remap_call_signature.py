from funcutils import SignatureExtended


def test_remap_call_signature():

    def foo(a: str, b: str):
        return a + b

    mapping = {0: 1, 1: 0}

    def bar(b: str, a: str):
        return foo(a, b)

    s = SignatureExtended(foo)
    s.permute(1, 0)

    args = ('world', 'hello')
    value_mapping = {}
    for k, v in mapping.items():
        i, p = s.get_pos_and_param(k)
        if p.kind == p.POSITIONAL_OR_KEYWORD or p.kind == p.POSITIONAL_ONLY:
            key = i
        else:
            key = p.name
        value_mapping[key] = args[v]

    bound = s.bind('world', 'hello')
    print(bound)