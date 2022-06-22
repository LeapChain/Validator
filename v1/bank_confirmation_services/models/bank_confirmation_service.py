from django.db import models
from leapchain.models.confirmation_service import ConfirmationService

from v1.banks.models.bank import Bank


class BankConfirmationService(ConfirmationService):
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE)

    class Meta:
        default_related_name = 'bank_confirmation_services'

    def __str__(self):
        return (
            f'ID: {self.id} | '
            f'{self.start} - {self.end}'
        )
