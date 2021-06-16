# [rero-ils-tools][repo]

RERO ILS misc tools for data manipulation.

## Usage

### For local machines

1. Clone the repository.
2. Set the environment variables:

```bash
export PYTHONPATH=~/rero-ils-tools export
PATH=$PATH:~/rero-ils-tools/scripts/
```

### For PODs

```bash
export PYTHONPATH=/data/nfs/ils/rero-ils-tools/rero-ils-tools
export PATH=$PATH:/data/nfs/ils/rero-ils-tools/rero-ils-tools/scripts/
```

### Examples

```bash
poetry run tools.py tools update set_circulation_category --help
```

[repo]: https://github.com/rero/rero-ils-tools
