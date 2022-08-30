# Func Utils



## Features

### Signature Manipulations

### Function Transforms

**Permuting Arguments**

*Status*: Incomplete
```
permute(1, 0, 2)
f(a, b, c) --> f(b, a, c)
```

**Packing Arguments**

*Status*: Incomplete
```
pack({(0, 2): 0})
f(a, b, c) --> f(ac, b)
```

```
pack({(0, 2): 1})
f(a, b, c) --> f(b, ac)
```

**Unpacking Arguments**

*Status*: Incomplete

```
unpack({1: (0, 1))
f(b, ac) --> f(a, c, b)
```

**Curry**

*Status*: Incomplete

## Developing

### Running Tox Tests

Install pyenv. 

Install python versions using `pyenv install 3.8.12` and so on.

Use `pyenv local 3.8.12 3.9.10 3.10.2` to install new versions of python if necessary.

Run `tox` to run tests.

