"""Layer isolation, source identity, and bounded curriculum context."""
from copy import deepcopy
from contextlib import closing
import json
import sqlite3
import unittest

import curriculum_graph as curriculum
import knowledge_graph as graph
import test_knowledge_graph as fixtures


class CurriculumGraphTests(unittest.TestCase):
    setUp = fixtures.KnowledgeGraphTests.setUp
    _write_question = fixtures.KnowledgeGraphTests._write_question
    _mapping = fixtures.KnowledgeGraphTests._mapping
    _write_source = fixtures.KnowledgeGraphTests._write_source

    def install(self, relation='partial'):
        nodes = [{'id': n, 'label': n, 'description': 'Source scope', 'placement': {'grade': 8}}
                 for n in ('standard', 'foundation', 'unmapped')]
        self.curricula = {'schemaVersion': 1, 'layers': [
            {'id': lid, 'label': lid, 'source': 'Source document', 'revision': '1',
             'placementMeaning': 'Source suggested placement', 'nodes': deepcopy(nodes),
             'relationships': [{'id': 'native', 'fromId': 'standard', 'toId': 'foundation',
                                'relation': 'supports', 'original': {'sourceDirection': 'reverse'}}]}
            for lid in ('CN', 'US')]}
        self.alignments = [{'id': 'crosswalk', 'nodeId': 'math:target', 'layer': 'US',
                            'sourceNodeId': 'standard', 'relation': relation,
                            'status': 'accepted', 'reason': 'Explicit scope overlap.',
                            'reviewStatus': 'machine_reviewed'}]
        self.write_curricula()
        graph.build_database(self.root)

    def write_curricula(self):
        directory = self.root / 'knowledge-graph/source'
        (directory / 'curricula.json').write_text(json.dumps(self.curricula), encoding='utf-8')
        (directory / 'alignments.json').write_text(json.dumps(self.alignments), encoding='utf-8')

    def test_native_layers_are_separate_and_crosswalks_never_project_edges(self):
        self.install()
        us = curriculum.layer_neighborhood('math:target', 'US', self.root)
        cn = curriculum.layer_neighborhood('math:target', 'CN', self.root)
        self.assertEqual(us['status'], 'partial')
        self.assertEqual({n['id'] for n in us['nodes']}, {'standard', 'foundation'})
        self.assertEqual(us['relationships'][0]['fromId'], 'standard')
        self.assertEqual(cn['status'], 'unmapped')
        self.assertEqual(cn['relationships'], [])
        self.assertIn('unmapped', {n['id'] for n in curriculum.browse_layer('US', self.root)['nodes']})
        ailleo = curriculum.layer_neighborhood('math:target', 'ailleo', self.root)
        self.assertTrue(all('level' not in n and 'placement' not in n for n in ailleo['nodes']))
        self.assertNotIn('native', {e['id'] for e in ailleo['relationships']})

    def test_partial_broad_and_rejected_crosswalks_do_not_claim_coverage(self):
        self.install('broader')
        practice = curriculum.practice_candidates('math:target', 'US', self.root)
        self.assertEqual(practice['status'], 'partial')
        self.assertEqual(practice['candidates'][0]['coverage'], 'partial')
        self.alignments[0]['status'] = 'rejected'
        self.write_curricula()
        graph.build_database(self.root)
        self.assertEqual(curriculum.practice_candidates('math:target', 'US', self.root)['candidates'], [])
        self.assertEqual(curriculum.layer_neighborhood('math:target', 'US', self.root)['nodes'], [])

    def test_native_practice_keeps_unmapped_source_visible(self):
        self.install('narrower')
        mapped = curriculum.practice_for_source('standard', 'US', self.root)
        self.assertEqual(mapped['canonicalNodeIds'], ['math:target'])
        self.assertEqual(mapped['candidates'][0]['coverage'], 'partial')
        self.assertEqual(mapped['candidates'][0]['bank'], 'cn-math')
        unmapped = curriculum.practice_for_source('unmapped', 'US', self.root)
        self.assertEqual(unmapped['label'], 'unmapped')
        self.assertEqual(unmapped['status'], 'unmapped')
        self.assertEqual(unmapped['candidates'], [])

    def test_context_preserves_bound_routes_and_grading_without_crosslayer_expansion(self):
        self.install('exact')
        context = graph.context_for_question(self.question, self.root, layer='US')
        self.assertEqual(context['answerCheck'], self.source['mappings'][0]['answerCheck'])
        self.assertEqual(context['routes'], self.source['mappings'][0]['routes'])
        self.assertEqual(context['edges'], [])
        self.assertNotIn('math:base', {n['id'] for n in context['nodes']})
        self.assertTrue(all('level' not in n for n in context['nodes']))
        self.assertEqual(context['curriculumContext']['status'], 'partial')
        self.assertLessEqual(len(graph._json(context)), 8000)
        self.assertLessEqual(len(context['nodes']), 16)
        tight = graph.context_for_question(self.question, self.root, max_chars=512, layer='CN')
        self.assertLessEqual(len(graph._json(tight)), 512)
        self.assertEqual(tight['answerCheck'], {'status': 'checked'})
        self.assertEqual(graph.mapping_record(self.question['ID'], self.root), self.source['mappings'][0])

    def test_curriculum_source_and_index_tampering_are_detected(self):
        self.install()
        before = graph.source_digest(self.root)
        self.curricula['layers'][0]['nodes'][0]['placement']['grade'] = 9
        self.write_curricula()
        self.assertNotEqual(before, graph.source_digest(self.root))
        db = self.root / 'knowledge-graph/knowledge.sqlite3'
        with closing(sqlite3.connect(db)) as c:
            c.execute("UPDATE curriculum_relationships SET relation='prerequisite' WHERE layer='US'")
            c.commit()
        with self.assertRaisesRegex(graph.GraphError, 'index differs'):
            graph.validate_database(self.root)

    def test_duplicate_crosswalk_and_unknown_endpoint_are_rejected(self):
        self.install()
        self.alignments.append({**self.alignments[0], 'id': 'duplicate'})
        self.write_curricula()
        with self.assertRaisesRegex(graph.GraphError, 'Duplicate alignment'):
            graph.load_source(self.root)
        self.alignments.pop()
        self.curricula['layers'][0]['relationships'][0]['toId'] = 'missing'
        self.write_curricula()
        with self.assertRaisesRegex(graph.GraphError, 'unknown source endpoint'):
            graph.load_source(self.root)

    def test_related_cycles_allowed_and_only_claimed_prerequisite_dag_is_checked(self):
        self.install()
        layer = self.curricula['layers'][0]
        layer['relationships'] = [{'id': 'a', 'fromId': 'standard', 'toId': 'foundation', 'relation': 'related'},
                                  {'id': 'b', 'fromId': 'foundation', 'toId': 'standard', 'relation': 'related'}]
        layer['prerequisiteDAG'] = True
        self.write_curricula()
        graph.load_source(self.root)
        for edge in layer['relationships']:
            edge['relation'] = 'prerequisite'
        self.write_curricula()
        with self.assertRaises(graph.GraphError):
            graph.load_source(self.root)

    def test_annotations_have_connections_only_from_their_own_layer(self):
        self.install()
        annotation = curriculum.annotations_for_node('math:target', self.root)
        self.assertEqual(annotation['CN']['connections'], [])
        self.assertEqual(annotation['US']['connections'][0]['id'], 'native')
        self.assertIn('target-base', {e['id'] for e in annotation['ailleo']['connections']})
        self.assertNotIn('native', {e['id'] for e in annotation['ailleo']['connections']})

    def test_native_context_includes_route_only_crosswalk_and_compacts_source(self):
        self.install('exact')
        mapping = self.source['mappings'][0]
        mapping['assessedIds'] = []
        mapping['routes'] = [{'id': 'one', 'label': 'A complete route', 'nodeIds': ['math:target', 'math:method']}]
        self._write_source()
        for layer in self.curricula['layers']:
            for node in layer['nodes']:
                node['original'] = {'grade': 99, 'hugeRawSource': 'x' * 9000}
        self.write_curricula()
        graph.build_database(self.root)
        context = graph.context_for_question(self.question, self.root, layer='US')
        self.assertEqual(context['routes'], mapping['routes'])
        self.assertEqual(context['edges'], [])
        native = context['curriculumContext']
        self.assertEqual(native['neighborhoods'][0]['status'], 'mapped')
        self.assertEqual(native['neighborhoods'][0]['nodeId'], 'math:target')
        self.assertLessEqual(sum(len(n['nodes']) for n in native['neighborhoods']), native['maxNativeNodes'])
        self.assertLessEqual(len(graph._json(context)), 8000)
        from tutor_context import context_for
        teaching = context_for(self.question, self.root, layer='US')
        self.assertEqual(teaching['layer'], 'US')
        self.assertEqual(teaching['knowledgeGraph']['routes'], mapping['routes'])
        for field in ('grade', 'level', 'curriculumUnit'):
            self.assertIsNone(context_for(self.question, self.root)[field])

    def install_tutor_foundations(self):
        self.install('exact')
        self.alignments.append({**self.alignments[0], 'id': 'cn-crosswalk', 'layer': 'CN'})
        for layer in self.curricula['layers']:
            layer['nodes'] += [{'id': n, 'label': n, 'description': 'A complete native definition.',
                                'criteria': ['Explain the native operation.'], 'placement': {'grade': 7}}
                               for n in ('preparation', 'successor', 'grandparent', 'child', 'related',
                                         'rejected', 'unresolved', 'undirected')]
            layer['nodes'][0]['description'] = 'A full mathematical definition with conditions. ' * 9
            layer['nodes'][0]['criteria'] = ['Explain and use the stated conditions.']
            layer['relationships'] = [
                {'id': edge_id, 'fromId': dependent, 'toId': foundation, 'relation': relation,
                 'status': status, 'directed': directed,
                 'directionMeaning': 'dependent to prerequisite/supporting foundation'}
                for edge_id, dependent, foundation, relation, status, directed in (
                    ('z-required', 'standard', 'foundation', 'prerequisite', 'accepted', True),
                    ('a-preparation', 'standard', 'preparation', 'supports', 'accepted', True),
                    ('successor-edge', 'successor', 'standard', 'prerequisite', 'accepted', True),
                    ('second-hop', 'foundation', 'grandparent', 'prerequisite', 'accepted', True),
                    ('child-edge', 'standard', 'child', 'contains', 'accepted', True),
                    ('related-edge', 'standard', 'related', 'related', 'accepted', False),
                    ('rejected-edge', 'standard', 'rejected', 'prerequisite', 'rejected', True),
                    ('unresolved-edge', 'standard', 'unresolved', 'supports', 'unresolved', True),
                    ('undirected-edge', 'standard', 'undirected', 'supports', 'accepted', False))]
        self.write_curricula()
        graph.build_database(self.root)

    def test_tutor_foundations_follow_direction_without_changing_browse_neighbors(self):
        self.install_tutor_foundations()
        for layer in ('CN', 'US'):
            with self.subTest(layer=layer):
                tutor = curriculum.compact_tutor_prerequisites('math:target', layer, self.root)
                self.assertEqual([n['id'] for n in tutor['nodes']], ['standard', 'foundation', 'preparation'])
                self.assertEqual([(e['fromId'], e['relation'], e['toId']) for e in tutor['relationships']],
                                 [('standard', 'prerequisite', 'foundation'), ('standard', 'supports', 'preparation')])
                self.assertTrue(all(e['directed'] for e in tutor['relationships']))
                self.assertFalse(tutor['truncated'])
                browse = curriculum.layer_neighborhood('math:target', layer, self.root)
                browse_ids = {n['id'] for n in browse['nodes']}
                self.assertTrue({'successor', 'child', 'related', 'undirected'} <= browse_ids)
                self.assertNotIn('grandparent', browse_ids)
                compact_browse = curriculum.compact_neighborhood('math:target', layer, self.root)
                self.assertIn('successor', {n['id'] for n in compact_browse['nodes']})

    def test_tutor_prompt_retains_definitions_criteria_routes_and_only_direct_foundations(self):
        from practice_tutor import review_prompt
        self.install_tutor_foundations()
        context = graph.context_for_question(self.question, self.root, layer='US', depth=20, selected_node_id='standard')
        native = context['curriculumContext']['neighborhoods'][0]
        self.assertEqual(native['depth'], 1)
        self.assertEqual({n['id'] for n in native['nodes']}, {'standard', 'foundation', 'preparation'})
        root_node = next(n for n in native['nodes'] if n['id'] == 'standard')
        self.assertEqual(root_node['description'], self.curricula['layers'][1]['nodes'][0]['description'])
        self.assertGreater(len(root_node['description']), 320)
        self.assertEqual(root_node['criteria'], ['Explain and use the stated conditions.'])
        self.assertEqual(context['routes'], self.source['mappings'][0]['routes'])
        self.assertEqual(context['binding']['status'], 'current')
        canonical = next(n for n in context['nodes'] if n['id'] == 'math:target')
        self.assertEqual(canonical['criteria'], self.source['nodes'][0]['criteria'])
        prompt = json.loads(review_prompt(self.question, '3', 'I expanded.', 'partial', 'wrong', 'wrong',
                                         root=self.root, layer='US', selected_node_id='standard'))
        self.assertEqual(prompt['teachingContext']['knowledgeGraph']['curriculumContext']['neighborhoods'][0]['nodes'], native['nodes'])
        self.assertLessEqual(len(graph._json(context)), 8000)

    def test_tutor_budget_keeps_required_foundation_before_helpful_preparation(self):
        self.install_tutor_foundations()
        tutor = curriculum.compact_tutor_prerequisites('math:target', 'US', self.root, limit=2)
        self.assertEqual([n['id'] for n in tutor['nodes']], ['standard', 'foundation'])
        self.assertEqual([e['relation'] for e in tutor['relationships']], ['prerequisite'])
        self.assertEqual(tutor['omissions'], {'nodes': 1, 'relationships': 1})
        self.assertTrue(tutor['truncated'])
        full_budget = curriculum.compact_tutor_prerequisites('math:target', 'US', self.root, limit=1,
                                                             existing_node_ids={'foundation'})
        self.assertEqual(full_budget['nodes'], [])
        self.assertEqual(full_budget['relationships'], [])
        roots = curriculum.compact_tutor_prerequisites('math:target', 'US', self.root, depth=0)
        self.assertEqual([n['id'] for n in roots['nodes']], ['standard'])
        self.assertEqual(roots['relationships'], [])

    def test_tutor_selection_and_unmapped_crosswalk_never_invent_foundations(self):
        self.install_tutor_foundations()
        self.alignments.append({**self.alignments[0], 'id': 'another-native-root', 'sourceNodeId': 'unmapped'})
        self.write_curricula()
        graph.build_database(self.root)
        selected = curriculum.compact_tutor_prerequisites('math:target', 'US', self.root, source_node_id='standard')
        self.assertNotIn('unmapped', {n['id'] for n in selected['nodes']})
        isolated = curriculum.compact_tutor_prerequisites('math:target', 'US', self.root, source_node_id='unmapped')
        self.assertEqual([n['id'] for n in isolated['nodes']], ['unmapped'])
        self.assertEqual(isolated['relationships'], [])
        missing = curriculum.compact_tutor_prerequisites('math:method', 'US', self.root)
        self.assertEqual(missing['status'], 'unmapped')
        self.assertEqual(missing['nodes'], [])
        self.assertEqual(missing['relationships'], [])

    def test_native_budget_reports_question_concepts_not_expanded(self):
        self.install_tutor_foundations()
        self.alignments.append({**self.alignments[0], 'id': 'method-root', 'nodeId': 'math:method',
                                'sourceNodeId': 'unmapped'})
        self.alignments.append({**self.alignments[0], 'id': 'alternative-root', 'nodeId': 'math:alternative',
                                'sourceNodeId': 'child'})
        self.write_curricula()
        graph.build_database(self.root)
        context = graph.context_for_question(self.question, self.root, layer='US', max_nodes=3)
        native = context['curriculumContext']
        self.assertEqual(native['maxNativeNodes'], 3)
        self.assertEqual(native['omissions']['neighborhoods'], 2)
        self.assertTrue(native['truncated'])
        self.assertEqual(context['routes'], self.source['mappings'][0]['routes'])
        self.assertEqual({n['id'] for group in native['neighborhoods'] for n in group['nodes']},
                         {'standard', 'foundation', 'preparation'})

    def test_native_budget_counts_shared_foundations_once_across_method_routes(self):
        self.install_tutor_foundations()
        self.alignments += [
            {**self.alignments[0], 'id': 'method-root', 'nodeId': 'math:method', 'sourceNodeId': 'foundation'},
            {**self.alignments[0], 'id': 'alternative-root', 'nodeId': 'math:alternative', 'sourceNodeId': 'preparation'}]
        self.write_curricula()
        graph.build_database(self.root)
        context = graph.context_for_question(self.question, self.root, layer='US', max_nodes=4)
        native = context['curriculumContext']
        self.assertEqual(len(native['neighborhoods']), 3)
        unique_ids = {n['id'] for group in native['neighborhoods'] for n in group['nodes']}
        self.assertEqual(unique_ids, {'standard', 'foundation', 'preparation', 'grandparent'})
        self.assertEqual(native['omissions']['neighborhoods'], 0)
        self.assertFalse(native['truncated'])
        method = next(n for n in native['neighborhoods'] if n['nodeId'] == 'math:method')
        self.assertEqual([(e['fromId'], e['toId']) for e in method['relationships']], [('foundation', 'grandparent')])
        self.assertEqual({n['id'] for n in method['nodes']}, {'foundation', 'grandparent'})

    def test_api_projects_native_browse_and_validates_queries(self):
        from serve_math_practice import knowledge_payload
        self.install()
        browse = knowledge_payload('browse', 'layer=US', self.root)
        self.assertEqual(len(browse['nodes']), 3)
        self.assertEqual(set(browse['nodes'][0]), {'id', 'label', 'description', 'placement'})
        practice = knowledge_payload('practice', 'layer=US&sourceNodeId=standard', self.root)
        self.assertEqual(practice['candidates'][0]['questionId'], self.question['ID'])
        self.assertEqual(knowledge_payload('practice', 'layer=US&sourceNodeId=unmapped', self.root)['candidates'], [])
        for query in ('layer=wrong', 'layer=US&layer=CN', 'layer=US&sourceNodeId=missing',
                      'layer=US&sourceNodeId=standard&nodeId=math:target', 'layer=US&extra=1'):
            with self.subTest(query=query), self.assertRaises(graph.GraphError):
                knowledge_payload('practice', query, self.root)

    def test_handler_rejects_unknown_layer_before_assessment(self):
        import io
        from unittest.mock import MagicMock
        from serve_math_practice import Handler
        handler = MagicMock()
        body = json.dumps({'curriculumLayer': 'wrong'}).encode()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.local_request.return_value = True
        Handler.assessment(handler)
        self.assertEqual(handler.error_json.call_args.args[0], 400)
        handler.current_assessor.assert_not_called()

    def test_tutor_prompt_captures_selected_layer(self):
        from practice_tutor import review_prompt
        self.install('exact')
        for layer in ('ailleo', 'US', 'CN'):
            prompt = json.loads(review_prompt(self.question, '3', 'I expanded it.', 'partial', 'wrong', 'wrong', root=self.root, layer=layer))
            teaching = prompt['teachingContext']
            self.assertEqual(teaching['layer'], layer)
            self.assertEqual(teaching['knowledgeGraph']['routes'], self.source['mappings'][0]['routes'])
            self.assertIsNone(teaching['grade'])

    def test_selected_standard_reaches_prompt_without_unrelated_crosswalk_seeds(self):
        from practice_tutor import review_prompt
        self.install('exact')
        self.alignments.append({**self.alignments[0], 'id': 'other-scope', 'sourceNodeId': 'unmapped'})
        self.write_curricula()
        graph.build_database(self.root)
        prompt = json.loads(review_prompt(self.question, '3', 'I expanded.', 'partial', 'wrong', 'wrong', root=self.root, layer='US', selected_node_id='standard'))
        native = prompt['teachingContext']['knowledgeGraph']['curriculumContext']
        self.assertEqual(native['selection']['nodeId'], 'standard')
        self.assertEqual(native['selection']['status'], 'matched')
        self.assertEqual({a['sourceNodeId'] for n in native['neighborhoods'] for a in n['alignments']}, {'standard'})
        self.assertNotIn('unmapped', {n['id'] for group in native['neighborhoods'] for n in group['nodes']})
        mismatch = graph.context_for_question(self.question, self.root, layer='US', selected_node_id='foundation')['curriculumContext']
        self.assertEqual(mismatch['selection']['status'], 'unrelated_to_question')
        self.assertTrue(any(n['alignments'] for n in mismatch['neighborhoods']))
        with self.assertRaises(graph.GraphError):
            graph.context_for_question(self.question, self.root, layer='US', selected_node_id='missing')

    def test_source_practice_merges_complete_routes_and_assessed_roles(self):
        self.install('exact')
        self.alignments.append({**self.alignments[0], 'id': 'method-crosswalk', 'nodeId': 'math:method'})
        self.write_curricula()
        graph.build_database(self.root)
        candidate = curriculum.practice_for_source('standard', 'US', self.root)['candidates'][0]
        self.assertEqual([r['id'] for r in candidate['routes']], ['distribution'])
        self.assertTrue(candidate['assessed'])
        self.assertEqual(candidate['routes'][0]['nodeIds'], ['math:method'])
        self.alignments[1]['id'] = 'a-first-method'
        self.write_curricula()
        graph.build_database(self.root)
        self.assertTrue(curriculum.practice_for_source('standard', 'US', self.root)['candidates'][0]['assessed'])

    def test_practice_ranks_direct_simple_concept_before_old_complex_route(self):
        self.install('exact')
        question = {**self.question, 'ID': 'cnm_000_q1'}
        (self.question_path.parent / 'cnm_000_q1.json').write_text(json.dumps(question), encoding='utf-8')
        mapping = {**self.source['mappings'][0], 'questionId': question['ID'],
                   **graph.question_fingerprint(question, self.root), 'assessedIds': ['math:alternative'],
                   'routes': [{'id': 'complex', 'label': 'A compound route', 'nodeIds': ['math:target', 'math:method', 'math:hidden']}]}
        self.source['mappings'].append(mapping)
        self._write_source()
        graph.build_database(self.root)
        for candidates in (curriculum.practice_candidates('math:target', 'ailleo', self.root, limit=1)['candidates'],
                           curriculum.practice_for_source('standard', 'US', self.root, limit=1)['candidates']):
            self.assertEqual(candidates[0]['questionId'], self.question['ID'])
            self.assertTrue(candidates[0]['assessed'])
            self.assertEqual(candidates[0]['additionalConceptCount'], 1)

    def test_handler_rejects_unknown_native_selection_before_model_work(self):
        import io
        from unittest.mock import MagicMock
        from serve_math_practice import Handler
        self.install()
        handler = MagicMock()
        body = json.dumps({'curriculumLayer': 'US', 'curriculumNodeId': 'unknown'}).encode()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.local_request.return_value = True
        handler.current_assessor.return_value.root = self.root
        Handler.assessment(handler)
        self.assertEqual(handler.error_json.call_args.args[0], 400)
        handler.current_assessor.return_value.assess.assert_not_called()


if __name__ == '__main__':
    unittest.main()
