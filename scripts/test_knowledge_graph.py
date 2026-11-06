"""Portable graph bindings, direction, alternatives, and build/reader checks."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import knowledge_graph as graph


def node(node_id):
    return {'id': node_id, 'name': node_id.split(':')[-1].title(), 'nameZh': '',
            'description': 'A specific mathematical operation with stated conditions.',
            'criteria': ['Explain and carry out the stated operation.'], 'level': 'test scope',
            'kind': 'procedure', 'aliases': [], 'sourceId': None, 'sourceRevision': None,
            'reviewStatus': 'machine_reviewed'}


def edge(edge_id, dependent, prerequisite, relation='requires', status='accepted', method=None):
    return {'id': edge_id, 'nodeId': dependent, 'prerequisiteId': prerequisite,
            'relation': relation, 'methodId': method, 'scope': 'The stated operation only.',
            'reason': 'The dependent operation uses this mathematical step.',
            'status': status, 'reviewStatus': 'machine_reviewed',
            'original': {'strength': 'hard', 'reason': 'Preserved original rationale.'},
            'reviews': [{'reviewer': 'fixture reviewer', 'decision': status, 'reason': 'Fixture evidence.'}]}


class KnowledgeGraphTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='math-graph-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.question = {'ID': 'cnm_001_q1', 'Bank': 'cn-math', 'Language': 'en',
                         'Question': 'Expand $(x+1)^2$.', 'Question Type': 'text',
                         'Choices': {}, 'Choices Type': 'text', 'Correct Answer': 'x^2+2x+1',
                         'ResponseType': 'short', 'Grade': 8, 'Level': 'Middle school',
                         'CurriculumUnit': 'Grade 8', 'Solution': 'A worked solution.'}
        self.question_path = self.root / 'cn-math-bank/questions/cnm_001_q1.json'
        self.question_path.parent.mkdir(parents=True)
        self._write_question()
        ids = ['math:target', 'math:base', 'math:prepare', 'math:method', 'math:alternative',
               'math:hidden', 'math:rejected', 'math:unresolved', 'math:dependent', 'math:related']
        self.source = {'metadata': {'version': 'fixture-v1', 'sources': []},
                       'nodes': [node(node_id) for node_id in ids],
                       'relationships': [edge('target-base', 'math:target', 'math:base'),
                                         edge('base-prepare', 'math:base', 'math:prepare', 'prepares'),
                                         edge('target-method', 'math:target', 'math:method', 'method_component', method='reviewed-distributive-expansion'),
                                         edge('target-hidden', 'math:target', 'math:hidden', 'method_component', method='distribution'),
                                         edge('target-rejected', 'math:target', 'math:rejected', status='rejected'),
                                         edge('target-unresolved', 'math:target', 'math:unresolved', status='unresolved'),
                                         edge('dependent-target', 'math:dependent', 'math:target'),
                                         edge('target-related', 'math:target', 'math:related', 'related')],
                       'mappings': [self._mapping()]}
        self._write_source()

    def _mapping(self):
        return {'questionId': self.question['ID'], 'bank': self.question['Bank'],
                **graph.question_fingerprint(self.question, self.root), 'status': 'mapped',
                'reviewStatus': 'machine_reviewed', 'assessedIds': ['math:target'], 'supportIds': [],
                'routes': [{'id': 'distribution', 'label': 'Expand the product', 'nodeIds': ['math:method']},
                           {'id': 'identity', 'label': 'Use the identity', 'nodeIds': ['math:alternative']}],
                'sourceTopicAgreement': 'not_used_as_evidence', 'flags': [],
                'rationale': 'The displayed question asks for a binomial expansion.',
                'answerCheck': {'status': 'checked'},
                'reviews': [{'reviewer': 'fixture reviewer', 'decision': 'mapped'}]}

    def _write_source(self):
        directory = self.root / 'knowledge-graph/source'
        directory.mkdir(parents=True, exist_ok=True)
        for field in ('metadata', 'nodes', 'relationships'):
            (directory / (field + '.json')).write_text(json.dumps(self.source[field]), encoding='utf-8')
        (directory / 'mappings.jsonl').write_text(''.join(json.dumps(m) + '\n' for m in self.source['mappings']), encoding='utf-8')

    def test_non_diagnostic_context_is_completed_definition_only_without_expansion(self):
        mapping = self.source['mappings'][0]
        mapping.update(status='non_diagnostic', assessedIds=[], supportIds=[], routes=[],
                       contextualIds=['math:target'], flags=['answer_relation_supplied'])
        self._write_source()
        report = graph.build_database(root=self.root)
        self.assertEqual((report['mapped'], report['non_diagnostic'], report['unresolved'],
                          report['completedMappings']), (0, 1, 0, 1))
        for dependents in (False, True):
            context = graph.context_for_question(self.question, root=self.root, depth=20, dependents=dependents)
            self.assertEqual(context['status'], 'non_diagnostic')
            self.assertEqual(context['binding']['status'], 'current')
            self.assertEqual(context['assessedIds'], [])
            self.assertEqual(context['supportIds'], [])
            self.assertEqual(context['nodes'], [])
            self.assertEqual(context['edges'], [])
            self.assertEqual(context['routes'], [])
            self.assertEqual(context['contextualIds'], ['math:target'])
            self.assertEqual([(n['id'], n['roles']) for n in context['contextualNodes']],
                             [('math:target', ['contextual'])])
        compact = graph.context_for_question(self.question, root=self.root, max_chars=512)
        self.assertEqual(compact['status'], 'non_diagnostic')
        self.assertEqual(compact['binding']['status'], 'current')
        self.assertLessEqual(len(graph._json(compact)), 512)
        self.assertEqual(compact['nodes'], [])
        self.assertEqual(compact['edges'], [])
        changed = {**self.question, 'Question': 'A different task.'}
        self.assertEqual(graph.context_for_question(changed, root=self.root)['status'], 'stale')

    def test_non_diagnostic_references_are_required_valid_and_not_assessed(self):
        mapping = deepcopy(self.source['mappings'][0])
        mapping.update(status='non_diagnostic', assessedIds=[], supportIds=[], routes=[],
                       contextualIds=['math:target'])
        ids = {n['id'] for n in self.source['nodes']}
        graph.validate_mapping(mapping, ids)
        for changed in [dict(contextualIds=[]), dict(contextualIds=['math:missing']),
                        dict(assessedIds=['math:target']), dict(supportIds=['math:base']),
                        dict(routes=[{'id': 'method', 'label': 'Not contextual', 'nodeIds': ['math:method']}])]:
            with self.subTest(changed=changed), self.assertRaises(graph.GraphError):
                graph.validate_mapping({**mapping, **changed}, ids)
        old_mapping = self.source['mappings'][0]
        self.assertNotIn('contextualIds', old_mapping)
        graph.validate_mapping(old_mapping, ids)

    def test_route_only_mapping_builds_with_alternatives_and_shared_prerequisites(self):
        mapping = self.source['mappings'][0]
        mapping['assessedIds'] = []
        mapping['routes'][0]['nodeIds'].insert(0, 'math:target')
        self.source['relationships'].append(edge('alternative-base', 'math:alternative', 'math:base'))
        report = self._build()
        self.assertEqual((report['mapped'], report['completedMappings'], report['unresolved']), (1, 1, 0))
        self.assertTrue(graph.validate_database(self.root)['valid'])
        context = graph.context_for_question(self.question, self.root, depth=2, max_chars=20000)
        self.assertEqual(context['status'], 'mapped')
        self.assertEqual(context['binding']['status'], 'current')
        self.assertEqual(context['assessedIds'], [])
        self.assertEqual(context['routes'], mapping['routes'])
        by_id = {item['id']: item for item in context['nodes']}
        self.assertEqual(by_id['math:target']['roles'], ['route:distribution'])
        self.assertEqual(by_id['math:alternative']['roles'], ['route:identity'])
        self.assertEqual(by_id['math:base']['roles'], ['prerequisite'])
        self.assertIn('math:prepare', by_id)
        self.assertFalse(any('assessed' in item['roles'] for item in context['nodes']))
        method = next(item for item in context['edges'] if item['id'] == 'target-method')
        self.assertEqual(method['applicableRouteIds'], ['distribution'])
        self.assertIn('not evidence of learner mastery', context['meaning'])
        stale = graph.context_for_question({**self.question, 'Correct Answer': 'changed'}, self.root)
        self.assertEqual(stale['status'], 'stale')

    def test_route_only_budgets_keep_complete_groups_and_shared_support(self):
        mapping = self.source['mappings'][0]
        mapping.update(assessedIds=[], supportIds=['math:base'], routes=[
            {'id': 'short', 'label': 'A complete shorter alternative', 'nodeIds': ['math:method']},
            {'id': 'long', 'label': 'A different complete alternative',
             'nodeIds': ['math:alternative', 'math:hidden']}])
        self.source['relationships'] = [edge('method-base', 'math:method', 'math:base'),
                                        edge('alternative-base', 'math:alternative', 'math:base')]
        self._build()
        limited = graph.context_for_question(self.question, self.root, max_nodes=3, max_chars=20000)
        self.assertEqual([route['id'] for route in limited['routes']], ['short'])
        self.assertEqual({item['id'] for item in limited['nodes']}, {'math:base', 'math:method'})
        self.assertEqual([item['id'] for item in limited['edges']], ['method-base'])
        self.assertEqual(limited['omissions']['routes'], 1)
        self.assertEqual(next(item for item in limited['nodes'] if item['id'] == 'math:base')['roles'], ['support'])
        for budget in (512, 900, 1400, 2200, 6000):
            with self.subTest(max_chars=budget):
                context = graph.context_for_question(self.question, self.root, max_chars=budget)
                self.assertEqual(context['status'], 'mapped')
                self.assertEqual(context['binding']['status'], 'current')
                self.assertLessEqual(len(graph._json(context)), budget)
                included = {item['id'] for item in context['nodes']}
                for route in context['routes']:
                    self.assertIn(route, mapping['routes'])
                    self.assertTrue(set(route['nodeIds']) <= included)
                self.assertTrue(all(item['nodeId'] in included and item['prerequisiteId'] in included
                                    for item in context['edges']))
        tiny = graph.context_for_question(self.question, self.root, max_chars=512)
        self.assertEqual(tiny['routes'], [])
        self.assertEqual(tiny['nodes'], [])
        self.assertEqual(tiny['omissions']['routes'], 2)

    def test_route_only_does_not_allow_support_only_or_invalid_alternatives(self):
        mapping = deepcopy(self.source['mappings'][0])
        mapping.update(assessedIds=[], supportIds=['math:base'])
        ids = {item['id'] for item in self.source['nodes']}
        graph.validate_mapping(mapping, ids)
        for change in [dict(routes=[]), dict(routes=None),
                       dict(routes=[{'id': 'empty', 'label': 'Incomplete route', 'nodeIds': []}]),
                       dict(routes=[{'id': 'unknown', 'label': 'Unknown concept', 'nodeIds': ['math:missing']}]),
                       dict(status='non_diagnostic', contextualIds=['math:target'])]:
            with self.subTest(change=change), self.assertRaises(graph.GraphError):
                graph.validate_mapping({**mapping, **change}, ids)

    def test_default_context_retains_a_fourteen_concept_complete_route(self):
        # A reviewed geometry route needs fourteen distinct concepts. The old
        # twelve-node default silently omitted its entire mathematical context.
        ids = ['math:step' + str(i) for i in range(14)]
        self.source['nodes'] = [node(node_id) for node_id in ids]
        self.source['relationships'] = []
        mapping = self.source['mappings'][0]
        mapping.update(assessedIds=[], supportIds=[], routes=[
            {'id': 'complete-geometry', 'label': 'Locate centers and prove the area bound', 'nodeIds': ids}])
        self._build()
        result = graph.context_for_question(self.question, self.root)
        self.assertEqual(result['routes'], mapping['routes'])
        self.assertEqual({item['id'] for item in result['nodes']}, set(ids))
        self.assertLessEqual(len(graph._json(result)), graph.DEFAULT_MAX_CHARS)
        self.assertEqual(result['omissions']['routes'], 0)
        explicit_small = graph.context_for_question(self.question, self.root, max_nodes=12)
        self.assertEqual(explicit_small['nodes'], [])
        self.assertEqual(explicit_small['routes'], [])
        self.assertEqual(explicit_small['omissions']['routes'], 1)

    def test_character_budget_can_keep_shorter_route_after_longer_shared_route_is_omitted(self):
        ids = ['math:target', 'math:method', 'math:alternative', 'math:shared']
        self.source['nodes'] = [node(node_id) for node_id in ids]
        self.source['nodes'][1]['description'] = 'A complete but lengthy method definition. ' * 100
        self.source['relationships'] = []
        mapping = self.source['mappings'][0]
        mapping.update(routes=[
            {'id': 'long', 'label': 'Longer complete method', 'nodeIds': ['math:method', 'math:shared']},
            {'id': 'short', 'label': 'Shorter complete method', 'nodeIds': ['math:alternative', 'math:shared']}],
            answerCheck={'status': 'matches', 'reason': 'Retain the exact reviewed answer qualification.'})
        self._build()
        result = graph.context_for_question(self.question, self.root, max_chars=3000)
        self.assertEqual([route['id'] for route in result['routes']], ['short'])
        self.assertEqual({item['id'] for item in result['nodes']},
                         {'math:target', 'math:alternative', 'math:shared'})
        self.assertEqual(result['answerCheck'], mapping['answerCheck'])
        self.assertEqual(result['omissions']['routes'], 1)
        self.assertLessEqual(len(graph._json(result)), 3000)
        self.assertNotIn('route:long', [role for item in result['nodes'] for role in item['roles']])

    def test_node_budget_skips_an_oversized_route_and_keeps_a_complete_alternative(self):
        mapping = self.source['mappings'][0]
        mapping.update(assessedIds=[], supportIds=[], routes=[
            {'id': 'long', 'label': 'A larger alternative',
             'nodeIds': ['math:target', 'math:method', 'math:hidden']},
            {'id': 'short', 'label': 'A smaller complete alternative', 'nodeIds': ['math:alternative']}])
        self.source['relationships'] = [edge('short-base', 'math:alternative', 'math:base')]
        self._build()
        result = graph.context_for_question(self.question, self.root, max_nodes=2)
        self.assertEqual([route['id'] for route in result['routes']], ['short'])
        self.assertEqual({node['id'] for node in result['nodes']}, {'math:alternative', 'math:base'})
        self.assertEqual([item['id'] for item in result['edges']], ['short-base'])
        self.assertEqual(result['omissions']['routes'], 1)
        self.assertEqual(result['omissions']['nodes'], 3)
        self.assertEqual(result, graph.context_for_question(self.question, self.root, max_nodes=2))

        # A node from an omitted alternative can still be a genuine prerequisite
        # of the retained route. It is then present, not counted as omitted.
        mapping['routes'][0]['nodeIds'][0] = 'math:base'
        self._build()
        result = graph.context_for_question(self.question, self.root, max_nodes=2)
        base = next(node for node in result['nodes'] if node['id'] == 'math:base')
        self.assertEqual(base['roles'], ['prerequisite'])
        self.assertEqual(result['omissions']['nodes'], 2)

    def test_text_extraction_retains_criterion_scope_and_review_qualifications(self):
        method = next(item for item in self.source['nodes'] if item['id'] == 'math:method')
        method.update(criteria=['Calculate only for the supplied special-value cosine.'],
                      scopeNotes='This scope does not cover a general unknown angle.')
        relationship = self.source['relationships'][2]
        relationship['scope'] = 'Only within the explicitly selected expansion route.'
        self._build()
        result = graph.context_for_question(self.question, self.root)
        text = graph.format_context(result)
        self.assertIn(method['criteria'][0], text)
        self.assertIn(method['scopeNotes'], text)
        self.assertIn(relationship['scope'], text)
        self.assertIn('Review: machine_reviewed', text)
        self.assertIn('Routes are optional alternatives', text)

    def test_alternative_excluded_by_node_budget_can_recover_after_character_trimming(self):
        mapping = self.source['mappings'][0]
        mapping.update(assessedIds=[], supportIds=[], routes=[
            {'id': 'long-text', 'label': 'A larger textual definition', 'nodeIds': ['math:method', 'math:hidden']},
            {'id': 'short', 'label': 'A complete smaller alternative', 'nodeIds': ['math:alternative']}])
        self.source['nodes'][3]['description'] *= 1000
        self.source['relationships'] = [edge('short-base', 'math:alternative', 'math:base')]
        self._build()
        result = graph.context_for_question(self.question, self.root, max_nodes=2, max_chars=3000)
        self.assertEqual([route['id'] for route in result['routes']], ['short'])
        self.assertEqual({node['id'] for node in result['nodes']}, {'math:alternative', 'math:base'})
        self.assertLessEqual(len(graph._json(result)), 3000)
        self.assertEqual(result['omissions']['routes'], 1)
        self.assertEqual(result['omissions']['nodes'], 2)

    def test_complete_route_and_grading_caveats_take_priority_over_edge_summaries(self):
        mapping = self.source['mappings'][0]
        mapping.update(supportIds=['math:base', 'math:prepare', 'math:hidden'], routes=[
            {'id': 'complete', 'label': 'A complete reviewed method',
             'nodeIds': ['math:method', 'math:alternative']}],
            answerCheck={'status': 'confirmed_conflict',
                         'reason': 'Preserve this adjudicated source interpretation in full. ' * 30},
            flags=['The original answer key is retained; automatic grading is withheld.'])
        relationship = edge('method-link', 'math:method', 'math:alternative',
                            'method_component', method='reviewed-method')
        relationship['reason'] = 'A detailed reviewed justification for this method relationship. ' * 200
        self.source['relationships'] = [relationship]
        self._build()
        large = graph.context_for_question(self.question, self.root, max_chars=30000)
        self.assertEqual(len(large['edges']), 1)
        result = graph.context_for_question(self.question, self.root)
        self.assertEqual(result['routes'], mapping['routes'])
        self.assertEqual(result['nodes'], large['nodes'])
        self.assertEqual(result['answerCheck'], mapping['answerCheck'])
        self.assertEqual(result['flags'], mapping['flags'])
        self.assertEqual(result['edges'], [])
        self.assertEqual(result['omissions']['edges'], 1)
        self.assertEqual(result['omissions']['routes'], 0)
        self.assertEqual(result['omissions']['nodes'], 0)
        self.assertLessEqual(len(graph._json(result)), graph.DEFAULT_MAX_CHARS)

    def test_optional_contextual_nodes_do_not_join_mapped_traversal_or_allow_forged_stub(self):
        from knowledge_graph_questions import graph_payload
        mapping = self.source['mappings'][0]
        mapping['contextualIds'] = ['math:hidden']
        self._write_source()
        graph.build_database(root=self.root)
        context = graph.context_for_question(self.question, root=self.root)
        self.assertEqual([n['id'] for n in context['contextualNodes']], ['math:hidden'])
        self.assertNotIn('math:hidden', {n['id'] for n in context['nodes']})
        self.assertFalse(any('math:hidden' in (e['nodeId'], e['prerequisiteId']) for e in context['edges']))
        for limit in (512, 900, 1300, 1700, 2400):
            bounded = graph.context_for_question(self.question, root=self.root, max_chars=limit)
            self.assertLessEqual(len(graph._json(bounded)), limit)
        stub = graph_payload(mapping, 'fixture-v1')
        stub['contextualIds'] = ['math:base']
        changed = {**self.question, 'KnowledgeGraph': stub}
        self.assertEqual(graph.context_for_question(changed, root=self.root)['status'], 'stale')

    def test_visible_heading_is_bound_only_when_used_to_interpret_task(self):
        from knowledge_graph_questions import graph_payload, validate_imported_references
        self.question['Topic'] = {'id': 'source-label', 'label': 'Binomial expansion'}
        self._write_question()
        mapping = self.source['mappings'][0]
        mapping['headingContext'] = self.question['Topic']['label']
        self._write_source()
        graph.build_database(root=self.root)
        self.question['KnowledgeGraph'] = graph_payload(mapping, 'fixture-v1')
        context = graph.context_for_question(self.question, root=self.root)
        self.assertEqual(context['binding']['headingContext'], 'Binomial expansion')
        validate_imported_references(self.question, root=self.root)
        changed = deepcopy(self.question)
        changed['Topic']['label'] = 'A different theorem'
        self.assertEqual(graph.context_for_question(changed, root=self.root)['status'], 'stale')
        with self.assertRaisesRegex(graph.GraphError, 'heading'):
            validate_imported_references(changed, root=self.root)
        del mapping['headingContext']
        self._write_source()
        graph.build_database(root=self.root)
        changed.pop('KnowledgeGraph')
        self.assertEqual(graph.context_for_question(changed, root=self.root)['status'], 'mapped')

    def _write_question(self):
        self.question_path.write_text(json.dumps(self.question), encoding='utf-8')

    def _build(self):
        self._write_source()
        return graph.build_database(self.root)

    def test_binding_tracks_task_answer_and_level_but_excludes_solution_and_tags(self):
        original = graph.question_fingerprint(self.question, self.root)
        for field, value in [('Question', 'Factor $(x+1)^2$.'), ('Correct Answer', 'other'),
                             ('Choices', {'A': 'Different choice'}), ('ResponseType', 'numeric'),
                             ('Answer Form', {'type': 'simplified'}), ('Unordered Answers', True),
                             ('Accepted Answers', ['alternative']), ('Rejected Answers', ['unsimplified']),
                             ('Language', 'zh'), ('Grade', 9), ('Level', 'Other'),
                             ('CurriculumUnit', 'Other'), ('GradingStatus', 'withheld')]:
            changed = {**self.question, field: value}
            with self.subTest(field=field):
                self.assertNotEqual(original['contentHash'], graph.question_fingerprint(changed, self.root)['contentHash'])
        changed = {**self.question, 'Solution': 'Rewritten', 'skill': ['arbitrary'],
                   'Topic': {'id': 'wrong'}, 'Meta': {'SourceTopicID': 'wrong'},
                   'KnowledgeGraph': {'contentHash': 'circular metadata'}}
        self.assertEqual(original, graph.question_fingerprint(changed, self.root))
        self.assertEqual(original, graph.question_fingerprint(dict(reversed(list(self.question.items()))), self.root))

    def test_server_builds_missing_index_and_rebuilds_a_corrupt_derived_index(self):
        from serve_math_practice import prepare_knowledge_graph
        first = prepare_knowledge_graph(self.root)
        self.assertTrue(first['valid'])
        database = self.root / 'knowledge-graph/knowledge.sqlite3'
        database.write_bytes(b'broken derived index')
        rebuilt = prepare_knowledge_graph(self.root)
        self.assertTrue(rebuilt['valid'])
        self.assertEqual(first['logicalDigest'], rebuilt['logicalDigest'])

    def test_server_rebuilds_changed_sources_before_retrieval_and_grading(self):
        from serve_math_practice import prepare_knowledge_graph
        first = prepare_knowledge_graph(self.root)
        self.source['metadata']['version'] = 'fixture-v2'
        self.source['relationships'][0]['status'] = 'rejected'
        self.source['mappings'][0]['answerCheck'] = {
            'status': 'confirmed_conflict', 'reason': 'A reviewed source correction.'}
        self._write_source()
        rebuilt = prepare_knowledge_graph(self.root)
        self.assertEqual(rebuilt['graphVersion'], 'fixture-v2')
        self.assertNotEqual(first['sourceDigest'], rebuilt['sourceDigest'])
        context = graph.context_for_question(self.question, self.root)
        self.assertNotIn('target-base', {e['id'] for e in context['edges']})
        self.assertEqual(context['answerCheck']['status'], 'confirmed_conflict')
        # A malformed replacement must not leave the previously valid claims active.
        self.source['mappings'][0]['assessedIds'] = ['math:missing']
        self._write_source()
        self.assertFalse(prepare_knowledge_graph(self.root)['valid'])
        self.assertFalse((self.root / 'knowledge-graph/knowledge.sqlite3').exists())
        self.assertEqual(len(list((self.root / 'knowledge-graph').glob('knowledge-invalid-*.sqlite3'))), 1)

    def test_text_extraction_preserves_alternatives_and_confirmed_grading_dispute(self):
        self.source['mappings'][0]['answerCheck'] = {
            'status': 'confirmed_conflict', 'reason': 'The provided conditions are inconsistent.'}
        self._build()
        text = graph.format_context(graph.context_for_question(self.question, self.root))
        self.assertIn('Optional route distribution: Expand the product', text)
        self.assertIn('Optional route identity: Use the identity', text)
        self.assertIn('math:method [route:distribution]', text)
        self.assertIn('[routes: distribution]', text)
        self.assertIn('Grading: withheld', text)
        self.assertIn('The provided conditions are inconsistent.', text)

    def test_actual_stem_and_choice_figures_are_bound_solution_figures_excluded(self):
        figures = self.root / 'cn-math-bank/figures'
        figures.mkdir()
        (figures / 'stem.svg').write_bytes(b'<svg>one</svg>')
        (figures / 'choice.svg').write_bytes(b'<svg>two</svg>')
        self.question.update(Question='Inspect [Figure 1](figures/stem.svg)',
                             Choices={'A': '[Figure 2](figures/choice.svg)'},
                             Solution='[Figure 3](figures/missing-solution-only.svg)')
        first = graph.question_fingerprint(self.question, self.root)
        self.assertEqual(set(first['figureHashes']), {'figures/stem.svg', 'figures/choice.svg'})
        (figures / 'choice.svg').write_bytes(b'<svg>changed geometry</svg>')
        self.assertNotEqual(first['contentHash'], graph.question_fingerprint(self.question, self.root)['contentHash'])
        (figures / 'stem.svg').unlink()
        with self.assertRaisesRegex(graph.GraphError, 'figure'):
            graph.question_fingerprint(self.question, self.root)

    def test_preinstall_fingerprint_and_unsafe_image_path(self):
        source = self.root / 'incoming'
        (source / 'figures').mkdir(parents=True)
        (source / 'figures/plot.svg').write_bytes(b'<svg/>')
        question = {**self.question, 'ID': 'new_bank__001', 'Bank': 'new_bank',
                    'Question': '[Figure 1](figures/plot.svg)'}
        bound = graph.question_fingerprint(question, self.root, bank_root=source)
        self.assertIn('figures/plot.svg', bound['figureHashes'])
        question['Question'] = '[Figure 1](../outside.svg)'
        with self.assertRaises(graph.GraphError):
            graph.question_fingerprint(question, self.root, bank_root=source)

    def test_direct_prerequisites_have_correct_direction_and_review_filter(self):
        self._build()
        context = graph.context_for_question(self.question, self.root)
        ids = {n['id'] for n in context['nodes']}
        self.assertIn('math:base', ids)
        self.assertNotIn('math:dependent', ids)
        self.assertNotIn('math:prepare', ids)
        self.assertNotIn('math:hidden', ids)
        self.assertNotIn('math:rejected', ids)
        self.assertNotIn('math:unresolved', ids)
        self.assertNotIn('math:related', ids)
        edge_ids = {e['id'] for e in context['edges']}
        self.assertEqual(edge_ids, {'target-base', 'target-method'})
        self.assertEqual(context['status'], 'mapped')
        self.assertEqual(context['binding']['status'], 'current')
        deeper = graph.context_for_question(self.question, self.root, depth=2)
        self.assertIn('math:prepare', {n['id'] for n in deeper['nodes']})
        downstream = graph.context_for_question(self.question, self.root, dependents=True)
        self.assertIn('math:dependent', {n['id'] for n in downstream['nodes']})
        self.assertNotIn('math:base', {n['id'] for n in downstream['nodes']})

    def test_route_alternatives_stay_groups_and_do_not_become_assessed_conjunction(self):
        self._build()
        context = graph.context_for_question(self.question, self.root)
        self.assertEqual(context['assessedIds'], ['math:target'])
        self.assertEqual(context['routes'], self.source['mappings'][0]['routes'])
        by_id = {n['id']: n for n in context['nodes']}
        self.assertEqual(by_id['math:alternative']['roles'], ['route:identity'])
        method_edge = next(edge for edge in context['edges'] if edge['id'] == 'target-method')
        self.assertEqual(method_edge['methodId'], 'reviewed-distributive-expansion')
        self.assertEqual(method_edge['applicableRouteIds'], ['distribution'])
        # A coincidentally matching method name cannot add an undeclared node.
        self.assertNotIn('target-hidden', {edge['id'] for edge in context['edges']})
        self.assertNotIn('mastery', context)
        # Remove the relevant route: its method-only component cannot be traversed.
        self.source['mappings'][0]['routes'] = []
        self._build()
        context = graph.context_for_question(self.question, self.root)
        self.assertNotIn('math:method', {n['id'] for n in context['nodes']})

    def test_missing_stale_unresolved_and_corrupt_database_degrade_explicitly(self):
        self.assertEqual(graph.context_for_question(self.question, self.root)['reason'], 'database_missing')
        self.assertFalse((self.root / 'knowledge-graph/knowledge.sqlite3').exists())
        self._build()
        changed = {**self.question, 'Question': 'A different question.'}
        self.assertEqual(graph.context_for_question(changed, self.root)['status'], 'stale')
        stale_stub = {**self.question, 'KnowledgeGraph': {'version': 'old'}}
        self.assertEqual(graph.context_for_question(stale_stub, self.root)['reason'], 'question_graph_metadata_changed')
        self.source['mappings'][0]['status'] = 'unresolved'
        self._build()
        unresolved = graph.context_for_question(self.question, self.root)
        self.assertEqual(unresolved['status'], 'unresolved')
        self.assertEqual(unresolved['nodes'], [])
        (self.root / 'knowledge-graph/knowledge.sqlite3').write_bytes(b'not a database')
        self.assertEqual(graph.context_for_question(self.question, self.root)['reason'], 'database_unavailable')

    def test_edited_pixels_stale_runtime_and_fail_validation(self):
        figures = self.root / 'cn-math-bank/figures'
        figures.mkdir()
        (figures / 'plot.svg').write_bytes(b'<svg>original</svg>')
        self.question['Question'] += ' [Figure 1](figures/plot.svg)'
        self._write_question()
        self.source['mappings'] = [self._mapping()]
        self._build()
        (figures / 'plot.svg').write_bytes(b'<svg>different</svg>')
        self.assertEqual(graph.context_for_question(self.question, self.root)['status'], 'stale')
        with self.assertRaisesRegex(graph.GraphError, 'stale'):
            graph.validate_database(self.root)

    def test_deterministic_bounded_context_has_no_dangling_edges_or_partial_routes(self):
        self._build()
        first = graph.context_for_question(self.question, self.root, max_nodes=2)
        self.assertEqual(first, graph.context_for_question(self.question, self.root, max_nodes=2))
        self.assertLessEqual(len(first['nodes']), 2)
        self.assertGreater(first['omissions']['nodes'], 0)
        included = {n['id'] for n in first['nodes']}
        self.assertTrue(all(e['nodeId'] in included and e['prerequisiteId'] in included for e in first['edges']))
        self.assertTrue(all(set(r['nodeIds']) <= included for r in first['routes']))
        self.assertGreater(first['omissions']['routes'], 0)
        tiny = graph.context_for_question(self.question, self.root, max_chars=1200)
        self.assertLessEqual(len(graph._json(tiny)), 1200)
        self.assertGreater(tiny['omissions']['nodes'], 0)

    def test_omitted_route_does_not_leave_a_method_edge_without_its_alternative_group(self):
        self.source['mappings'][0]['routes'][0]['nodeIds'].append('math:hidden')
        self._build()
        context = graph.context_for_question(self.question, self.root, max_nodes=2)
        self.assertEqual([route['id'] for route in context['routes']], ['identity'])
        self.assertFalse(any(edge['relation'] == 'method_component' for edge in context['edges']))
        self.assertNotIn('math:method', {node['id'] for node in context['nodes']})

    def test_method_edges_require_an_explicit_mapped_dependent_and_complete_route(self):
        self.source['relationships'] = [edge for edge in self.source['relationships']
                                        if edge['id'] != 'dependent-target']
        self.source['relationships'].append(edge('unmapped-method-dependent', 'math:dependent',
                                                  'math:method', 'method_component', method='anything'))
        self._build()
        context = graph.context_for_question(self.question, self.root, dependents=True)
        self.assertNotIn('math:dependent', {node['id'] for node in context['nodes']})
        self.assertNotIn('unmapped-method-dependent', {edge['id'] for edge in context['edges']})

    def test_incomplete_route_prunes_only_exclusive_nodes_and_their_branches(self):
        self.source['nodes'].extend([node('math:exclusive'), node('math:exclusive-base')])
        self.source['relationships'].append(edge('exclusive-base', 'math:exclusive', 'math:exclusive-base'))
        self.source['mappings'][0]['routes'] = [
            {'id': 'shared', 'label': 'Complete route', 'nodeIds': ['math:method']},
            {'id': 'omitted', 'label': 'Incomplete route', 'nodeIds': ['math:exclusive', 'math:hidden']}]
        # Make the shared method node serve both alternatives as well.
        self.source['mappings'][0]['routes'][1]['nodeIds'].insert(0, 'math:method')
        self._build()
        context = graph.context_for_question(self.question, self.root, max_nodes=3, depth=2)
        ids = {node['id'] for node in context['nodes']}
        self.assertIn('math:method', ids)
        self.assertNotIn('math:exclusive', ids)
        self.assertNotIn('math:exclusive-base', ids)
        self.assertEqual([route['id'] for route in context['routes']], ['shared'])
        shared = next(node for node in context['nodes'] if node['id'] == 'math:method')
        self.assertEqual(shared['roles'], ['route:shared'])
        method_edge = next(edge for edge in context['edges'] if edge['id'] == 'target-method')
        self.assertEqual(method_edge['applicableRouteIds'], ['shared'])

    def test_method_edge_cannot_join_nodes_from_different_alternative_routes(self):
        self.source['relationships'].append(edge('cross-route', 'math:alternative', 'math:method',
                                                  'method_component', method='distribution'))
        self._build()
        context = graph.context_for_question(self.question, self.root)
        self.assertNotIn('cross-route', {item['id'] for item in context['edges']})
        self.source['mappings'][0]['routes'][0]['nodeIds'].append('math:alternative')
        self._build()
        context = graph.context_for_question(self.question, self.root)
        linked = next(item for item in context['edges'] if item['id'] == 'cross-route')
        self.assertEqual(linked['applicableRouteIds'], ['distribution'])

    def test_bound_answer_checks_and_flags_survive_unresolved_and_compact_contexts(self):
        mapping = self.source['mappings'][0]
        mapping['answerCheck'] = {'status': 'confirmed_ambiguous', 'reason': 'Evidence ' * 1000}
        mapping['flags'] = ['confirmed_answer_ambiguity']
        self._build()
        for status in ('mapped', 'unresolved'):
            mapping['status'] = status
            self._build()
            with self.subTest(status=status):
                normal = graph.context_for_question(self.question, self.root, max_chars=20000)
                self.assertEqual(normal['answerCheck'], mapping['answerCheck'])
                self.assertEqual(normal['flags'], mapping['flags'])
                compact = graph.context_for_question(self.question, self.root, max_chars=512)
                self.assertLessEqual(len(graph._json(compact)), 512)
                self.assertEqual(compact['binding']['status'], 'current')
                self.assertEqual(compact['answerCheck']['status'], 'confirmed_ambiguous')
        stale = graph.context_for_question({**self.question, 'Correct Answer': 'changed'}, self.root)
        self.assertNotIn('answerCheck', stale)
        self.assertNotIn('flags', stale)

    def test_optional_local_mapping_overlay_builds_only_when_present_and_binds_strictly(self):
        from serve_math_practice import prepare_knowledge_graph
        public = self._build()
        self.assertEqual(public['bindingsChecked'], 1)
        overlay_dir = self.root / 'knowledge-graph/local'
        overlay_dir.mkdir()
        overlay_path = overlay_dir / 'mappings.jsonl'
        bank = self.root / 'custom-banks/local_math'
        (bank / 'questions').mkdir(parents=True)
        (bank / 'figures').mkdir()
        (bank / 'bank.json').write_text(json.dumps({'id': 'local_math', 'label': 'Local math',
                                                   'attribution': 'Fixture', 'license': 'Fixture'}), encoding='utf-8')
        (bank / 'figures/local.svg').write_bytes(b'<svg>installed local geometry</svg>')
        local_question = {**self.question, 'ID': 'local_math__one', 'Bank': 'local_math',
                          'Question': 'A local task. [Figure 1](figures/local.svg)'}
        local_path = bank / 'questions' / (local_question['ID'] + '.json')
        local_path.write_text(json.dumps(local_question), encoding='utf-8')
        local_mapping = {**self.source['mappings'][0], 'questionId': local_question['ID'], 'bank': 'local_math',
                         **graph.question_fingerprint(local_question, self.root)}
        overlay_path.write_text(json.dumps(local_mapping) + '\n', encoding='utf-8')
        installed = prepare_knowledge_graph(self.root)
        self.assertEqual(installed['bindingsChecked'], 2)
        self.assertNotEqual(public['sourceDigest'], installed['sourceDigest'])
        self.assertEqual(graph.mapping_record(local_question['ID'], self.root), local_mapping)
        self.assertEqual(graph.context_for_question(local_question, self.root)['binding']['status'], 'current')
        # Duplicate IDs across the public and local files cannot silently override.
        overlay_path.write_text(json.dumps(self.source['mappings'][0]) + '\n', encoding='utf-8')
        with self.assertRaisesRegex(graph.GraphError, 'Duplicate question mapping'):
            graph.build_database(self.root)
        overlay_path.write_text(json.dumps(local_mapping) + '\n', encoding='utf-8')
        local_path.unlink()
        with self.assertRaisesRegex(graph.GraphError, 'cannot load installed question'):
            graph.build_database(self.root)
        # A clean checkout has no local overlay or dependency on its local tasks.
        overlay_path.unlink()
        clean = prepare_knowledge_graph(self.root)
        self.assertEqual(public['sourceDigest'], clean['sourceDigest'])
        self.assertEqual(public['logicalDigest'], clean['logicalDigest'])
        self.assertEqual(clean['bindingsChecked'], 1)

    def test_build_reproducibility_atomic_failure_and_read_apis(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first['logicalDigest'], second['logicalDigest'])
        self.assertEqual(first['bindingsChecked'], 1)
        self.assertEqual(graph.graph_version(self.root), 'fixture-v1')
        self.assertEqual(graph.mapping_record(self.question['ID'], self.root), self.source['mappings'][0])
        self.assertIsNone(graph.mapping_record('unknown', self.root))
        self.assertEqual(graph.node_ids(self.root), frozenset(n['id'] for n in self.source['nodes']))
        # Source record order is not part of logical build identity.
        self.source['nodes'].reverse()
        self.source['relationships'].reverse()
        self.assertEqual(first['logicalDigest'], self._build()['logicalDigest'])
        database = self.root / 'knowledge-graph/knowledge.sqlite3'
        before = database.read_bytes()
        self.source['mappings'][0]['contentHash'] = '0' * 64
        with self.assertRaisesRegex(graph.GraphError, 'stale'):
            self._build()
        self.assertEqual(database.read_bytes(), before)
        self.assertEqual(list(database.parent.glob('.knowledge-*')), [])

    def test_all_references_and_duplicates_are_rejected_before_build(self):
        changes = [lambda: self.source['nodes'].append(deepcopy(self.source['nodes'][0])),
                   lambda: self.source['relationships'].append(deepcopy(self.source['relationships'][0])),
                   lambda: self.source['relationships'].append({**self.source['relationships'][0], 'id': 'duplicate-edge'}),
                   lambda: self.source['mappings'].append(deepcopy(self.source['mappings'][0])),
                   lambda: self.source['mappings'][0]['routes'][0]['nodeIds'].append('math:missing'),
                   lambda: self.source['relationships'][0].update(prerequisiteId='math:missing'),
                   lambda: self.source['mappings'][0]['routes'].append(deepcopy(self.source['mappings'][0]['routes'][0]))]
        pristine = deepcopy(self.source)
        for change in changes:
            self.source = deepcopy(pristine)
            change()
            with self.subTest(change=change), self.assertRaises(graph.GraphError):
                self._build()

    def test_only_accepted_requires_cycles_block_build(self):
        self.source['relationships'].append(edge('cycle', 'math:base', 'math:target'))
        with self.assertRaisesRegex(graph.GraphError, 'cycle'):
            self._build()
        self.source['relationships'][-1]['status'] = 'unresolved'
        self._build()
        self.source['relationships'][-1].update(status='accepted', relation='prepares')
        self._build()
        self.assertLessEqual(len(graph.context_for_question(self.question, self.root, depth=20)['nodes']), 12)

    def test_validation_detects_an_index_that_disagrees_with_review_records(self):
        self._build()
        path = self.root / 'knowledge-graph/knowledge.sqlite3'
        with sqlite3.connect(path) as connection:
            connection.execute('UPDATE relationships SET node_id=?,prerequisite_id=? WHERE id=?',
                               ('math:base', 'math:target', 'target-base'))
        connection.close()
        with self.assertRaisesRegex(graph.GraphError, 'index differs'):
            graph.validate_database(self.root)


if __name__ == '__main__':
    unittest.main()
