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
    job_title = models.CharField('Должность', max_length=120, blank=True)
    sector = models.CharField('Сектор', max_length=80, blank=True)
    district = models.CharField('Район / город', max_length=120, blank=True)
    region = models.CharField('Область', max_length=120, blank=True)
    purpose = models.CharField('Цель использования', max_length=80, blank=True)
    interest_layers = models.CharField('Интерес к слоям', max_length=255, blank=True)
    comment = models.TextField('Комментарий', blank=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def is_read_only(self):
        if self.is_superuser:
            return False
        return self.role == self.Role.OBSERVER

    def can_edit(self):
        return self.role in (
            self.Role.ADMIN,
            self.Role.SPECIALIST,
            self.Role.MONITOR,
        )
