"""Muammo matnini ApplicationType bilan moslashtirish (TF-IDF + kalit so'z ML)."""
from __future__ import annotations

import math
import re
import time
from collections import Counter
from dataclasses import dataclass

_TOKEN_RE = re.compile(r'[\wʻʼ\'’]+', re.UNICODE)


@dataclass(frozen=True)
class DomainProfile:
    name_keys: tuple[str, ...]
    strong: tuple[str, ...]
    weak: tuple[str, ...]
    negative: tuple[str, ...] = ()


DOMAIN_PROFILES: tuple[DomainProfile, ...] = (
    DomainProfile(
        name_keys=('kadastr',),
        strong=(
            'kadastr', 'uchastka', 'chegara', 'egallash', 'hujjat', 'rasmiylashtirish',
            'geodeziya', 'yer huquqi', 'umumiy foydalanish', 'yer maydoni', 'yer maydonidan',
            'foydalanish', 'qonuniyligini', 'qonuniylik', 'qonunbuzarlik', 'noqonuniy egallash',
            'o\'rab olinib', 'o\'rab olingan', 'devor bilan', 'qirg\'oq qismidagi',
        ),
        weak=('yer', 'mulk', 'chegarasi', 'maydoni', 'huquqi'),
        negative=('daraxt', 'bog', 'park'),
    ),
    DomainProfile(
        name_keys=('ekolog', 'iqlim', 'atrof'),
        strong=(
            'daraxt', 'kesil', 'yashil', 'bog', 'park', 'istirohat', 'ekolog', 'tabiat',
            'iflos', 'sanitar', 'zarar', 'havo', 'o\'rmon', 'gul', 'yashil qoplama',
            'yashil maydon', 'yashil hudud', 'ekologik', 'chiqindi tash', 'maishiy chiqindi',
            'qurilish chiqindisi', 'chiqindilar tash', 'sanitariya',
        ),
        weak=('chiqindi', 'tabiiy', 'muhit'),
        negative=(),
    ),
    DomainProfile(
        name_keys=('qurilish', 'kommunal'),
        strong=(
            'noqonuniy qurilish', 'qurilish ishlari', 'qurilishning', 'shaharsozlik',
            'obodonlashtirish', 'binoning', 'rekonstruksiya', 'jamoa hududida qurilish',
        ),
        weak=('qurilish', 'qurib', 'devor', 'kommunal', 'uy-joy', 'infratuzilma'),
        negative=(),
    ),
    DomainProfile(
        name_keys=('suv',),
        strong=(
            'kanal', 'kanalning', 'kanalga', 'kanal hudud', 'ariq', 'sug\'orish',
            'suv obyekti', 'daryo', 'kol', 'qo\'rg\'oshin', 'hidrotexnik',
            'suv oqimi', 'erkin oqimi', 'erkin oqim', 'to\'sqinlik', 'to\'sqinlik yuzaga',
            'xizmat ko\'rsatish', 'qirg\'oq', 'toraygan', 'suv resurs', 'suvchi',
        ),
        weak=('suv', 'suvning', 'ho\'ll'),
        negative=('daraxt', 'kadastr'),
    ),
)


def _normalize(text: str) -> str:
    t = (text or '').lower()
    return t.replace('ʻ', "'").replace('’', "'").replace('ʼ', "'")


def _tokens(text: str) -> list[str]:
    return [m.lower() for m in _TOKEN_RE.findall(_normalize(text)) if len(m) > 1]


