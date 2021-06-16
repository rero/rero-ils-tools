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
from rero_ils.modules.api import IlsRecordsIndexer
from rero_ils.modules.item_types.api import ItemType
from rero_ils.modules.tasks import process_bulk_queue
from rero_ils.modules.utils import (JsonWriter,
                                    get_record_class_from_schema_or_pid_type,
                                    get_ref_for_pid, read_json_record)


@click.command('set_circulation_category')
@click.option('-l', '--lazy', 'lazy', is_flag=True, default=False)
@click.option('-e', '--save_errors', 'save_errors')
@click.option('-o', '--output', 'output')
@click.option('-t', '--record_type', 'record_type', is_flag=False,
              default='item')
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False)
@click.option('-d', '--debug', 'debug', is_flag=True, default=False)
@click.argument('infile', type=click.File('r'))
@with_appcontext
def set_circulation_category(
    infile, lazy, save_errors, output, record_type, verbose, debug):
    """Set circulation category for items.

    infile: Json file contains record pid and the new category.
    :param record_type: either item or hold as in RECORDS_REST_ENDPOINTS.
    :param lazy: lazy reads file.
    :param save_errors: save error records to file.
    :param output: save modified records to file.    
    """
    # TODO: adapt this method for holdings records
    if record_type not in ['item']:
        click.secho(
            f'{record_type} is an unsupported record type', fg='red')
        exit()
    if output:
        name, ext = os.path.splitext(infile.name)
        out_file_name = f'{name}_output{ext}'
        out_file = JsonWriter(out_file_name)

    if save_errors:
        name, ext = os.path.splitext(infile.name)
        err_file_name = f'{name}_errors{ext}'
        error_file = JsonWriter(err_file_name)

    if lazy:
        file_data = read_json_record(infile)
    else:
        file_data = json.load(infile)

    click.secho(f'Setting circulation category {record_type}', fg='green')

    record_class = get_record_class_from_schema_or_pid_type(
        pid_type=record_type)

    ids = []
    for counter, record in enumerate(file_data, 1):
        record_pid = record.get('pid')
        new_circ_category = record.get('new_circulation_category_pid')

        if not record_pid or not new_circ_category:
            click.secho(f'record # {counter} missing fields', fg='red')
            if save_errors:
                error_file.write(record)
            continue

        record = record_class.get_record_by_pid(record_pid)
        itty = ItemType.get_record_by_pid(new_circ_category)
        # we do not modify circulation category if:
        # item is not in database
        # invalid new new_circ_category
        # items of type issue
        if not record or not itty or (
            record_type == 'item' and record.item_record_type == 'issue'
        ):
            click.secho(
                f'unable to modify rec # {counter} pid {record_pid}', fg='red')
            if save_errors:
                error_file.write(record)
            continue

        try:
            if record_type == 'item':
                record['item_type'] = {
                    '$ref': get_ref_for_pid('item_types', new_circ_category)
                }
                new_record = record.update(
                    record, dbcommit=False, reindex=False)
                new_record.commit()
                ids.append(record.id)
            click.secho(f'record # {counter} created', fg='green')
            if output:
                out_file.write(new_record)
        except Exception as err:
            text = f'record# {counter} pid {record_pid} failed creation {err}'
            click.secho(text, fg='red')
            if save_errors:
                error_file.write(record)
        # TODO: create a separate loop for indexing and commits
        if counter % 1000 == 0:
            db.session.commit()
            IlsRecordsIndexer().bulk_index(ids, doc_type=record_type)
            ids = []
    if ids:
        db.session.commit()
        IlsRecordsIndexer().bulk_index(ids, doc_type=record_type)
