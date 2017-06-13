from rest_framework import serializers


class ConstantFunctionSerializer(serializers.Serializer):
    sender_address = serializers.CharField()
    multisig_address = serializers.CharField()
    evm_input_code = serializers.CharField()
    amount = serializers.IntegerField()
    contract_address = serializers.CharField()
