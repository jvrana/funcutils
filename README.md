# jdv_funcutils

[![Python package](https://github.com/jvrana/funcutils/actions/workflows/python-package.yml/badge.svg)](https://github.com/jvrana/funcutils/actions/workflows/python-package.yml)
[![Upload Python Package](https://github.com/jvrana/funcutils/actions/workflows/python-publish.yml/badge.svg)](https://github.com/jvrana/funcutils/actions/workflows/python-publish.yml)

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

### Github Actions

### Making a Release

1. Merge the branch
2. Wait for tests to pass
3. Tag the branch. Run `poetry version <VERSION>` to update the version.
4. Allow Github Actions to make a Release


