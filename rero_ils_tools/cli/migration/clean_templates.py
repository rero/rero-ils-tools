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

"""RERO ILS circulation category command line interface."""

from __future__ import absolute_import, print_function

import json
import os

import click
from flask import current_app
from flask.cli import with_appcontext
from rero_ils.modules.templates.api import Template
from rero_ils.modules.utils import JsonWriter


@click.command('clean_templates')
@click.option('-o', '--output', 'output', help='backup json file.')
@with_appcontext
def clean_templates(output):
    """Remove from templates unwanted fields in the data dictionary.

    :param output: save backup of templates before updates.    
    """
    if output:
        name, ext = os.path.splitext(output)
        out_file_name = f'{name}_output{ext}'
        out_file = JsonWriter(out_file_name)

    fields_to_remove = {
        'items': ['pid', 'barcode', 'status', 'document', 'holding',
                  'organisation', 'library'],
        'holdings': ['pid', 'organisation', 'library', 'document'],
        'patrons': ['pid', 'user_id', 'patron.subscriptions'],
        'documents': ['pid'],
    }
    click.secho(f'Start clean up of current templates...', fg='green')
    pids = [pid for pid in Template.get_all_pids()]
    click.secho(f'   number of templates to clean: {len(pids)}', fg='green')
    for pid in pids:
        template = Template.get_record_by_pid(pid)
        out_file.write(template)
        template_type = template.get('template_type')
        fields = fields_to_remove.get(template_type, [])
        for field in fields:
            if '.' in field:
                level_1, level_2 = field.split('.')
                template.get('data', {}).get(level_1, {}).pop(level_2, None)
            else:
                template.get('data', {}).pop(field, None)
        if fields:
            click.secho(
                f'     cleaning template : {template.get("name")}', fg='green')
            try:
                template.update(template, dbcommit=True, reindex=True)
            except Exception as err:
                text = f'unable to clean template pid: {pid} {err}'
                click.secho(text, fg='red')
