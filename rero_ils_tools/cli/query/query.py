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
from invenio_db import db
from invenio_records_rest.utils import obj_or_import_string
from rero_ils.modules.utils import (JsonWriter,
                                    get_record_class_from_schema_or_pid_type,
                                    read_json_record)


@click.command('query')
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False)
@click.option('-o', '--output', 'output', required=True)
@click.option('-t', '--record_type', 'record_type', is_flag=False,
              default='item')
@click.option('-m', '--model', 'model', required=False)
@click.option('-f', '--full', 'full', is_flag=True, default=False)
@click.argument('infile', type=click.File('r'))
@with_appcontext
def records_query(infile, full, model, record_type, output, verbose):
    """Query records.

    :param verbose: verbose
    :param infile: text file containing the query to select records
    :param output: JSON output file
    :param record_type: record type as in RECORDS_REST_ENDPOINTS
    :param full: extract all fields of record
    :param model: JSON file to list fields to extract or not
    """
    click.secho(f'Extract {record_type} records to: {output}', fg='green')
    outfile = JsonWriter(output)

    record_class = get_record_class_from_schema_or_pid_type(
        pid_type=record_type)

    search_class = obj_or_import_string(
        current_app.config
        .get('RECORDS_REST_ENDPOINTS')
        .get(record_type, {}).get('search_class'))
    
    if not record_class or not search_class:
        click.secho(f'Invalid record type: {record_type}', fg='red')
        exit()

    model_json = {'pid': True}
    if model:
        with open(model) as model_filename:
            model_json = json.load(model_filename)
            
    expert_search = infile.readline().strip()
    click.secho(f'Using expert search: {expert_search}', fg='green')

    search = search = search_class().query(
        'query_string', query=expert_search).source('pid')
    click.secho(f'Number of records to extract: {search.count()}', fg='green')

    for count, hit in enumerate(search.scan(), 1):
        try:
            pid = hit.pid
            record = record_class.get_record_by_pid(pid)
            if verbose:
                click.echo(
                    f'{count: <8} extract record {record.pid}:{record.id}')
            if full:
                for key, values in model_json.items():
                    if key == 'exclude':
                        for field in values:
                            record.pop(field, None)
                outfile.write(record)
            else:
                extracted_record = {}
                for key, values in model_json.items():
                    if key == 'include':
                        for field in values:
                            if record.get(field):
                                extracted_record[field] = record[field]
                    else:
                        extracted_record[key] = values
                outfile.write(extracted_record)
        except Exception as err:
            click.echo(err)
            click.echo(f'ERROR: Can not extract record pid:{pid}')
