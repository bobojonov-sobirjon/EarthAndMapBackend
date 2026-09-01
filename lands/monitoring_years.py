"""Bazadagi monitoring yillari — hardcode emas."""
from __future__ import annotations

from .models import CityBoundary, MonitoringYear, ObjectVersion, PublicLand


def collect_monitoring_years(*, include_boundaries: bool = True) -> list[int]:
    """Faol obyektlar, versiyalar va MonitoringYear jadvalidan yillar."""
    years: set[int] = set()

    for y in PublicLand.objects.filter(is_active=True).values_list('monitoring_year', flat=True).distinct():
        if y:
            years.add(int(y))

    for y in ObjectVersion.objects.values_list('year', flat=True).distinct():
        if y:
            years.add(int(y))

    for y in MonitoringYear.objects.filter(
        year_type=MonitoringYear.YearType.MONITORING,
        is_active=True,
    ).values_list('year', flat=True):
        if y:
            years.add(int(y))

    if include_boundaries:
        for y in CityBoundary.objects.filter(is_visible=True).values_list('monitoring_year', flat=True).distinct():
            if y:
                years.add(int(y))

    return sorted(years)


def latest_monitoring_year(years: list[int] | None = None) -> int | None:
    items = years if years is not None else collect_monitoring_years()
    return max(items) if items else None
