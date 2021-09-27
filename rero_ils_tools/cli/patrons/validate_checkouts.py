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
import string

import click
from flask import current_app
from flask.cli import with_appcontext
from rero_ils.modules.items.api import Item
from rero_ils.modules.utils import JsonWriter, extracted_data_from_ref


@click.command('validate_checkouts')
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False)
@click.option('-i', '--infile', 'infile', required=True)
@with_appcontext
def validate_checkouts(infile, verbose):
    """Valide Virtua checkouts.

    :param infile: file with Virtua circulation transactions
    :param verbose: verbose
    """
    click.secho(f'Validating Virtua checkouts', fg='green')
    
    vs_file = JsonWriter('virtua_transactions_not_yet_loaded_vs.json')
    bulle_file = JsonWriter('virtua_transactions_not_yet_loaded_bulle.json')
    nj_file = JsonWriter('virtua_transactions_not_yet_loaded_nj.json')
    with open(infile) as infile_filename:
        transactions = json.load(infile_filename)
        for transaction in transactions:
            item_pid = transaction.get('item_pid')
            print('item_pid', item_pid)
            on_loan_loan = Item.get_loan_pid_with_item_on_loan(item_pid) 
            if on_loan_loan:
                item = Item.get_record_by_pid(item_pid)
                if item.get('status') != 'on_loan':
                    print('missing on_loan status')
                    item['status'] = 'on_loan'
                    item.update(item, dbcommit=True, reindex=True)
            else:
                org_pid = extracted_data_from_ref(
                    transaction.get('organisation').get('$ref'))
                if int(org_pid) == 1:
                    bulle_file.write(transaction)
                elif int(org_pid) == 2:
                    vs_file.write(transaction)
                elif int(org_pid) == 3:
                    nj_file.write(transaction)
