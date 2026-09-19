import django_filters

from .models import PublicLand


class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass


class PublicLandFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name='category_id')
    category_code = django_filters.CharFilter(field_name='category__code')
    status = django_filters.CharFilter()
    monitoring_year = django_filters.NumberFilter(field_name='monitoring_year')
    # Bir nechta yil: ?monitoring_years=2018,2020,2022
    monitoring_years = NumberInFilter(field_name='monitoring_year')
    mahalla = django_filters.CharFilter(field_name='mahalla', lookup_expr='iexact')
    area_min = django_filters.NumberFilter(field_name='area_sqm', lookup_expr='gte')
    area_max = django_filters.NumberFilter(field_name='area_sqm', lookup_expr='lte')
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    updated_after = django_filters.DateFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = django_filters.DateFilter(field_name='updated_at', lookup_expr='lte')

    class Meta:
        model = PublicLand
        fields = ['category', 'status', 'is_active', 'monitoring_year']
