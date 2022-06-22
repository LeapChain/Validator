from factory import Faker
from factory.django import DjangoModelFactory
from leapchain.constants.network import BALANCE_LOCK_LENGTH, MAX_POINT_VALUE, VERIFY_KEY_LENGTH

from ..models.account import Account


class AccountFactory(DjangoModelFactory):
    account_number = Faker('pystr', max_chars=VERIFY_KEY_LENGTH)
    balance = Faker('pyint', max_value=MAX_POINT_VALUE)
    balance_lock = Faker('pystr', max_chars=BALANCE_LOCK_LENGTH)
    locked = Faker('pystr', max_chars=MAX_POINT_VALUE)

    class Meta:
        model = Account
