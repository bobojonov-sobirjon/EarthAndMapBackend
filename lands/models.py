from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .geo_utils import geometry_metrics


class LandCategory(models.Model):
    class GeometryType(models.TextChoices):
        POINT = 'Point', 'Точка'
        LINE = 'LineString', 'Линия'
        POLYGON = 'Polygon', 'Полигон'

    code = models.SlugField('Код', max_length=50, unique=True)
    name_uz = models.CharField('Название (UZ)', max_length=200)
    name_ru = models.CharField('Название (RU)', max_length=200, blank=True)
    name_en = models.CharField('Название (EN)', max_length=200, blank=True)
    geometry_type = models.CharField(
        'Тип геометрии',
        max_length=20,
        choices=GeometryType.choices,
        default=GeometryType.POLYGON,
    )
    color = models.CharField('Цвет', max_length=7, default='#3388ff')
    icon = models.CharField('Иконка', max_length=50, blank=True)
    description = models.TextField('Описание (UZ)', blank=True)
    description_ru = models.TextField('Описание (RU)', blank=True)
    description_en = models.TextField('Описание (EN)', blank=True)
    is_active = models.BooleanField('Активна', default=True)
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        ordering = ['order', 'name_uz']
        verbose_name = 'Категория земель'
        verbose_name_plural = 'Категории земель'

    def __str__(self):
        return self.name_ru or self.name_uz


class CityBoundary(models.Model):
    """Административная граница (город или область)."""

    class BoundaryType(models.TextChoices):
        CITY = 'city', 'Город'
        REGION = 'region', 'Область'

    code = models.SlugField('Код', max_length=50, default='bukhara_city')
    monitoring_year = models.PositiveSmallIntegerField(
        'Monitoring yili',
        default=2026,
        db_index=True,
    )
    name = models.CharField('Название (UZ)', max_length=100, default='Город Бухара')
    name_ru = models.CharField('Название (RU)', max_length=100, blank=True)
    name_en = models.CharField('Название (EN)', max_length=100, blank=True)
    boundary_type = models.CharField(
        'Тип границы',
        max_length=20,
        choices=BoundaryType.choices,
        default=BoundaryType.CITY,
    )
    geometry = models.JSONField('Геометрия', help_text='GeoJSON Polygon')
    color = models.CharField('Цвет', max_length=7, default='#ff6b00')
    weight = models.PositiveSmallIntegerField('Толщина линии', default=4)
    dash_array = models.CharField('Пунктир (dash)', max_length=20, blank=True, default='')
    fill_opacity = models.FloatField('Прозрачность заливки', default=0.04)
    is_visible = models.BooleanField('Видима', default=True)
    order = models.PositiveIntegerField('Порядок', default=0)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Административная граница'
        verbose_name_plural = 'Административные границы'
        constraints = [
            models.UniqueConstraint(
                fields=['code', 'monitoring_year'],
                name='lands_cityboundary_code_year_uniq',
            ),
        ]

    def __str__(self):
        return self.name


