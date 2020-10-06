import time

import pytest
from django.core.cache import cache
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from thenewboston.utils.format import format_address
from thenewboston.utils.signed_requests import generate_signed_request

from v1.banks.models.bank import Bank
from v1.banks.serializers.bank import BankSerializer
from v1.cache_tools.cache_keys import CLEAN_STATUS
from v1.self_configurations.helpers.signing_key import get_signing_key
from ..constants import (
    CLEAN_COMMAND_START,
    CLEAN_COMMAND_STOP,
    CLEAN_STATUS_CLEANING,
    CLEAN_STATUS_NOT_CLEANING,
    CLEAN_STATUS_STOP_REQUESTED
)
from ..serializers.clean import CleanSerializer


@pytest.fixture(autouse=True)
def self_configuration(confirmation_validator_configuration):
    return confirmation_validator_configuration


def clean_request(client, command, status):
    return client.post_json(
        reverse('clean-list'),
        generate_signed_request(
            data={
                'clean': command
            },
            nid_signing_key=get_signing_key()
        ),
        expected=status,
    )


def clean_status(client):
    return client.get_json(
        reverse('clean-list'),
        expected=HTTP_200_OK,
    )


@pytest.mark.django_db(transaction=True)
def test_clean_start_200(client, no_requests, celery_worker):
    response = clean_request(client, CLEAN_COMMAND_START, HTTP_200_OK)

    assert response['clean_last_completed'] is None
    assert response['clean_status'] == CLEAN_STATUS_CLEANING

    assert cache.get(CLEAN_STATUS) == CLEAN_STATUS_CLEANING
    time.sleep(1)
    assert cache.get(CLEAN_STATUS) == CLEAN_STATUS_NOT_CLEANING
    assert clean_status(client)['clean_status'] == CLEAN_STATUS_NOT_CLEANING


def test_clean_start_200_bank_removed(client, settings, requests_mock):
    settings.CELERY_TASK_ALWAYS_EAGER = True

    bank = Bank.objects.first()
    bank_address = format_address(
        ip_address=bank.ip_address,
        port=bank.port,
        protocol=bank.protocol
    )
    requests_mock.get(
        f'{bank_address}/config',
        json=BankSerializer(bank).data,
    )
    clean_request(client, CLEAN_COMMAND_START, HTTP_200_OK)

    with pytest.raises(Bank.DoesNotExist):
        bank.refresh_from_db()


def test_clean_start_400_already_cleaning(client):
    cache.set(CLEAN_STATUS, CLEAN_STATUS_CLEANING, None)

    response = clean_request(client, CLEAN_COMMAND_START, HTTP_400_BAD_REQUEST)
    assert response['clean'] == [CleanSerializer().error_messages['cant_start_clean']]
    assert clean_status(client)['clean_status'] == CLEAN_STATUS_CLEANING


def test_clean_start_400_stop_requested(client):
    cache.set(CLEAN_STATUS, CLEAN_STATUS_STOP_REQUESTED, None)

    response = clean_request(client, CLEAN_COMMAND_START, HTTP_400_BAD_REQUEST)
    assert response['clean'] == [CleanSerializer().error_messages['cant_start_clean']]
    assert clean_status(client)['clean_status'] == CLEAN_STATUS_STOP_REQUESTED


@pytest.mark.django_db(transaction=True)
def test_clean_stop_200(client, celery_worker):
    clean_request(client, CLEAN_COMMAND_START, HTTP_200_OK)
    response = clean_request(client, CLEAN_COMMAND_STOP, HTTP_200_OK)

    assert response['clean_last_completed'] is None
    assert response['clean_status'] == CLEAN_STATUS_STOP_REQUESTED
    time.sleep(2)
    assert cache.get(CLEAN_STATUS) == CLEAN_STATUS_NOT_CLEANING
    assert clean_status(client)['clean_status'] == CLEAN_STATUS_NOT_CLEANING


def test_clean_stop_400_not_cleaning(client):
    cache.set(CLEAN_STATUS, CLEAN_STATUS_NOT_CLEANING, None)

    response = clean_request(client, CLEAN_COMMAND_STOP, HTTP_400_BAD_REQUEST)
    assert response['clean'] == [CleanSerializer().error_messages['cant_stop_clean']]
    assert clean_status(client)['clean_status'] == CLEAN_STATUS_NOT_CLEANING


@pytest.mark.parametrize(
    'status',
    [
        CLEAN_STATUS_CLEANING,
        CLEAN_STATUS_NOT_CLEANING,
        CLEAN_STATUS_STOP_REQUESTED
    ]
)
def test_clean_status_200(client, status):
    cache.set(CLEAN_STATUS, status, None)
    assert clean_status(client)['clean_status'] == status