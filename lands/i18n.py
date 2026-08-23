LANGS = ('uz', 'ru', 'en')


def request_lang(request):
    raw = ''
    if request is not None:
        raw = (
            request.query_params.get('lang')
            or request.headers.get('X-Lang')
            or request.headers.get('Accept-Language', '')
        )
    lang = (raw or 'uz')[:2].lower()
    return lang if lang in LANGS else 'uz'


def pick(uz='', ru='', en='', lang='uz'):
    uz, ru, en = uz or '', ru or '', en or ''
    if lang == 'ru':
        return ru or uz or en
    if lang == 'en':
        return en or uz or ru
    return uz or ru or en
