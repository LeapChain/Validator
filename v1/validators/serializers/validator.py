from rest_framework import serializers
from leapchain.utils.fields import all_field_names

from ..models.validator import Validator


class ValidatorSerializer(serializers.ModelSerializer):

    class Meta:
        exclude = ('id',)
        model = Validator
        read_only_fields = all_field_names(Validator)


class ValidatorSerializerCreate(serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        model = Validator


class ValidatorSerializerUpdate(serializers.ModelSerializer):

    class Meta:
        fields = ('trust',)
        model = Validator
