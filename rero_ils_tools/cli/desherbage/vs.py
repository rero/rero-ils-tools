#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2022 RERO
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

"""RERO ILS bibliomedia desherbage VS command line interface."""

from __future__ import absolute_import, print_function

import json
import os
import sys
from datetime import datetime

import click
from elasticsearch_dsl import Q
from flask.cli import with_appcontext
from rero_ils.modules.api import IlsRecordError
from rero_ils.modules.documents.api import Document
from rero_ils.modules.documents.utils import title_format_text_head
from rero_ils.modules.holdings.api import Holding
from rero_ils.modules.items.api import Item, ItemsSearch
from rero_ils.modules.libraries.api import Library
from rero_ils.modules.local_fields.api import LocalField, LocalFieldsSearch
from rero_ils.modules.utils import JsonWriter


def validate_inputs(library_pid, save):
    """Validate correct inputs are given."""
    library = Library.get_record_by_pid(library_pid)
    if not library:
        click.secho(f'error: library record not found.', fg='red')
        sys.exit()
    if not os.path.exists(save):
        click.secho(f'error: directory {save} does not exist.', fg='red')
        sys.exit()
    return library


def write_to_log_file(msg, info):
    """Write information into log file."""
    click.echo(msg)
    info.write(msg + '\n')


def get_document_local_fields(document_pid, org_pid):
    """."""
    query_filters = [
        Q('term', parent__type='doc'),
        Q('term', parent__pid=document_pid),
        Q('term', organisation__pid=org_pid),
    ]
    query = LocalFieldsSearch()\
        .query('bool', filter=query_filters)\
        .source(['pid'])

    local_fields = []
    for hit in query.scan():
        local_field_pid = hit.pid
        local_field = LocalField.get_record_by_pid(local_field_pid)
        local_fields.append(local_field)
    return local_fields


def delete_library_code(data, text_1, text_2):
    """Delete the library code from local fields."""
    data_field = ''
    if f'$2 {text_2}' in data:
        dollar_2 = data.split('$2')
        for a in dollar_2:
            if text_2 in a:
                dollar_2.remove(a)
        if len(dollar_2) > 1:
            for a in dollar_2:
                if a == '':
                    a = '$2'
                data_field += a
    elif f'$a {text_1}' in data:
        dollar_a = data.split('$a')
        for a in dollar_a:
            if text_1 in a:
                dollar_a.remove(a)
        if len(dollar_a) > 1:
            for a in dollar_a:
                if a == '':
                    a = '$a'
                data_field += a
    return data_field


def update_local_fields(
        local_fields, library_code, document, docs_file,
        local_fields_list, document_pid, dbcommit, reindex):
    """Delete library code from local fields."""
    for record in local_fields:
        fields = list(record.get('fields', {}).keys())
        for field in fields:
            text_1 = f'{library_code}'
            text_2 = f'cdu-{library_code}'
            data_field = ' '.join([
                str(elem) for elem in record['fields'][field]])
            if text_1 in data_field or text_2 in data_field:
                docs_file.write(document)
                msg = f"{document_pid}: {record.pid}: {record['fields'][field]}"
                local_fields_list.write(msg + '\n')
                field_data = delete_library_code(data_field, text_1, text_2)
                if not field_data:
                    del record['fields'][field]
                else:
                    record['fields'][field] = [field_data]
        if len(record.get('fields', {}).keys()):
            record.update(record, dbcommit=dbcommit, reindex=reindex)
        else:
            record.delete(record, dbcommit=dbcommit, delindex=reindex)


def number_of_items(library_pid, document_pid):
    """Get number of items for given library."""
    query_filters = [
        Q('term', document__pid=document_pid),
        Q('term', library__pid=library_pid)
    ]
    query = ItemsSearch()\
        .query('bool', filter=query_filters)\
        .source(['pid'])
    return query.count()


def delete_documents(document_pids, deleted_docs_file):
    """Attempt to delete documents."""
    for document_pid in document_pids:
        document = Document.get_record_by_pid(document_pid)
        if document:
            can, _ = document.can_delete
            if can:
                deleted_docs_file.write(document)
                try:
                    document.delete(document, dbcommit=True, delindex=True)
                except Exception as error:
                    click.echo(error)
                    click.echo(
                        f'ERROR: Unable to delete document_pid:{document_pid}')
                

