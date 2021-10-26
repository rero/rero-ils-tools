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

"""RERO ILS bibliomedia delete command line interface."""

from __future__ import absolute_import, print_function

import os
from datetime import datetime

import click
from elasticsearch_dsl import Q
from flask.cli import with_appcontext
from rero_ils.modules.documents.api import Document
from rero_ils.modules.holdings.api import Holding
from rero_ils.modules.items.api import Item, ItemsSearch
from rero_ils.modules.local_fields.api import LocalField, LocalFieldsSearch
from rero_ils.modules.operation_logs.api import OperationLogsSearch
from rero_ils.modules.utils import JsonWriter


def delete_record(record, verbose):
    """Delete record.

    :param record: record to delete_count.
    :param verbose: verbose print.
    :param delete: really delete record.
    """
    reasons_not_to_delete = record.reasons_not_to_delete()
    if reasons_not_to_delete:
        if verbose:
            click.secho(
                '\tNOT DELETED:\t'
                f'{type(record).__name__} {record.get("pid")}\t'
                f'{reasons_not_to_delete}',
                fg='yellow'
            )
        return False
    record.delete(dbcommit=True, delindex=True)
    return True


def local_field_to_change(locf, doc, collection):
    """Local field to change.

    :param locf: local field to change.
    :param doc: document to reindex.
    :param collection: collection to delete from local field.
    """
    field_1 = locf['fields']['field_1']
    new_data = []
    for data in field_1:
        new_elements = []
        for data_element in data.split(' | '):
            if collection not in data_element:
                new_elements.append(data_element)
        if new_elements:
            new_data.append(' | '.join(new_elements))
    if new_data:
        locf['fields']['field_1'] = new_data
    else:
        locf['fields'].pop('field_1')
    if locf['fields']:
        locf.update(data=locf, dbcommit=True, reindex=True)
    else:
        locf.delete(dbcommit=True, delindex=True)
    doc.reindex()


def get_bibliomedia_id(document):
    """Get bibliomedia id from document."""
    for identified_by in document.get('identifiedBy', []):
        if identified_by.get('source') == 'BIBLIOMEDIA':
            return identified_by.get('value')


@click.command()
@click.argument('collection')
@click.option('-s', '--save', default=None, help='Directory for saving files.')
@click.option('-d', '--delete', is_flag=True, default=False,
              help='Realy delete records.')
@click.option('-v', '--verbose', is_flag=True, default=False,
              help='Verbose print.')
