from respa_admin import accessibility_api


def test_calculate_checksum():
    params = {
        'systemId': '123',
        'targetId': '456',
        'user': 'user',
        'validUntil': '2020-05-05T09:00:00',
        'name': 'target name',
        'formId': '2',
    }
    result = accessibility_api.calculate_checksum(params, 'secret')
    assert result == 'BDEDD65FB02A88AC721A5078EB4E6CB01CB2F02E1474CB4CB84FC99509373BC0'


def test_calculate_checksum_location_id():
    params = {
        'systemId': '123',
        'targetId': '456',
        'user': 'user',
        'validUntil': '2020-05-05T09:00:00',
        'name': 'target name',
        'formId': '2',
        'locationId': 'location1'
    }
    result = accessibility_api.calculate_checksum(params, 'secret')
    assert result == 'E874A16F77896E71BE46B24BC9ADF5410EB4067EAFEBEA1F14BBBDF188CFDFFA'
