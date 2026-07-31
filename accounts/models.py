from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Главный администратор'
        SPECIALIST = 'specialist', 'Специалист'
        MONITOR = 'monitor', 'Сотрудник мониторинга'
        OBSERVER = 'observer', 'Публичный пользователь'

    role = models.CharField(
        'Роль',
        max_length=20,
        choices=Role.choices,
        default=Role.OBSERVER,
    )
    organization = models.CharField('Организация', max_length=255, blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def is_read_only(self):
        return self.role == self.Role.OBSERVER

    def can_edit(self):
        return self.role in (
            self.Role.ADMIN,
            self.Role.SPECIALIST,
            self.Role.MONITOR,
        )
