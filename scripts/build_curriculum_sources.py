"""Rebuild native CN/US layers and reviewed crosswalks from packaged evidence.

Offline and deterministic. Never edits the canonical graph or its mappings.
Use --check to verify generated files without writing them.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'knowledge-graph/evidence/curricula'
REVISION_CN = '62b341d4b66b175413d6e3f697e37639fd96aa2d'
BOOKS = {10: '必修一', 11: '必修二', 12: '选必一', 13: '选必二', 14: '选必三'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def digest(content):
    return hashlib.sha256(content).hexdigest()


def stable_id(prefix, *parts):
    return prefix + ':' + digest(json.dumps(parts, ensure_ascii=False, separators=(',', ':')).encode())[:24]


def cn_layer(native):
    nodes = []
    for n in sorted(native['nodes'], key=lambda n: n['id']):
        grade = n['grade']
        placement = {'grade': grade} if grade <= 9 else {'bookCode': str(grade), 'bookLabel': BOOKS[grade]}
        placement.update({k: n[k] for k in ('semester', 'chapter', 'domain') if k in n})
        nodes.append({'id': n['id'], 'label': n['name'], 'description': n['description'],
                      'criteria': n['mastery_criteria'], 'placement': placement, 'original': n,
                      'reviewStatus': 'source_only'})
    relationships = []
    for e in native['relationships']:
        relation = 'prerequisite' if e['strength'] == 'hard' else 'supports'
        relationships.append({'id': stable_id('CN', e['topicId'], e['prerequisiteId'], e['strength']),
            'fromId': e['topicId'], 'toId': e['prerequisiteId'], 'relation': relation,
            'directed': True, 'status': 'accepted', 'reviewStatus': 'source_only',
            'reason': e['reason'], 'original': e,
            'directionMeaning': 'dependent to prerequisite/supporting foundation'})
    return {'id': 'CN', 'label': 'Chinese mathematics bank taxonomy', 'source': native['source'],
        'revision': REVISION_CN, 'placementMeaning': 'Grades 1-9 are literal native grades. Native values 10-14 are book codes: 必修一, 必修二, 选必一, 选必二, 选必三; not grades 10-14.',
        'nodes': nodes, 'relationships': sorted(relationships, key=lambda e: e['id'])}


def us_layer(native):
    nodes = []
    for n in sorted(native['nodes'], key=lambda n: int(n['sourceId'])):
        nodes.append({'id': str(n['sourceId']), 'label': n['code'], 'code': n['code'],
            'description': n['description'], 'parentSourceId': n['parentSourceId'],
            'placement': {'grade': n['grade'], 'meaning': 'High school band, not an exact year' if n['grade'] == 'HS' else 'Native Common Core grade'},
            'metadata': {k: v for k, v in n.items() if k not in ('sourceId', 'code', 'description', 'parentSourceId', 'grade')},
            'reviewStatus': 'source_only'})
    relationships = []
    for e in native['edges']:
        relationships.append({'id': stable_id('US:supports', e['from'], e['to']),
            'fromId': str(e['to']), 'toId': str(e['from']), 'relation': 'supports', 'directed': True,
            'status': 'accepted', 'reviewStatus': 'source_only', 'original': e,
            'directionMeaning': 'dependent to supporting foundation; original A supports B is normalized B to A',
            'claimMeaning': native['source']['edgeSemantics']})
    for e in native['relatedPairs']:
        a, b = sorted((str(e['from']), str(e['to'])), key=int)
        relationships.append({'id': stable_id('US:related', a, b), 'fromId': a, 'toId': b,
            'relation': 'related', 'directed': False, 'status': 'accepted', 'reviewStatus': 'source_only', 'original': e})
    for n in nodes:
        if n['parentSourceId']:
            relationships.append({'id': stable_id('US:contains', n['parentSourceId'], n['id']),
                'fromId': str(n['parentSourceId']), 'toId': n['id'], 'relation': 'contains',
                'directed': True, 'status': 'accepted', 'reviewStatus': 'source_structure',
                'directionMeaning': 'parent standard to child substandard; no prerequisite claim'})
    source = dict(native['source'])
    source['repositoryRevisionMeaning'] = 'Repository source-code revision, not a version claim about the live data snapshot.'
    source['distributionScope'] = 'Local source-backed integration; external data license remains unverified, no external publication authorized.'
    return {'id': 'US', 'label': 'Common Core Coherence Map mathematics', 'source': source,
        'revision': 'sha256:' + native['source']['sourceSnapshotSha256'],
        'placementMeaning': 'Native Common Core K-8 grades and HS band. HS is not an exact school year. Standards and substandards are preserved separately.',
        'nodes': nodes, 'relationships': sorted(relationships, key=lambda e: e['id'])}


def alignment(node_id, layer, source_id, relation, reason, provenance):
    return {'id': stable_id('alignment', node_id, layer, source_id, relation),
        'nodeId': node_id, 'layer': layer, 'sourceNodeId': source_id, 'relation': relation,
        'status': 'accepted', 'reason': reason, 'reviewStatus': 'machine_content_review',
        'reviewProvenance': provenance}


def apply_us_overrides(alignments, overrides, source_ids, canonical_ids, initial_reviews=None):
    """Adopt explicit reviewed changes, rejecting stale or unknown pair claims."""
    active = {}
    for a in alignments:
        key = (a['sourceNodeId'], a['nodeId'])
        if a['layer'] == 'US':
            if key in active:
                raise ValueError(f'Duplicate initial US pair: {key}')
            active[key] = a
    history, seen = [], set()
    for correction in overrides.get('corrections', []):
        key = (correction['sourceNodeId'], correction['nodeId'])
        if key in seen:
            raise ValueError(f'Duplicate override pair: {key}')
        seen.add(key)
        if key[0] not in source_ids or key[1] not in canonical_ids:
            raise ValueError(f'Unknown override endpoint: {key}')
        previous = active.get(key)
        prior, target = correction['priorRelation'], correction['targetRelation']
        if prior is None:
            if previous is not None or target == 'remove':
                raise ValueError(f'Override addition requires an absent pair: {key}')
        elif previous is None or previous['relation'] != prior:
            raise ValueError(f'Override prior relation mismatch or unknown pair: {key}')
        if target not in ('exact', 'narrower', 'broader', 'partial', 'remove'):
            raise ValueError(f'Invalid override target: {target}')
        provenance = {'initial': previous['reviewProvenance'] if previous else None,
            'initialSourceReview': (initial_reviews or {}).get(key[0]),
            'adoptedAudit': dict(overrides['provenance'], reason=correction['reason'],
                priorRelation=prior, targetRelation=target,
                reviewMeaning='Adopted scope review; partial does not assert question coverage or standard mastery.')}
        new = None if target == 'remove' else alignment(key[1], 'US', key[0], target, correction['reason'], provenance)
        if new is None:
            del active[key]
        else:
            active[key] = new
        history.append({'sourceNodeId': key[0], 'nodeId': key[1], 'priorRelation': prior,
            'targetRelation': target, 'priorAlignment': previous,
            'activeAlignmentId': new['id'] if new else None,
            'reason': correction['reason'], 'provenance': overrides['provenance']})
    return [a for a in alignments if a['layer'] != 'US'] + list(active.values()), history


def build():
    canonical_path = ROOT / 'knowledge-graph/source/nodes.json'
    canonical = {n['id']: n for n in read(canonical_path)}
    cn, us = read(EVIDENCE / 'cn-native.json'), read(EVIDENCE / 'us-native.json')
    refined = read(EVIDENCE / 'cn-refined-review.json')
    refinements = {r['nodeId']: r for r in refined['results']}
    cn_input = {r['id']: r for r in read(EVIDENCE / 'cn-refined-input.json')}
    assert set(refinements) == set(cn_input) and len(refinements) == 28
    layers = [cn_layer(cn), us_layer(us)]
    alignments, unchanged = [], 0
    for n in cn['nodes']:
        c = canonical[n['id']]
        # Prove source identity from retained original definitions, not matching IDs alone.
        assert c['original']['description'] == n['description'], n['id']
        assert c['original']['mastery_criteria'] == n['mastery_criteria'], n['id']
        same = c['description'] == n['description'] and c['criteria'] == n['mastery_criteria']
        if same:
            assert n['id'] not in refinements
            unchanged += 1
            relation, reason = 'exact', 'Canonical description and mastery criteria are unchanged from this pinned native topic; placement remains a separate source annotation.'
            provenance = {'type': 'source_identity_comparison', 'sourceRevision': REVISION_CN,
                          'comparedFields': ['description', 'criteria'], 'reviewMeaning': 'Definition identity, not an official curriculum equivalence claim.'}
        else:
            r, review_input = refinements[n['id']], cn_input[n['id']]
            assert c['description'] == review_input['description'] and c['criteria'] == review_input['criteria']
            assert n['description'] == review_input['originalDescription'] and n['mastery_criteria'] == review_input['originalCriteria']
            relation, reason = r['relation'], r['reason']
            provenance = dict(refined['reviewer'], evidenceFile='cn-refined-review.json', sourceRevision=REVISION_CN)
        alignments.append(alignment(n['id'], 'CN', n['id'], relation, reason, provenance))
    assert unchanged == 774
    reviews = []
    for filename in ('us-review-primary.json', 'us-review-secondary.json'):
        report = read(EVIDENCE / filename)
        for row in report['results']:
            reviews.append(dict(row, reviewEvidence=filename))
            for a in row['alignments']:
                alignments.append(alignment(a['nodeId'], 'US', str(row['sourceNodeId']), a['relation'],
                    a['reason'], dict(report['reviewer'], evidenceFile=filename, sourceReviewStatus=row['status'],
                    reviewMeaning='Initial machine content review, not teacher review or an official crosswalk; no complete-standard mastery claim.')))
    assert len(reviews) == len({r['sourceNodeId'] for r in reviews}) == 480
    assert {r['sourceNodeId'] for r in reviews} == {n['id'] for n in layers[1]['nodes']}
    for r in reviews:
        assert bool(r['alignments']) == (r['status'] != 'unmapped'), r['sourceNodeId']
    override_path = EVIDENCE / 'us-alignment-overrides.json'
    overrides = read(override_path) if override_path.is_file() else {'corrections': []}
    if overrides['corrections']:
        for role in ('audit', 'adjudication'):
            provenance = overrides['provenance']
            if digest((EVIDENCE / provenance[role + 'File']).read_bytes()) != provenance[role + 'Sha256']:
                raise ValueError(f'Override {role} evidence hash differs')
    alignments, override_history = apply_us_overrides(alignments, overrides,
        {n['id'] for n in layers[1]['nodes']}, set(canonical),
        {r['sourceNodeId']: {'status': r['status'], 'reason': r['reason'],
            'evidenceFile': r['reviewEvidence']} for r in reviews})
    for r in reviews:
        r['initialStatus'] = r['status']
        remaining = [a for a in alignments if a['layer'] == 'US' and a['sourceNodeId'] == r['sourceNodeId']]
        r['finalStatus'] = 'unmapped' if not remaining else ('mapped' if r['initialStatus'] == 'mapped' and all(a['relation'] in ('exact', 'narrower') for a in remaining) else 'partial')
    assert len(layers[0]['nodes']) == 802 and len(layers[0]['relationships']) == 1299
    assert Counter(e['relation'] for e in layers[1]['relationships']) == {'supports': 757, 'related': 142, 'contains': 116}
    import curriculum_graph
    curricula = {'schemaVersion': 1, 'layers': layers}
    alignments.sort(key=lambda a: a['id'])
    curriculum_graph.validate_source(curricula, alignments, set(canonical))
    outputs = {'knowledge-graph/source/curricula.json': encoded(curricula), 'knowledge-graph/source/alignments.json': encoded(alignments)}
    manifest = {'schemaVersion': 1, 'builder': 'scripts/build_curriculum_sources.py',
        'builderSha256': digest(Path(__file__).read_bytes()),
        'rebuild': 'python scripts/build_curriculum_sources.py --check',
        'relationDirection': 'Canonical relative to native source: narrower is subset, broader is superset, partial is overlap without containment.',
        'reviewMeaning': 'Machine content review and source-identity checks, not teacher review, official equivalence or learner mastery evidence.',
        'edgeMeaning': 'Native layers only; alignments never project source edges into canonical prerequisites.',
        'sourceStatusMeaning': 'Initial status is retained from initial reviewers. Final status is unmapped without active links, partial with partial/broader links or initial incomplete coverage, and mapped only for initially mapped standards whose remaining links are exact/narrower. These are content-review summaries, not question coverage or mastery claims.',
        'USAlignmentOverrideHistory': override_history,
        'baselineCanonicalSourceHashes': read(EVIDENCE / 'baseline-source-hashes.json'),
        'canonicalNodesAtBuildSha256': digest(canonical_path.read_bytes()),
        'evidenceFiles': [{'path': str(p.relative_to(ROOT)).replace('\\', '/'), 'sha256': digest(p.read_bytes()), 'bytes': p.stat().st_size} for p in sorted(EVIDENCE.glob('*.json'))],
        'generatedFiles': [{'path': p, 'sha256': digest(v), 'bytes': len(v)} for p, v in outputs.items()],
        'counts': {'CN': {'nodes': 802, 'relationships': 1299, 'relations': dict(Counter(e['relation'] for e in layers[0]['relationships'])), 'exactIdentityAlignments': unchanged, 'refinedPartialAlignments': 28},
                   'US': {'nodes': 480, 'relationships': 1015, 'relations': {'supports': 757, 'related': 142, 'contains': 116}, 'reviewedSources': len(reviews), 'initialSourceStatus': dict(Counter(r['initialStatus'] for r in reviews)), 'finalSourceStatus': dict(Counter(r['finalStatus'] for r in reviews)), 'alignments': sum(a['layer'] == 'US' for a in alignments), 'alignmentRelations': dict(Counter(a['relation'] for a in alignments if a['layer'] == 'US')), 'adoptedOverrides': len(override_history)}},
        'USSourceReviews': [{'sourceNodeId': r['sourceNodeId'], 'code': r['code'], 'initialStatus': r['initialStatus'], 'finalStatus': r['finalStatus'], 'initialReason': r['reason'], 'adoptedAuditReasons': [h['reason'] for h in override_history if h['sourceNodeId'] == r['sourceNodeId']], 'reviewEvidence': r['reviewEvidence'], 'alignmentIds': [a['id'] for a in alignments if a['layer'] == 'US' and a['sourceNodeId'] == r['sourceNodeId']]} for r in sorted(reviews, key=lambda r: int(r['sourceNodeId']))]}
    outputs['knowledge-graph/curriculum-manifest.json'] = encoded(manifest)
    return outputs, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs, manifest = build()
    for name, content in outputs.items():
        path = ROOT / name
        if args.check:
            if not path.is_file() or path.read_bytes() != content:
                raise SystemExit(f'Out of date: {name}')
        else:
            path.write_bytes(content)
    print(json.dumps(manifest['counts'], ensure_ascii=False))


if __name__ == '__main__':
    main()
