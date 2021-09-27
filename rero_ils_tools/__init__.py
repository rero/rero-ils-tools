#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2021 RERO
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""RERO ILS Tools module."""

import click
from flask.cli import FlaskGroup
from invenio_app.factory import create_app

from .cli.example import app
from .cli.items.replace import items_replace
from .cli.items.update import items_update
from .cli.patrons.duplicate_emails import duplicate_emails
from .cli.patrons.fix_patron_emails import fix_patron_emails
from .cli.patrons.validate_checkouts import validate_checkouts
from .cli.query.query import records_query
from .cli.update.circ_category import set_circulation_category
from .cli.delete.bibliomedia import bibliomedia


@click.group(cls=FlaskGroup, create_app=create_app)
def tools_cli():
    """All app commands."""


@tools_cli.group()
def tools():
    """Tools commands."""


@tools.group()
def update():
    """Update commands."""


@tools.group()
def replace():
    """Replace commands."""


@tools.group()
def search():
    """Search commands."""


@tools.group()
def patrons():
    """Patrons commands."""


@tools.group()
def delete():
    """Delete commands."""


tools.add_command(app)

update.add_command(set_circulation_category)
update.add_command(items_update)

replace.add_command(items_replace)

search.add_command(records_query)

patrons.add_command(duplicate_emails)
patrons.add_command(fix_patron_emails)
patrons.add_command(validate_checkouts)

delete.add_command(bibliomedia)
