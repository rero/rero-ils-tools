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

"""RERO ILS Command Line Interface."""

import click

from flask.cli import with_appcontext
from flask import current_app
from ..api import Example


@click.command()
@with_appcontext
@click.argument('arg')
def app(arg):
    """This script returns a simple flask app."""
    click.secho(
        f'app: {current_app} with {arg}: {Example.example()}', fg='green')
