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
from rero_ils.modules.items.api import Item, ItemsIndexer
from rero_ils.modules.utils import JsonWriter, read_json_record


@click.command('items')
@click.option('-l', '--lazy', 'lazy', is_flag=True, default=False)
@click.option('-e', '--save_errors', 'save_errors')
@click.option('-o', '--output', 'output')
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False)
@click.option('-d', '--debug', 'debug', is_flag=True, default=False)
@click.argument('infile', type=click.File('r'))
@with_appcontext
def items_replace(
    infile, lazy, save_errors, output, verbose, debug):
    """Replace item records.

    infile: JSON file contains new item records to replace.
    :param lazy: lazy reads file.
    :param save_errors: save error records to file.
    :param output: successfully replaced records to file.    
    """
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

    click.secho(f'Replacing item records', fg='green')

    ids = []
    for counter, data in enumerate(file_data, 1):
        item_pid = data.get('pid')
        if not item_pid:
            click.secho(f'item # {counter} missing pid field', fg='red')
            if save_errors:
                error_file.write(data)
            continue

        db_record = Item.get_record_by_pid(item_pid)
        # No replace is possible in the following cases:
        # 1. item is not in database
        # 2. item of type issue and there is a new circ_category or location
        if not db_record or (
            db_record.item_record_type == 'issue' and
            (
                    (
                        data.get('item_type')
                        and data.get('item_type') != db_record.get('item_type')
                    )
                or
                    (
                        data.get('location')
                        and data.get('location') != db_record.get('location')
                    )
            )
        ):
            click.secho(
                f'unable to replace item # {counter} pid {item_pid}', fg='red')
            if save_errors:
                error_file.write(data)
            continue

        try:
            new_record = db_record.replace(
                data, dbcommit=False, reindex=False)
            new_record.commit()
            # TODO: remove this line when bulk indexing problem works
            new_record.reindex()
            ids.append(new_record.id)
            click.secho(f'record # {counter} replaced', fg='green')
            if output:
                out_file.write(new_record)
        except Exception as err:
            text = f'record# {counter} pid {item_pid} failed replace {err}'
            click.secho(text, fg='red')
            if save_errors:
                error_file.write(data)
        # TODO: create a separate loop for indexing and commits
        if counter % 1000 == 0:
            db.session.commit()
            ItemsIndexer().bulk_index(ids)
            ItemsIndexer().process_bulk_queue()
            ids = []
    if ids:
        db.session.commit()
        ItemsIndexer().bulk_index(ids)
        ItemsIndexer().process_bulk_queue()