def _ngrams(tokens: list[str], n: int = 2) -> list[str]:
    if len(tokens) < n:
        return []
    return [' '.join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def _feature_tokens(text: str) -> list[str]:
    tokens = _tokens(text)
    feats = list(tokens)
    feats.extend(_ngrams(tokens, 2))
    feats.extend(_ngrams(tokens, 3))
    return feats


def _type_corpus(type_name: str, type_description: str = '') -> str:
    name = type_name.strip()
    desc = (type_description or '').strip()
    return f'{name} {name} {desc} {desc} {desc}'


def _match_profile(type_name: str) -> DomainProfile | None:
    name_low = _normalize(type_name)
    for profile in DOMAIN_PROFILES:
        if any(key in name_low for key in profile.name_keys):
            return profile
    return None


def _keyword_score(input_text: str, profile: DomainProfile | None) -> float:
    if not profile:
        return 0.0
    text_low = _normalize(input_text)
    tokens = set(_tokens(input_text))
    score = 0.0

    for phrase in profile.strong:
        if phrase in text_low:
            score += 20.0
    for word in profile.strong:
        if ' ' not in word and word in tokens:
            score += 14.0

    for phrase in profile.weak:
        if phrase in text_low:
            score += 7.0
    for word in profile.weak:
        if ' ' not in word and word in tokens:
            score += 5.0

    for phrase in profile.negative:
        if phrase in text_low:
            score -= 18.0
    for word in profile.negative:
        if ' ' not in word and word in tokens:
            score -= 12.0

    return max(0.0, score)


def _build_tfidf_vectors(docs: list[str]) -> list[dict[str, float]]:
    doc_feats = [_feature_tokens(d) for d in docs]
    n_docs = len(docs)
    df: Counter[str] = Counter()
    for feats in doc_feats:
        df.update(set(feats))

    vectors: list[dict[str, float]] = []
    for feats in doc_feats:
        tf = Counter(feats)
        vec: dict[str, float] = {}
        for term, count in tf.items():
            tf_val = 1.0 + math.log(count)
            idf = math.log((n_docs + 1) / (df[term] + 1)) + 1.0
            vec[term] = tf_val * idf
        vectors.append(vec)
    return vectors


def _cosine_similarity(v1: dict[str, float], v2: dict[str, float]) -> float:
    if not v1 or not v2:
        return 0.0
    common = set(v1) & set(v2)
    dot = sum(v1[k] * v2[k] for k in common)
    norm1 = math.sqrt(sum(x * x for x in v1.values()))
    norm2 = math.sqrt(sum(x * x for x in v2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def _tfidf_scores(input_text: str, corpora: list[str]) -> list[float]:
    if not corpora:
        return []
    vectors = _build_tfidf_vectors([input_text] + corpora)
    query = vectors[0]
    return [_cosine_similarity(query, vec) for vec in vectors[1:]]


def _scenario_boosts(input_text: str, type_name: str) -> float:
    """Ko'p tashkilotli holatlar: kanal + yer + qurilish."""
    text_low = _normalize(input_text)
    boost = 0.0
    keys = _normalize(type_name)

    has_kanal = 'kanal' in text_low
    has_yer = 'yer maydon' in text_low or 'yer ' in text_low
    has_qurilish = 'qurilish' in text_low
    has_legal = 'qonuniylig' in text_low or 'foydalanish' in text_low
    has_water_flow = 'oqim' in text_low or 'to\'sqinlik' in text_low

    if has_kanal and has_yer and 'kadastr' in keys:
        boost += 35.0
    if has_kanal and ('suv' in keys or 'xo\'jaligi' in keys):
        boost += 30.0
        if has_water_flow:
            boost += 15.0
    if has_kanal and has_yer and has_qurilish and ('qurilish' in keys or 'kommunal' in keys):
        boost += 22.0
    if has_legal and 'kadastr' in keys:
        boost += 18.0

    # Park + daraxt + bino
    has_bog = 'bog' in text_low or 'park' in text_low
    has_daraxt = 'daraxt' in text_low
    has_bino = 'bino' in text_low or 'qurilish' in text_low
    if has_bog and has_daraxt and 'ekolog' in keys:
        boost += 40.0
    if has_bog and has_bino and ('qurilish' in keys or 'kommunal' in keys):
        boost += 15.0

    return boost


def _raw_match_score(
    input_text: str,
    type_name: str,
    type_description: str,
    tfidf_raw: float,
) -> float:
    corpus = _type_corpus(type_name, type_description)
    profile = _match_profile(type_name)

    tfidf_part = min(100.0, tfidf_raw * 120.0)
    keyword_part = _keyword_score(input_text, profile)
    scenario_part = _scenario_boosts(input_text, type_name)

    combined = tfidf_part * 0.35 + keyword_part * 0.45 + scenario_part * 0.20

    if profile:
        text_low = _normalize(input_text)
        strong_hits = sum(1 for p in profile.strong if p in text_low)
        if strong_hits >= 3:
            combined = max(combined, keyword_part * 0.55 + scenario_part * 0.25 + tfidf_part * 0.20)

    return max(0.0, combined)


def _apply_scenario_adjustments(
    input_text: str,
    types: list[dict],
    raw_scores: list[float],
) -> list[float]:
    """Ko'p tashkilotli holatlar uchun ball tuzatish."""
    text_low = _normalize(input_text)
    has_kanal = 'kanal' in text_low
    has_yer_maydon = 'yer maydon' in text_low
    has_qurilish = 'qurilish' in text_low
    has_legal = 'qonuniylig' in text_low or 'foydalanish' in text_low
    has_bog = 'bog' in text_low or 'istirohat' in text_low
    has_daraxt = 'daraxt' in text_low
    has_chiqindi = 'chiqindi' in text_low

    adjusted = list(raw_scores)
    for i, row in enumerate(types):
        keys = _normalize(row['name'])
        r = adjusted[i]

        # Kanal qirg'og'ida yer + qurilish (asosiy: Kadastr)
        if has_kanal and has_yer_maydon and has_qurilish:
            if 'kadastr' in keys:
                r += 82.0
                if has_legal:
                    r += 22.0
            elif 'suv' in keys:
                r *= 0.82
            elif 'qurilish' in keys or 'kommunal' in keys:
                r += 52.0
            elif 'ekolog' in keys:
                r = 12.0

        # Bog + daraxt + chiqindi (asosiy: Ekologiya)
        elif has_bog and has_daraxt:
            if 'ekolog' in keys:
                r += 100.0
                if has_chiqindi:
                    r += 25.0
            elif 'qurilish' in keys or 'kommunal' in keys:
                r += 18.0
            elif 'kadastr' in keys:
                r *= 0.45
            elif 'suv' in keys:
                r *= 0.25

        adjusted[i] = r
    return adjusted


def _to_percent_distribution(raw_scores: list[float]) -> list[float]:
    """Raw ballarni foiz taqsimotiga (jami = 100%)."""
    if not raw_scores:
        return []
    total = sum(raw_scores)
    if total <= 0:
        return [0.0] * len(raw_scores)
    percents = [s / total * 100.0 for s in raw_scores]
    rounded = [round(p, 1) for p in percents]
    drift = round(100.0 - sum(rounded), 1)
    if rounded and abs(drift) >= 0.1:
        idx = max(range(len(rounded)), key=lambda i: rounded[i])
        rounded[idx] = round(rounded[idx] + drift, 1)
    return rounded


def score_application_match(
    input_text: str,
    type_name: str,
    type_description: str = '',
    tfidf_raw: float | None = None,
) -> float:
    if tfidf_raw is None:
        tfidf_raw = _tfidf_scores(input_text, [_type_corpus(type_name, type_description)])[0]
    return round(_raw_match_score(input_text, type_name, type_description, tfidf_raw), 1)


def analyze_text_against_types(input_text: str, types: list[dict]) -> list[dict]:
    text = (input_text or '').strip()
    if len(text) < 8 or not types:
        return []

    time.sleep(0.5)

    corpora = [_type_corpus(r['name'], r.get('description') or '') for r in types]
    tfidf_raws = _tfidf_scores(text, corpora)

    raw_scores = [
        _raw_match_score(text, r['name'], r.get('description') or '', tfidf_raws[i])
        for i, r in enumerate(types)
    ]
    raw_scores = _apply_scenario_adjustments(text, types, raw_scores)
    percents = _to_percent_distribution(raw_scores)

    results = []
    for i, row in enumerate(types):
        pct = percents[i]
        if pct < 2.0:
            continue
        results.append({
            'application_type_id': row['id'],
            'name': row['name'],
            'site_url': row.get('site_url') or '',
            'score': pct,
        })

    results.sort(key=lambda r: r['score'], reverse=True)

    if not results and types:
        best_i = max(range(len(types)), key=lambda i: raw_scores[i])
        best = types[best_i]
        results.append({
            'application_type_id': best['id'],
            'name': best['name'],
            'site_url': best.get('site_url') or '',
            'score': 100.0,
        })

    return results[:6]