class PublicLand(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Хорошее / Активен'
        UNDER_CONSTRUCTION = 'construction', 'Строительство'
        DAMAGED = 'damaged', 'Повреждён'
        CLOSED = 'closed', 'Закрыт'
        PLANNED = 'planned', 'Запланирован'

    class RoadClass(models.TextChoices):
        MAGISTRAL = 'magistral', 'Магистральные'
        SHAHAR = 'shahar', 'Городские / районные'
        MAHALLIY = 'mahalliy', 'Местные'
        PIYODA = 'piyoda', 'Пешеходные'
        # Sug'orish
        KANAL = 'kanal', 'Каналы'
        ARIQ = 'ariq', 'Арыки'
        # Istirohat (SHP fclass)
        PARK = 'park', 'Парки'
        XIYOBON = 'xiyobon', 'Бульвары / хиёбон'
        SQUARE = 'square', 'Площади / майдон'

    class Condition(models.TextChoices):
        GOOD = 'good', 'Хорошее'
        NORMAL = 'normal', 'Удовлетворительное'
        BAD = 'bad', 'Плохое'

    category = models.ForeignKey(
        LandCategory,
        on_delete=models.PROTECT,
        related_name='lands',
        verbose_name='Категория',
    )
    public_id = models.CharField(
        'Публичный ID',
        max_length=40,
        unique=True,
        null=True,
        blank=True,
        help_text='Например PARK-001, ROAD-I-001',
    )
    name = models.CharField('Название (UZ)', max_length=255)
    name_ru = models.CharField('Название (RU)', max_length=255, blank=True)
    name_en = models.CharField('Название (EN)', max_length=255, blank=True)
    cadastral_number = models.CharField('Кадастровый номер', max_length=100, blank=True)
    address = models.CharField('Адрес (UZ)', max_length=500, blank=True)
    address_ru = models.CharField('Адрес (RU)', max_length=500, blank=True)
    address_en = models.CharField('Адрес (EN)', max_length=500, blank=True)
    mahalla = models.CharField('Махалля', max_length=200, blank=True)
    description = models.TextField('Описание (UZ)', blank=True)
    description_ru = models.TextField('Описание (RU)', blank=True)
    description_en = models.TextField('Описание (EN)', blank=True)
    data_source = models.CharField('Источник данных', max_length=200, blank=True, default='GIS / OSM')

    geometry = models.JSONField('Геометрия', help_text='Геометрия GeoJSON')
    area_sqm = models.FloatField(
        'Площадь (м²)',
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )
    length_m = models.FloatField(
        'Длина (м)',
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )

    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    condition = models.CharField(
        'Состояние',
        max_length=20,
        choices=Condition.choices,
        default=Condition.GOOD,
        blank=True,
    )
    road_class = models.CharField(
        'Класс дороги',
        max_length=20,
        choices=RoadClass.choices,
        blank=True,
        default='',
    )
    monitoring_year = models.PositiveIntegerField(
        'Год мониторинга',
        default=2026,
        help_text='Актуальный год версии объекта',
    )
    responsible_org = models.CharField('Ответственная организация', max_length=255, blank=True)
    acquisition_date = models.DateField('Дата постановки на учёт', null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_lands',
        verbose_name='Создал',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_lands',
        verbose_name='Обновил',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Объект реестра (земля общего пользования)'
        verbose_name_plural = 'Объекты реестра'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),
            models.Index(fields=['public_id']),
            models.Index(fields=['monitoring_year']),
        ]

    def __str__(self):
        return f'{self.public_id or "—"} · {self.name}'

    def save(self, *args, **kwargs):
        if self.geometry:
            area, length = geometry_metrics(self.geometry)
            if area is not None:
                self.area_sqm = area
            if length is not None:
                self.length_m = length
        if not self.public_id:
            from .registry_utils import next_public_id
            self.public_id = next_public_id(
                self.category.code if self.category_id else 'obj',
                self.road_class or '',
            )
        super().save(*args, **kwargs)

    @property
    def area_ha(self):
        from .registry_utils import sqm_to_ha
        return sqm_to_ha(self.area_sqm)

    @property
    def length_km(self):
        from .registry_utils import m_to_km
        return m_to_km(self.length_m)


class LandAttachment(models.Model):
    class FileType(models.TextChoices):
        IMAGE = 'image', 'Изображение'
        DOCUMENT = 'document', 'Документ'
        OTHER = 'other', 'Другое'

    land = models.ForeignKey(
        PublicLand,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='Объект',
    )
    file = models.FileField('Файл', upload_to='land_attachments/%Y/%m/')
    file_type = models.CharField(
        'Тип файла',
        max_length=20,
        choices=FileType.choices,
        default=FileType.IMAGE,
    )
    title = models.CharField('Заголовок', max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Загрузил',
    )
    uploaded_at = models.DateTimeField('Загружено', auto_now_add=True)

    class Meta:
        verbose_name = 'Вложение'
        verbose_name_plural = 'Вложения'

    def __str__(self):
        return self.title or self.file.name


