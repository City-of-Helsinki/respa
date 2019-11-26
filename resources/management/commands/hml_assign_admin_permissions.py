# -*- coding: utf-8 -*-
"""
Management command to assign admin permission to a group of users.

All users in given group are given administrative access to ALL non-berth resources.
"""


from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from guardian.shortcuts import assign_perm

from resources.models import Resource, UnitAuthorization
from resources.enums import UnitAuthorizationLevel


class Command(BaseCommand):
    args = 'group name'
    help = "Assign administrator permissions"

    def add_arguments(self, parser):
        parser.add_argument('group')
        parser.add_argument('--run', action='store_true')

    def handle(self, *args, **options):
        self.run = options['run']
        if not self.run:
            self.stdout.write('Doing a dry run. To actually write data use --run')
        group = Group.objects.get(name=options['group'])
        users = group.user_set.all()
        resources = Resource.objects.filter(berth__isnull=True).select_related('unit')
        units = set(r.unit for r in resources)

        with transaction.atomic():
            for user in users:
                self.grant_permissions(user, units)

    def grant_permissions(self, user, units):
        self.stdout.write('Granting permissions to {}\n'.format(user.username))
        if self.run:
            user.is_staff = True
            user.save()
            for unit in units:
                assign_perm('unit:can_approve_reservation', user, unit)
                UnitAuthorization.objects.get_or_create(
                    subject=unit, authorized=user, level=UnitAuthorizationLevel.admin)
