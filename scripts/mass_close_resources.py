import csv

from resources.models import Resource

resources = Resource.objects.filter(
    reservable=True
)

row_list = []
for resource in resources:
    row_list.append([resource.id, resource.name])

with open('closed_resources.csv', 'w', newline='') as file:
    writer = csv.writer(file, delimiter=';')
    writer.writerows(row_list)

print('Resources has been closed!')
resources.update(reservable=False)
