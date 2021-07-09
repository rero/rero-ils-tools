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

import string

import click
from flask import current_app
from flask.cli import with_appcontext
from rero_ils.modules.patrons.api import Patron, PatronsSearch
from rero_ils.modules.users.api import User
from rero_ils.modules.utils import JsonWriter


@click.command('fix_patron_emails')
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False)
@with_appcontext
def fix_patron_emails(verbose):
    """Identify and fix patron emails.

    :param verbose: verbose
    """
    click.secho(f'Fixing patron emails', fg='green')
    
    out_file = JsonWriter('list_patrons_with_emails_to_fix.json')

    
    for pid in Patron.get_all_pids():
        patron = Patron.get_record_by_pid(pid)
        if patron:
            user_id = patron.get('user_id')
            print('user_id: ', user_id)
            user = User.get_by_id(user_id)
            try:
                data = user.dumpsMetadata()
                email = data.get('email')
                if email and email[-1].isdigit():
                    out_file.write(data)
                    data['email'] = None
                    if not data.get('keep_history'):
                        data['keep_history'] = True
                    user.update(data)
                    for patron in Patron.get_patrons_by_user(user.user):
                        if patron.get('patron') and not patron.get(
                            'patron', {}).get('additional_communication_email'):
                            patron['patron']['additional_communication_email'] = email.rstrip(string.digits)
                            print('patron_pid: ', patron.pid)
                            patron.update(patron, dbcommit=True, reindex=True)
            except Exception as err:
                click.echo(err)
                click.echo(f'ERROR: Can not extract record pid:{pid}')
