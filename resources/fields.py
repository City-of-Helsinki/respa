from django.db import models


class EquipmentField(models.ManyToManyField):
    """
    Model field for Equipment M2M in Resource.

    Used for overriding save_form_data so that it allows saving the form
    m2m field even though there is an intermediary model.
    """
    def save_form_data(self, instance, data):
        # data is a queryset of equipment
        # instance is a Resource
        instance_equipment = getattr(instance, self.attname)  # ManyRelatedManager

        # The through model (a.k.a intermediate table)
        through_model = instance_equipment.through

        # Delete the relations that were unchecked from the form
        equipment_to_delete = instance_equipment.exclude(pk__in=data)
        for equipment in equipment_to_delete:
            through_model.objects.filter(resource=instance, equipment=equipment).delete()

        # Add new relations for those that don't exist yet
        for equipment in data:
            if not instance_equipment.filter(pk=equipment).exists():
                through_model.objects.update_or_create(resource=instance, equipment=equipment)
