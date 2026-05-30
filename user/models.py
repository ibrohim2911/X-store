from django.db import models
from common.models import BaseModel
from django.contrib.auth.models import AbstractUser, BaseUserManager
# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, password, **extra_fields)
class User(AbstractUser, BaseModel):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, unique=True)
    username = None
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['name']
    objects = UserManager()
    def __str__(self):
        return f'{self.name} - {self.phone_number} - {self.is_staff}'