@with_appcontext
def bibliomedia(collection, save, delete, verbose):
    """Delete bibliomedia collection."""
    click.secho(f'Delete Bibliomedia Collection: {collection}', fg='red')

    if save:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        doc_file = JsonWriter(
            os.path.join(save, f'documents_{timestamp}.json'))
        item_file = JsonWriter(
            os.path.join(save, f'items_{timestamp}.json'))
        locf_file = JsonWriter(
            os.path.join(save, f'local_fields_{timestamp}.json'))
        doc_error_file = JsonWriter(
            os.path.join(save, f'documents_error_{timestamp}.json'))
        item_error_file = JsonWriter(
            os.path.join(save, f'items_error_{timestamp}.json'))
        locf_error_file = JsonWriter(
            os.path.join(save, f'local_fields_error_{timestamp}.json'))
        info = open(
            os.path.join(save, f'{collection}_{timestamp}.log'), 'w')

    # if there is a - in the collection name the elastic search is not working.
    collection_split = collection.split('-')
    search_collection = collection_split[0]
    if len(collection_split) > 1:
        search_collection = collection_split[1]

    query = ItemsSearch() \
        .filter('term', notes__type='staff_note') \
        .filter('match', notes__content=search_collection)
    # group by documents
    document_items = {}
    for hit in query.source(['pid', 'document']).scan():
        document_pid = hit.document.pid
        document_items.setdefault(document_pid, [])
        document_items[document_pid].append(hit.pid)

    idx = 0
    delete_count = 0
    checkouts_count = 0
    for idx, document_pid in enumerate(document_items, 1):
        do_not_delete = False
        item_pids = document_items[document_pid]
        document = Document.get_record_by_pid(document_pid)
        # items
        items = []
        for item_pid in item_pids:
            item = Item.get_record_by_pid(item_pid)
            reasons_not_to_delete = item.reasons_not_to_delete()
            checkout_count = item.get('legacy_checkout_count', 0)
            checkout_count += OperationLogsSearch() \
                .filter('term', record__type='loan') \
                .filter('term', loan__item__pid=item_pid) \
                .filter('term', loan__trigger='checkout') \
                .count()
            checkouts_count += checkout_count

            if reasons_not_to_delete:
                msg = (f'{idx}\tDocument id: {get_bibliomedia_id(document)}\t'
                        f'item barcode: {item.get("barcode")}\t'
                        f'checkout count: {checkout_count}')
                if not verbose:
                    click.echo(msg)
                do_not_delete = True
                msg = (f'\tCAN NOT DELETE:\t'
                       f'document pid: {document_pid}\t'
                       f'item: pid: {item_pid}\t'
                       f'{reasons_not_to_delete}')
                if not verbose:
                    click.echo(msg)
                if save:
                    info.write(msg + '\n')
            items.append({
                'item': item,
                'reasons_not_to_delete': reasons_not_to_delete
            })
        # local fields
        query_filters = [
            Q('term', parent__type='doc'),
            Q('term', parent__pid=document_pid)
        ]
        query = LocalFieldsSearch()\
            .query('bool', filter=query_filters)\
            .source(['pid'])

        local_fields = []
        for hit in query.scan():
            local_field_pid = hit.pid
            local_field = LocalField.get_record_by_pid(local_field_pid)
            local_fields.append(local_field)

        msg = (f'{idx}\tDocument id: {get_bibliomedia_id(document)}\t'
               f'item barcode: {item.get("barcode")}\t'
               f'checkout count: {checkout_count}')
        can_not_delete_msg = (f'\tCAN NOT DELETE:\t'
                f'document pid: {document_pid}\t'
                f'item: pid: {item_pid}\t'
                f'{reasons_not_to_delete}')
        if save:
            if do_not_delete:
                info.write(msg + '\n')
                info.write(can_not_delete_msg + '\n')
                doc_error_file.write(document)
                for item in items:
                    item_error_file.write(item['item'])
                for local_field in local_fields:
                    locf_error_file.write(local_field)
            else:
                doc_file.write(document)
                for item in items:
                    item_file.write(item['item'])
                for local_field in local_fields:
                    locf_file.write(local_field)
        if verbose:
            click.echo(msg)
            if do_not_delete:
                click.secho(can_not_delete_msg, fg='red')
            click.secho(
                f'\tdocument    :{document_pid} '
                f"{document['adminMetadata']['note']}",
                fg='yellow'
            )
            for item in items:
                msg = item["reasons_not_to_delete"] or ''
                click.secho(
                    f"\titem        :{item['item']['pid']} "
                    f"barcode:{item['item']['barcode']} "
                    f"{item['item']['notes']} "
                    f'{msg}',
                    fg='yellow'
                )
            for local_field in local_fields:
                click.secho(
                    f"\tlocal field :{local_field['pid']} "
                    f"{local_field['fields']['field_1']}",
                    fg='yellow'
                )

        if not do_not_delete:
            delete_count += 1
        if delete and not do_not_delete:
            for item in items:
                delete_record(item['item'], verbose)
            if delete_record(document, verbose):
                for local_field in local_fields:
                    delete_record(local_field, verbose)
            else:
                for local_field in local_fields:
                    local_field_to_change(local_field, document, collection)

    msg = f'Count: {idx}, Deleted: {delete_count}, Checkouts: {checkouts_count}'
    click.echo(msg)
    if save:
        info.write(msg + '\n')