class MonitoringYear(models.Model):
    """Годы мониторинга (2018–2026) и урбанизации (2000–2025)."""

    class YearType(models.TextChoices):
        MONITORING = 'monitoring', 'Мониторинг земель'
        URBANIZATION = 'urbanization', 'Урбанизация'

    year = models.PositiveIntegerField('Год')
    year_type = models.CharField(
        'Тип',
        max_length=20,
        choices=YearType.choices,
        default=YearType.MONITORING,
    )
    is_current = models.BooleanField('Текущий', default=False)
    is_active = models.BooleanField('Активен', default=True)
    note = models.CharField('Примечание', max_length=255, blank=True)

    class Meta:
        ordering = ['year_type', 'year']
        unique_together = [('year', 'year_type')]
        verbose_name = 'Год мониторинга'
        verbose_name_plural = 'Годы мониторинга'

    def __str__(self):
        return f'{self.year} ({self.get_year_type_display()})'


class ObjectVersion(models.Model):
    """Снимок объекта за год — старые данные не перезаписываются."""

    land = models.ForeignKey(
        PublicLand,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='Объект',
    )
    year = models.PositiveIntegerField('Год')
    geometry = models.JSONField('Геометрия', null=True, blank=True)
    area_sqm = models.FloatField('Площадь (м²)', null=True, blank=True)
    length_m = models.FloatField('Длина (м)', null=True, blank=True)
    status = models.CharField('Статус', max_length=20, blank=True)
    condition = models.CharField('Состояние', max_length=20, blank=True)
    change_note = models.CharField('Примечание об изменении', max_length=500, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        ordering = ['-year']
        unique_together = [('land', 'year')]
        verbose_name = 'Версия объекта'
        verbose_name_plural = 'Версии объектов'

    def __str__(self):
        return f'{self.land.public_id} @ {self.year}'

    @property
    def area_ha(self):
        from .registry_utils import sqm_to_ha
        return sqm_to_ha(self.area_sqm)


class MonitoringRecord(models.Model):
    """Запись мониторинга изменений."""

    class RecordStatus(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        APPROVED = 'approved', 'Подтверждено'
        REJECTED = 'rejected', 'Отклонено'

    land = models.ForeignKey(
        PublicLand,
        on_delete=models.CASCADE,
        related_name='monitoring_records',
        verbose_name='Объект',
    )
    year = models.PositiveIntegerField('Год')
    description = models.TextField('Описание изменения (UZ)')
    description_ru = models.TextField('Описание (RU)', blank=True)
    description_en = models.TextField('Описание (EN)', blank=True)
    delta_area_ha = models.FloatField('Δ площадь (га)', default=0)
    delta_length_km = models.FloatField('Δ длина (км)', default=0)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=RecordStatus.choices,
        default=RecordStatus.APPROVED,
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Записал',
    )
    recorded_at = models.DateTimeField('Дата записи', auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        verbose_name = 'Запись мониторинга'
        verbose_name_plural = 'Записи мониторинга'

    def __str__(self):
        return f'{self.land.public_id}: {self.description[:40]}'


class UrbanizationLayer(models.Model):
    """Тематические слои урбанизации 2000–2025."""

    class LayerKind(models.TextChoices):
        URBAN = 'urban', 'Городская территория'
        AGRICULTURE = 'agriculture', 'Сельхозугодья'
        OTHER = 'other', 'Прочее'

    year = models.PositiveIntegerField('Год')
    name = models.CharField('Название (UZ)', max_length=200)
    name_ru = models.CharField('Название (RU)', max_length=200, blank=True)
    name_en = models.CharField('Название (EN)', max_length=200, blank=True)
    layer_kind = models.CharField(
        'Тип слоя',
        max_length=20,
        choices=LayerKind.choices,
        default=LayerKind.URBAN,
    )
    geometry = models.JSONField('Геометрия', null=True, blank=True)
    area_ha = models.FloatField('Площадь (га)', default=0)
    growth_pct = models.FloatField('Прирост (%)', default=0)
    color = models.CharField('Цвет', max_length=7, default='#e74c3c')
    is_visible = models.BooleanField('Видим', default=True)
    note = models.TextField('Примечание (UZ)', blank=True)
    note_ru = models.TextField('Примечание (RU)', blank=True)
    note_en = models.TextField('Примечание (EN)', blank=True)

    class Meta:
        ordering = ['year', 'layer_kind']
        verbose_name = 'Слой урбанизации'
        verbose_name_plural = 'Слои урбанизации'

    def __str__(self):
        return f'{self.year} — {self.name}'


class UrbanizationRasterSet(models.Model):
    """Yil bo'yicha urbanizatsiya: RGB + klassifikatsiya (GeoTIFF)."""

    year = models.PositiveIntegerField('Yil', unique=True)
    title = models.CharField('Sarlavha', max_length=255, blank=True)
    rgb_tif = models.FileField('RGB GeoTIFF', upload_to='urbanization/rgb/')
    classified_tif = models.FileField('Klassifikatsiya GeoTIFF', upload_to='urbanization/classified/')
    rgb_preview = models.ImageField('RGB preview', upload_to='urbanization/previews/', blank=True)
    classified_preview = models.ImageField('Klassifikatsiya preview', upload_to='urbanization/previews/', blank=True)
    rgb_bounds = models.JSONField('RGB bounds', default=list, blank=True)
    classified_bounds = models.JSONField('Klassifikatsiya bounds', default=list, blank=True)
    rgb_label = models.CharField('RGB yorliq', max_length=120, default='Landsat 7 ETM+ RGB')
    classified_label = models.CharField(
        'Klassifikatsiya yorliq',
        max_length=120,
        default='Urban extraction (ISO Cluster)',
    )
    urban_area_ha = models.FloatField('Urban maydon (ga)', null=True, blank=True)
    non_urban_area_ha = models.FloatField('Non-urban maydon (ga)', null=True, blank=True)
    note = models.TextField('Izoh', blank=True)
    is_visible = models.BooleanField('Ko\'rinadi', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year']
        verbose_name = 'Urbanizatsiya xaritasi'
        verbose_name_plural = 'Urbanizatsiya xaritalari'

    def __str__(self):
        return f'Urban {self.year}'


class UrbanizationVectorYear(models.Model):
    """Yil bo'yicha urbanizatsiya klassifikatsiyasi (shapefile → GeoJSON)."""

    year = models.PositiveIntegerField('Yil', unique=True)
    geojson = models.FileField('GeoJSON', upload_to='urbanization/vector/', blank=True)
    class_field = models.CharField('Klass maydoni', max_length=64, default='class')
    feature_count = models.PositiveIntegerField('Ob\'ektlar soni', default=0)
    urban_area_ha = models.FloatField('Urban maydon (ga)', null=True, blank=True)
    non_urban_area_ha = models.FloatField('Non-urban maydon (ga)', null=True, blank=True)
    bounds = models.JSONField('Bounds', default=list, blank=True)
    source_name = models.CharField('Manba fayl', max_length=255, blank=True)
    note = models.TextField('Izoh', blank=True)
    is_visible = models.BooleanField('Ko\'rinadi', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year']
        verbose_name = 'Urbanizatsiya vektor qatlami'
        verbose_name_plural = 'Urbanizatsiya vektor qatlamlari'

    def __str__(self):
        return f'Urban vector {self.year}'


class SystemNotice(models.Model):
    """Сообщения администратора на главной панели."""

    title = models.CharField('Заголовок (UZ)', max_length=200)
    title_ru = models.CharField('Заголовок (RU)', max_length=200, blank=True)
    title_en = models.CharField('Заголовок (EN)', max_length=200, blank=True)
    message = models.TextField('Текст (UZ)')
    message_ru = models.TextField('Текст (RU)', blank=True)
    message_en = models.TextField('Текст (EN)', blank=True)
    is_active = models.BooleanField('Активно', default=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Сообщение администратора'
        verbose_name_plural = 'Сообщения администратора'

    def __str__(self):
        return self.title


class Mahalla(models.Model):
    """Махалли города Бухара."""

    name = models.CharField('Название (UZ)', max_length=200)
    name_ru = models.CharField('Название (RU)', max_length=200, blank=True)
    name_en = models.CharField('Название (EN)', max_length=200, blank=True)
    code = models.SlugField('Код', max_length=50, unique=True)
    geometry = models.JSONField('Геометрия', null=True, blank=True)
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Махалля'
        verbose_name_plural = 'Махалли'

    def __str__(self):
        return self.name