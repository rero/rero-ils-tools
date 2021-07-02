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

import click
from flask import current_app
from flask.cli import with_appcontext
from rero_ils.modules.patrons.api import Patron


@click.command('duplicate_emails')
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False)
@with_appcontext
def duplicate_emails(verbose):
    """Identify duplicate emails in patron records.

    :param verbose: verbose
    """
    click.secho(f'Searching patron records for duplicate emails', fg='green')
    
    def check_email(email, emails, duplicate_emails):
        """Check if email is duplicated."""
        if email.lower() not in emails:
            emails.append(email.lower())
        else:
            duplicate_emails.append(email)

    all_user_ids = []
    for pid in Patron.get_all_pids():
        patron = Patron.get_record_by_pid(pid)
        all_user_ids.append(patron.get('user_id'))

    emails = []
    duplicate_emails = []
    duplicate_add_emails = []
    for user_id in all_user_ids:
        user = patron._get_user_by_user_id(user_id)
        email = user.email
        if email:
            check_email(email, emails, duplicate_emails)

    for pid in Patron.get_all_pids():
        patron = Patron.get_record_by_pid(pid)
        add_email = patron.patron.get('additional_communication_email')
        if add_email:
            check_email(email, emails, duplicate_add_emails)

    duplicate_emails = list(set(duplicate_emails))
    if duplicate_emails:
        click.secho(f'Duplicates in field email:', fg='red')
        for value in duplicate_emails:
            click.secho(f'{value}', fg='red')

    duplicate_add_emails = list(set(duplicate_add_emails))
    if duplicate_add_emails:
        click.secho(f'Duplicates in field additional_communication:', fg='red')
        for value in duplicate_add_emails:
            click.secho(f'{value}', fg='red')
