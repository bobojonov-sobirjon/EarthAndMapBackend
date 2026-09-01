from django.conf import settings
from django.db import models


class ChangeLog(models.Model):
    """История изменений земельного участка."""

    class ChangeType(models.TextChoices):
        CREATED = 'created', 'Создано'
        UPDATED = 'updated', 'Обновлено'
        STATUS_CHANGED = 'status_changed', 'Статус изменён'
        GEOMETRY_CHANGED = 'geometry_changed', 'Геометрия изменена'
        DELETED = 'deleted', 'Удалено'

    land = models.ForeignKey(
        'lands.PublicLand',
        on_delete=models.CASCADE,
        related_name='change_logs',
        verbose_name='Объект',
    )
    change_type = models.CharField('Тип изменения', max_length=20, choices=ChangeType.choices)
    field_name = models.CharField('Поле', max_length=100, blank=True)
    old_value = models.TextField('Старое значение', blank=True)
    new_value = models.TextField('Новое значение', blank=True)
    description = models.TextField('Описание', blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Кто изменил',
    )
    changed_at = models.DateTimeField('Дата изменения', auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Запись об изменении'
        verbose_name_plural = 'История изменений'

    def __str__(self):
        return f'{self.land.name} — {self.get_change_type_display()}'


class Issue(models.Model):
    """Проблемные участки (точка / линия / полигон)."""

    class Severity(models.TextChoices):
        LOW = 'low', 'Низкая'
        MEDIUM = 'medium', 'Средняя'
        HIGH = 'high', 'Высокая'
        CRITICAL = 'critical', 'Критическая'

    class IssueStatus(models.TextChoices):
        NEW = 'new', 'Новая'
        OPEN = 'open', 'Открыта'
        IN_PROGRESS = 'in_progress', 'В работе'
        RESOLVED = 'resolved', 'Устранена'
        CLOSED = 'closed', 'Закрыта'

    class GeometryKind(models.TextChoices):
        POINT = 'Point', 'Точка'
        LINE = 'LineString', 'Линия'
        POLYGON = 'Polygon', 'Полигон'

    land = models.ForeignKey(
        'lands.PublicLand',
        on_delete=models.CASCADE,
        related_name='issues',
        null=True,
        blank=True,
        verbose_name='Объект',
    )
    title = models.CharField('Заголовок (UZ)', max_length=255)
    title_ru = models.CharField('Заголовок (RU)', max_length=255, blank=True)
    title_en = models.CharField('Заголовок (EN)', max_length=255, blank=True)
    description = models.TextField('Описание (UZ)')
    description_ru = models.TextField('Описание (RU)', blank=True)
    description_en = models.TextField('Описание (EN)', blank=True)
    severity = models.CharField(
        'Важность',
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=IssueStatus.choices,
        default=IssueStatus.NEW,
    )
    geometry_kind = models.CharField(
        'Тип геометрии',
        max_length=20,
        choices=GeometryKind.choices,
        default=GeometryKind.POINT,
    )
    geometry = models.JSONField('Геометрия (GeoJSON)', null=True, blank=True)
    latitude = models.FloatField('Широта', null=True, blank=True)
    longitude = models.FloatField('Долгота', null=True, blank=True)
    address = models.CharField('Адрес', max_length=400, blank=True)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reported_issues',
        verbose_name='Сообщил',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_issues',
        verbose_name='Назначен',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    resolved_at = models.DateTimeField('Устранено', null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Проблемный участок'
        verbose_name_plural = 'Проблемные участки'

    def __str__(self):
        return self.title


class ApplicationType(models.Model):
    """Murojaat qabul qiluvchi tashkilot turi."""
    name = models.CharField('Nomi', max_length=255, unique=True)
    description = models.TextField(
        'Tavsif',
        blank=True,
        help_text='Tahlil uchun: qanday muammolar shu tashkilotga tegishli',
    )
    is_active = models.BooleanField('Faol', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Murojaat turi'
        verbose_name_plural = 'Murojaat turlari'

    def __str__(self):
        return self.name


class ApplicationOnSite(models.Model):
    """Tashkilotning onlayn murojaat sayti."""
    application_type = models.ForeignKey(
        ApplicationType,
        on_delete=models.CASCADE,
        related_name='sites',
        verbose_name='Turi',
    )
    site_url = models.URLField('Sayt URL', max_length=500)
    is_active = models.BooleanField('Faol', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Murojaat sayti'
        verbose_name_plural = 'Murojaat saytlari'

    def __str__(self):
        return f'{self.application_type.name} — {self.site_url}'


class ApplicationSubmission(models.Model):
    """Foydalanuvchi tashkilot saytiga yuborgan murojaati (bizda saqlanadi)."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Qoralama'
        SUBMITTED = 'submitted', 'Yuborilgan'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='application_submissions',
        verbose_name='Foydalanuvchi',
    )
    application_type = models.ForeignKey(
        ApplicationType,
        on_delete=models.PROTECT,
        related_name='submissions',
        verbose_name='Turi',
    )
    site = models.ForeignKey(
        ApplicationOnSite,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        verbose_name='Sayt',
    )
    analysis_text = models.TextField('Tahlil matni', blank=True)
    match_score = models.FloatField('Moslik %', default=0)
    title = models.CharField('Sarlavha', max_length=255, blank=True)
    description = models.TextField('Tavsif', blank=True)
    status = models.CharField(
        'Holat',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    external_payload = models.JSONField('Tashqi sayt ma\'lumoti', default=dict, blank=True)
    issue = models.ForeignKey(
        'Issue',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='application_submissions',
        verbose_name='Muammo',
    )
    submitted_at = models.DateTimeField('Yuborilgan', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Murojaat yozuvi'
        verbose_name_plural = 'Murojaat yozuvlari'

    def __str__(self):
        return f'{self.application_type.name} — {self.user}'
