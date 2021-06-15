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
from .cli import app

@click.group(cls=FlaskGroup, create_app=create_app)
def tools_cli():
    """All app commands."""
    pass

@tools_cli.group()
def tools():
    """New tools group."""
    pass

tools.add_command(app)
