from django.http import HttpResponse, HttpResponseBadRequest
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole, IsNotObserver

from .application_analysis import analyze_text_against_types
from .embed_proxy import fetch_embed_safe, is_allowed_embed_url, normalize_https_url
from .models import ApplicationOnSite, ApplicationSubmission, ApplicationType, ChangeLog, Issue
from .serializers import (
    ApplicationOnSiteSerializer,
    ApplicationSubmissionCreateSerializer,
    ApplicationSubmissionSerializer,
    ApplicationTypeSerializer,
    ChangeLogSerializer,
    IssueSerializer,
    ProblemAnalysisSerializer,
)


class ChangeLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ChangeLog.objects.select_related('land', 'changed_by')
    serializer_class = ChangeLogSerializer
    filterset_fields = ['land', 'change_type']
    ordering_fields = ['changed_at']


class IssueViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.select_related('land', 'reported_by', 'assigned_to')
    serializer_class = IssueSerializer
    filterset_fields = ['status', 'severity', 'land']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'severity']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        if self.action == 'create':
            return [IsAuthenticated()]
        return [IsNotObserver()]

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)


class ApplicationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ApplicationType.objects.filter(is_active=True).prefetch_related('sites')
    serializer_class = ApplicationTypeSerializer
    permission_classes = [AllowAny]


class ApplicationSubmissionViewSet(viewsets.ModelViewSet):
    queryset = ApplicationSubmission.objects.select_related(
        'application_type', 'site', 'user', 'issue',
    )
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ApplicationSubmissionCreateSerializer
        return ApplicationSubmissionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff or getattr(user, 'role', '') == 'admin':
            return qs
        return qs.filter(user=user)

    def _finalize_submission(self, submission: ApplicationSubmission):
        if submission.status != ApplicationSubmission.Status.SUBMITTED:
            submission.status = ApplicationSubmission.Status.SUBMITTED
            submission.submitted_at = timezone.now()

        if not submission.issue_id:
            title = (submission.title or submission.application_type.name)[:255]
            desc = submission.description or submission.analysis_text or ''
            issue = Issue.objects.create(
                title=title,
                description=desc,
                severity=Issue.Severity.MEDIUM,
                status=Issue.IssueStatus.NEW,
                reported_by=submission.user,
            )
            submission.issue = issue
        submission.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save(user=request.user)
        if request.data.get('status') == ApplicationSubmission.Status.SUBMITTED:
            self._finalize_submission(submission)
        out = ApplicationSubmissionSerializer(submission, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        submission = self.get_object()
        serializer = self.get_serializer(submission, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()
        if request.data.get('status') == ApplicationSubmission.Status.SUBMITTED:
            self._finalize_submission(submission)
        out = ApplicationSubmissionSerializer(submission, context={'request': request})
        return Response(out.data)


class ProblemAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ProblemAnalysisSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        text = ser.validated_data['text']

        types = []
        for t in ApplicationType.objects.filter(is_active=True).prefetch_related('sites'):
            site = t.sites.filter(is_active=True).first()
            types.append({
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'site_url': site.site_url if site else '',
            })

        results = analyze_text_against_types(text, types)
        return Response({
            'text': text,
            'results': results,
            'analyzed_at': timezone.now().isoformat(),
        })


class EmbedProxyView(APIView):
    """gov.uz sahifasini ichki ko'rinish uchun proxy (Selenium screenshot)."""
    permission_classes = [AllowAny]

    def get(self, request):
        raw = request.GET.get('url', '')
        url = normalize_https_url(raw)
        if not url or not is_allowed_embed_url(url):
            return HttpResponseBadRequest('Noto\'g\'ri URL')

        use_screenshot = request.GET.get('screenshot', '1') == '1'
        result = None

        if use_screenshot:
            from django.conf import settings
            from .embed_selenium import capture_screenshot
            wait = int(getattr(settings, 'EMBED_SELENIUM_WAIT_SEC', 10))
            png = capture_screenshot(url, wait_sec=wait)
            if png:
                resp = HttpResponse(png, content_type='image/png')
                resp['Cache-Control'] = 'no-store, no-cache, must-revalidate'
                resp['X-Frame-Options'] = 'SAMEORIGIN'
                resp['Content-Security-Policy'] = "frame-ancestors 'self' http://localhost:* http://127.0.0.1:*"
                return resp

        result = fetch_embed_safe(url, use_selenium=not use_screenshot)
        if not result:
            html = (
                '<!doctype html><html><body style="font-family:sans-serif;padding:1.5rem;background:#0f172a;color:#e2e8f0">'
                '<p>Sahifa yuklanmadi.</p>'
                f'<p><a href="{url}" target="_blank" rel="noopener" style="color:#38bdf8">{url}</a></p>'
                '</body></html>'
            )
            resp = HttpResponse(html, status=200, content_type='text/html; charset=utf-8')
        else:
            body, ctype = result
            resp = HttpResponse(body, content_type=ctype)

        resp['X-Frame-Options'] = 'SAMEORIGIN'
        resp['Content-Security-Policy'] = "frame-ancestors 'self' http://localhost:* http://127.0.0.1:*"
        return resp


class ApplicationOnSiteAdminViewSet(viewsets.ModelViewSet):
    queryset = ApplicationOnSite.objects.select_related('application_type').all()
    serializer_class = ApplicationOnSiteSerializer
    permission_classes = [IsAdminRole]


class ApplicationTypeAdminViewSet(viewsets.ModelViewSet):
    queryset = ApplicationType.objects.prefetch_related('sites').all()
    serializer_class = ApplicationTypeSerializer
    permission_classes = [IsAdminRole]
