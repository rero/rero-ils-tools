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
poetry run tools.py tools update items --help

```
### To extract items based on `query.txt` search and using the given model
```bash
poetry run tools.py tools search  query -t item  query.txt -o items.json -v -m model.json
query.txt: organisation.pid:1 AND document.pid:4 AND item_type.pid:4
model.json: {
    "include": ["pid", "location"],
    "item_type": {
        "$ref": "https://bib.rero.ch/api/item_types/6"
      }
}
```
### To list duplicate emails in database
```bash
poetry run tools.py tools patrons duplicate_emails
```

[repo]: https://github.com/rero/rero-ils-tools
