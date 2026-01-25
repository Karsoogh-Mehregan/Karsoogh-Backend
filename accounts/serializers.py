from rest_framework import serializers
from .models import Province, City, School, User
from .utils import validate_national_code

class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ['id', 'title']

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'title', 'province']

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'title', 'city']

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only = True)

    class Meta:
        model = User
        fields = ['id', 'national_code', 'phone', 'birth_date', 'Academic_Year', 'school', 'password']

    def validate_national_code(self, value):
        if not validate_national_code(value):
            raise serializers.ValidationError("کد ملی نامعتبر است")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserDetailSerializer(serializers.ModelSerializer):
    school = SchoolSerializer()

    class Meta:
        model = User
        exclude = ['password']