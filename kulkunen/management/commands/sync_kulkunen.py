from django.core.management.base import BaseCommand
from django.utils import timezone

from kulkunen.models import AccessControlGrant, AccessControlSystem


class Command(BaseCommand):
    help = 'Creates and removes Kulkunen access control grants'

    def sync_system(self, system):
        system_grants = AccessControlGrant.objects.filter(resource__system=system).distinct()
        # Revocation first
        revoke_states = (AccessControlGrant.INSTALLED, AccessControlGrant.CANCELLED)
        grants_to_revoke = system_grants.filter(state__in=revoke_states, remove_at__lte=self.now)
        for grant in grants_to_revoke:
            grant.remove()

        grants_to_install = system_grants.filter(state=AccessControlGrant.REQUESTED, install_at__lte=self.now)
        for grant in grants_to_install:
            grant.install()

    def handle(self, *args, **options):
        self.now = timezone.now()
        for system in AccessControlSystem.objects.all():
            self.sync_system(system)
