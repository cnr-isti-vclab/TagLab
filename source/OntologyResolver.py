import json
import os
import re
from functools import lru_cache
from urllib import request, error

SEMANTIC_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'semantic_config.json')


def normalize_ontology_term(ontology_term):
    if ontology_term is None:
        return ''

    normalized_term = re.sub(r'\s+', '', ontology_term.strip())
    parts = normalized_term.split(':', 1)
    if len(parts) != 2:
        return normalized_term

    return f"{parts[0].lower()}:{parts[1]}"


@lru_cache(maxsize=1)
def load_ontology_prefixes(config_file=SEMANTIC_CONFIG_FILE):
    try:
        with open(config_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    # Backward-compatible: support either flat prefix map or nested config.
    if 'ontology_prefixes' in data and isinstance(data['ontology_prefixes'], dict):
        data = data['ontology_prefixes']

    prefixes = {}
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        normalized_key = key.strip().lower()
        normalized_value = value.strip()
        if normalized_key == '' or normalized_value == '':
            continue
        prefixes[normalized_key] = normalized_value

    return prefixes


def resolve_ontology_uri(ontology_term, prefixes=None):
    normalized_term = normalize_ontology_term(ontology_term)
    if normalized_term == '':
        return ''

    parts = normalized_term.split(':', 1)
    if len(parts) != 2:
        return ''

    prefix = parts[0].strip().lower()
    local_name = parts[1].strip()
    if prefix == '' or local_name == '':
        return ''

    if prefixes is None:
        prefixes = load_ontology_prefixes()

    base_uri = prefixes.get(prefix)
    if base_uri is None:
        return ''

    return f"{base_uri}{local_name}"


def resolve_ontology_term(ontology_uri, prefixes=None):
    if ontology_uri is None:
        return ''

    normalized_uri = ontology_uri.strip()
    if normalized_uri == '':
        return ''

    if prefixes is None:
        prefixes = load_ontology_prefixes()

    best_match = None
    lowered_uri = normalized_uri.lower()

    for prefix, base_uri in prefixes.items():
        lowered_base_uri = base_uri.lower()
        if not lowered_uri.startswith(lowered_base_uri):
            continue

        local_name = normalized_uri[len(base_uri):].strip()
        if local_name == '':
            continue

        match_key = (len(base_uri), -len(prefix), prefix)
        if best_match is None or match_key > best_match[0]:
            best_match = (match_key, prefix, local_name)

    if best_match is None:
        return ''

    _, prefix, local_name = best_match
    return normalize_ontology_term(f"{prefix}:{local_name}")


def _has_network_connectivity(test_url='https://www.w3.org/', timeout=5):
    req = request.Request(test_url, method='HEAD')
    try:
        with request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def _check_uri_online(ontology_uri, timeout=8):
    req = request.Request(ontology_uri, method='GET', headers={'User-Agent': 'TagLab Semantic Validator'})
    try:
        with request.urlopen(req, timeout=timeout) as response:
            status_code = getattr(response, 'status', 200)
            return True, status_code, ''
    except error.HTTPError as http_err:
        # The endpoint is reachable, but the URI may be invalid or blocked.
        return False, http_err.code, f"HTTP {http_err.code}"
    except Exception as ex:
        return False, None, str(ex)


@lru_cache(maxsize=1)
def _load_dcmi_terms_page(timeout=10):
    url = 'https://www.dublincore.org/specifications/dublin-core/dcmi-terms/'
    req = request.Request(url, method='GET', headers={'User-Agent': 'TagLab Semantic Validator'})
    with request.urlopen(req, timeout=timeout) as response:
        return response.read().decode('utf-8', errors='ignore').lower()


def _validate_known_vocab_term(ontology_term, timeout=8):
    normalized_term = normalize_ontology_term(ontology_term)
    parts = normalized_term.split(':', 1)
    if len(parts) != 2:
        return None, ''

    prefix = parts[0].lower()
    local_name = parts[1].strip().lower()
    if local_name == '':
        return None, ''

    # DCMI often dereferences unknown terms to a generic page.
    # We explicitly verify local term existence in the official terms document.
    if prefix in {'dcmi', 'dcterms'}:
        try:
            html = _load_dcmi_terms_page(timeout=timeout)
        except Exception as ex:
            return None, f"Unable to validate DCMI term online: {ex}"

        tokens = (
            f"/terms/{local_name}",
            f"#{local_name}",
            f"/{local_name}\"",
            f">{local_name}<"
        )
        return any(token in html for token in tokens), ''

    return None, ''


def _terms_equivalent(term_a, term_b):
    normalized_a = normalize_ontology_term(term_a)
    normalized_b = normalize_ontology_term(term_b)

    if normalized_a == '' or normalized_b == '':
        return False

    parts_a = normalized_a.split(':', 1)
    parts_b = normalized_b.split(':', 1)
    if len(parts_a) != 2 or len(parts_b) != 2:
        return normalized_a.lower() == normalized_b.lower()

    return parts_a[0].lower() == parts_b[0].lower() and parts_a[1].lower() == parts_b[1].lower()


def check_semantic_mappings(fields, timeout=8):
    report = {
        'network_available': True,
        'items': []
    }

    if not _has_network_connectivity(timeout=timeout):
        report['network_available'] = False
        return report

    prefixes = load_ontology_prefixes()
    for field in fields:
        name = field.get('name', '<unnamed>')
        ontology_term = normalize_ontology_term(field.get('ontology_term', ''))
        ontology_uri = (field.get('ontology_uri', '') or '').strip()

        errors = []
        expected_uri = ''
        inferred_term = ''

        if ontology_term == '' and ontology_uri == '':
            errors.append('Missing ontology term and URI.')

        if ontology_term != '':
            expected_uri = resolve_ontology_uri(ontology_term, prefixes=prefixes)
            if expected_uri == '':
                errors.append('Ontology term has unknown or invalid prefix.')

        if ontology_uri != '':
            inferred_term = resolve_ontology_term(ontology_uri, prefixes=prefixes)
            if inferred_term == '':
                errors.append('Ontology URI does not match configured ontology prefixes.')

        if ontology_term != '' and ontology_uri != '' and expected_uri != '':
            if inferred_term != '':
                if not _terms_equivalent(ontology_term, inferred_term):
                    errors.append(f"Term and URI mismatch. Expected URI from term: {expected_uri}")
            elif expected_uri.lower() != ontology_uri.lower():
                errors.append(f"Term and URI mismatch. Expected URI from term: {expected_uri}")

        if ontology_term != '':
            term_exists, term_check_message = _validate_known_vocab_term(ontology_term, timeout=timeout)
            if term_exists is False:
                errors.append('Ontology term not found in authoritative vocabulary source.')
            elif term_check_message != '':
                errors.append(term_check_message)

        online_ok = False
        http_status = None
        online_message = ''
        uri_to_check = ontology_uri if ontology_uri != '' else expected_uri
        if uri_to_check != '':
            online_ok, http_status, online_message = _check_uri_online(uri_to_check, timeout=timeout)
            if not online_ok:
                errors.append(f"Online check failed for URI ({uri_to_check}): {online_message}")

        report['items'].append({
            'name': name,
            'ontology_term': ontology_term,
            'ontology_uri': ontology_uri,
            'expected_uri': expected_uri,
            'inferred_term': inferred_term,
            'checked_uri': uri_to_check,
            'online_ok': online_ok,
            'http_status': http_status,
            'errors': errors
        })

    return report
