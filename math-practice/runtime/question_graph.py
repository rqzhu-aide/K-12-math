"""Validate imported question references against the installed mathematics graph."""
from copy import deepcopy

from knowledge_graph import (GraphError, graph_version as database_graph_version,
                             mapping_record, node_ids, question_fingerprint, validate_mapping,
                             validate_heading_context)
from question_answers import confirmed_grading_notice
from question_banks import ROOT


GRAPH_FIELDS = ('contentHash', 'status', 'reviewStatus', 'assessedIds', 'supportIds', 'routes', 'flags')
GRADING_FIELDS = ('gradingStatus', 'gradingNote')


def graph_payload(mapping, version):
    """The portable question stub; evidence and topology remain central."""
    payload = {'version': str(version), **{key: deepcopy(mapping.get(key, [] if key in
               ('assessedIds', 'supportIds', 'routes', 'flags') else None)) for key in GRAPH_FIELDS}}
    payload.update(confirmed_grading_notice(mapping.get('answerCheck')) or {})
    if 'headingContext' in mapping:
        payload['headingContext'] = mapping['headingContext']
    if 'contextualIds' in mapping:
        payload['contextualIds'] = deepcopy(mapping['contextualIds'])
    return payload


def validate_imported_references(question, root=ROOT, *, bank_root=None):
    """Check explicit custom references without turning a supplied claim into a review.

    An exact copy of a central mapping keeps its recorded review provenance.
    Other valid references must say user_asserted; ordinary banks need no graph.
    """
    if 'KnowledgeGraph' not in question:
        return
    stub = question['KnowledgeGraph']
    required = {'version', *GRAPH_FIELDS}
    if not isinstance(stub, dict) or not required.issubset(stub):
        raise GraphError('KnowledgeGraph must contain version, contentHash, status, reviewStatus, '
                         'assessedIds, supportIds, routes and flags.')
    try:
        ids = node_ids(root=root)
        version = database_graph_version(root=root)
        central = mapping_record(question['ID'], root=root)
    except GraphError as exc:
        raise GraphError('Explicit KnowledgeGraph references need the installed central graph database. '
                         f'Build it first, or omit KnowledgeGraph for ordinary practice. ({exc})') from None
    if stub['version'] != version:
        raise GraphError('KnowledgeGraph.version differs from the installed graph; refresh the references.')
    fingerprint = question_fingerprint(question, root=root, bank_root=bank_root)
    if stub['contentHash'] != fingerprint['contentHash']:
        raise GraphError('KnowledgeGraph content binding is stale; remap the displayed question and figures.')
    validate_heading_context(stub, question)
    if (central is not None and central.get('bank') == question.get('Bank')
            and central.get('contentHash') == fingerprint['contentHash']
            and central.get('figureHashes') == fingerprint['figureHashes']
            and central.get('headingContext') == stub.get('headingContext')
            and central.get('contextualIds', []) == stub.get('contextualIds', [])
            and all(stub[key] == graph_payload(central, version)[key] for key in required)):
        validate_mapping(central, ids)
        # These are controlled projections of central adjudication, not claims
        # accepted from an imported stub. Refresh older exact central exports.
        notice = confirmed_grading_notice(central.get('answerCheck')) or {}
        for field in GRADING_FIELDS:
            if field in notice:
                stub[field] = notice[field]
            else:
                stub.pop(field, None)
        return
    if any(field in stub for field in GRADING_FIELDS):
        raise GraphError('Imported graph grading notices must come from an exact central mapping. '
                         'Omit gradingStatus and gradingNote from user_asserted graph references.')
    if stub['reviewStatus'] != 'user_asserted':
        raise GraphError('Imported graph references do not match a central reviewed mapping. '
                         'Use reviewStatus "user_asserted", or refresh them from the central mapping.')
    mapping = {key: deepcopy(stub[key]) for key in GRAPH_FIELDS}
    if 'headingContext' in stub:
        mapping['headingContext'] = stub['headingContext']
    if 'contextualIds' in stub:
        mapping['contextualIds'] = deepcopy(stub['contextualIds'])
    mapping.update(questionId=question['ID'], bank=question['Bank'],
                   figureHashes=fingerprint['figureHashes'],
                   rationale='User-provided references; no central review is asserted.',
                   answerCheck={'status': 'not_independently_reviewed'}, reviews=[])
    validate_mapping(mapping, ids)