def manage_documents(
        library_pid, document_pids, info, docs_file, docs_list, org_pid,
        library_code, local_fields_list, dbcommit, reindex):
    """Update document if needed."""
    for document_pid in document_pids:
        document = Document.get_record_by_pid(document_pid)
        to_print = False
        seriesStatement = document.get('seriesStatement', [])
        for statement in seriesStatement:
            if statement.get('seriesEnumeration'):
                to_print = True
        if document.get('partOf'):
            to_print = True
        if to_print:
            sort_title = title_format_text_head(
                document.get('title', []),
                with_subtitle=True
            )
            links = ''
            if document.get('partOf'):
                for part in document.get('partOf'):
                    link = part.get('document', {}).get('$ref')
                    if link:
                        links = f"{links} {link}"
            msg = f'{document.pid}: {links} | {sort_title}'
            docs_list.write(msg + '\n')
        if not number_of_items(library_pid, document_pid):
            local_fields = get_document_local_fields(document_pid, org_pid)
            update_local_fields(
                local_fields, library_code, document, docs_file,
                local_fields_list, document_pid, dbcommit, reindex)


def manage_holdings(holding_pids, info, holdings_list):
    """List of serial holdings."""
    for holding_pid in holding_pids:
        holding = Holding.get_record_by_pid(holding_pid)
        if holding and holding.holdings_type == 'serial':
            msg = f'{holding.pid}'
            holdings_list.write(msg + '\n')


@click.command('vs')
@click.argument('infile', type=click.File('r'))
@click.option('-n', '--noupdate', is_flag=True, default=True,help='No Update.')
@click.option('-l', '--library_pid', required=True, help='Library PID.')
@click.option('-c', '--library_code', required=True, help='Library code.')
@click.option('-s', '--save', required=True, help='Directory to saving files.')
@click.option('-v', '--verbose', is_flag=True, default=False,help='Verbose.')
@with_appcontext
def vs(
        infile, noupdate, library_pid, library_code, save, verbose):
    """Delete library items.

    infile: Text file contains the item barcodes to delete.
    :param library_pid: The PID of the library.
    :param library_code: The code of the library.
    :param save: The directory where to save output files.
    """
    dbcommit, reindex = True, True
    if not noupdate:
        dbcommit = False
        reindex = False
    library = validate_inputs(library_pid, save)
    click.secho(f'Delete items for library: {library.get("name")}', fg='red')

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    docs_file = JsonWriter(
        os.path.join(save, f'documents_{timestamp}.json'))
    deleted_docs_file = JsonWriter(
        os.path.join(save, f'deleted_documents_{timestamp}.json'))
    items_file = JsonWriter(os.path.join(save, f'items_{timestamp}.json'))
    docs_list = open(
        os.path.join(
            save, f'documents_partof_seriesStatement_{timestamp}.txt'), 'w')
    holdings_list = open(
        os.path.join(save, f'holding_serials_{timestamp}.txt'), 'w')
    info = open(os.path.join(save, f'vs_log_{timestamp}.log'), 'w')
    local_fields_list = open(
        os.path.join(save, f'local_fields_{timestamp}.txt'), 'w')

    org_pid = library.organisation_pid
    barcodes = infile.readlines()
    holding_pids, document_pids = [], []
    items_not_in_db, items_not_deleted, items_deleted = 0, 0, 0
    for idx, line in enumerate(barcodes, 1):
        barcode = line.rstrip()
        item = Item.get_item_by_barcode(barcode, org_pid)
        if not item:
            msg = (f'Item barcode: "{barcode}" does not exist in database.')
            write_to_log_file(msg, info)
            items_not_in_db +=1
        elif item.reasons_not_to_delete():
            reasons = item.reasons_not_to_delete()
            can, reasons = item.can_delete
            text = 'can not be deleted. reasons:'
            msg = (f'Item barcode: "{barcode}" {text} {json.dumps(reasons)}')
            write_to_log_file(msg, info)
            items_not_deleted += 1
        else:
            document_pid = item.document_pid
            holding_pid = item.holding_pid
            try:
                items_file.write(item)
                item.delete(item, dbcommit=dbcommit, delindex=reindex)
                items_deleted += 1
                msg = (f'Item barcode: "{barcode}" deleted from database.')
                write_to_log_file(msg, info)
                holding_pids.append(holding_pid)
                document_pids.append(document_pid)
            except IlsRecordError.NotDeleted:
                msg = (f'Item barcode: "{barcode}" unable to delete.')
                write_to_log_file(msg, info)
                items_not_deleted += 1
            except Exception as error:
                msg = (f'Item barcode: "{barcode}" unable to delete: {error}')
                write_to_log_file(msg, info)
                items_not_deleted += 1
    
    manage_holdings(list(set(holding_pids)), info, holdings_list)
    manage_documents(
        library_pid, list(set(document_pids)), info, docs_file, docs_list,
        org_pid, library_code, local_fields_list, dbcommit, reindex)
    delete_documents(list(set(document_pids)), deleted_docs_file)
    count = f'Count: {idx}'
    deleted = f', Deleted: {items_deleted}'
    not_in_db = f', Not in DB: {items_not_in_db}'
    not_deleted = f', Not deleted: {items_not_deleted}'
    msg = f'{count}{deleted}{not_in_db}{not_deleted}'
    click.secho(msg, fg='green')
    assert idx == items_deleted + items_not_in_db + items_not_deleted
