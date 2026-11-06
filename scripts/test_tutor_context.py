"""Task-bound graph integration and compatible optional pilot route detail."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest

from knowledge_graph import build_database, question_fingerprint
from tutor_context import context_for, GRAPH_REVISION, ITEMS, KNOWLEDGE


ROOT = Path(__file__).resolve().parents[1]


class TutorContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shipped_questions = {key: json.loads((ROOT / 'cn-math-bank/questions' / (key + '.json')).read_text(encoding='utf-8'))
                         for key in ITEMS}
        # Legacy-route behavior is checked against the exact legacy task fixture.
        # Shipped tasks are independently checked below and must pass the same guard.
        cls.questions = {}
        for key, item in ITEMS.items():
            question = deepcopy(cls.shipped_questions[key])
            question.update(ID=key, Bank='cn-math', Language='en', Question=item['question'],
                            Grade=item['grade'], Level='Middle school',
                            **{'Correct Answer': item['answer'], 'ResponseType': 'numeric', 'Choices': {},
                               'Accepted Answers': [], 'Rejected Answers': [], 'Answer Form': None,
                               'Unordered Answers': item['unordered'], 'GradingStatus': None,
                               'skill': ['skill:cn:' + topic for topic in item['taskTopics']]})
            question['Meta'].update(SourceRevision=GRAPH_REVISION, SourceQuestionID=key, SourceTopicID=item['sourceTopic'])
            question['Topic']['id'] = item['sourceTopic']
            cls.questions[key] = question
        temporary = tempfile.TemporaryDirectory(prefix='tutor-fallback-test-')
        cls.addClassCleanup(temporary.cleanup)
        cls.fallback_root = Path(temporary.name)

    def context(self, question):
        return context_for(question, root=self.fallback_root)

    def test_exact_legacy_pilots_keep_two_routes_in_gradeless_fallback(self):
        for key, question in self.questions.items():
            with self.subTest(item=key):
                context = self.context(question)
                self.assertEqual(len(context['candidateRoutes']), 2)
                self.assertIsNone(context['grade'])
                self.assertIsNone(context['level'])
                self.assertIsNone(context['curriculumUnit'])
                self.assertIn('gradeless', context['levelMeaning'])
                self.assertEqual(context['pilotReview']['sourceRevision'], GRAPH_REVISION)
                self.assertEqual(context['knowledgeGraph']['reason'], 'database_missing')
                self.assertEqual(context['contextSource'], 'displayed_task')
                self.assertIn('OR examples', context['contextLimits'])
                self.assertNotIn('studentRoute', context)
                self.assertNotIn('mastery', context)

    def test_both_square_routes_without_assigning_bare_square_to_one(self):
        routes = self.context(self.questions['cnm_221_q2'])['candidateRoutes']
        self.assertEqual([k['topicId'] for k in routes[0]['localKnowledge']], ['cnm_148'])
        self.assertEqual([k['topicId'] for k in routes[1]['localKnowledge']], ['cnm_146', 'cnm_034'])
        self.assertIn('does not distinguish', routes[1]['evidenceMarkers'][0])
        self.assertIn('(x+t)(x+t)', routes[1]['evidenceMarkers'][0])

    def test_pilot_route_steps_are_distinct_from_the_source_unit(self):
        context = self.context(self.questions['cnm_267_q2'])
        knowledge = [entry['topicId'] for route in context['candidateRoutes'] for entry in route['localKnowledge']]
        self.assertNotIn('cnm_267', knowledge)
        self.assertIn('cnm_232', knowledge)
        self.assertIn('does not demonstrate completing the square', context['candidateRoutes'][1]['evidenceMarkers'][0])
        self.assertNotIn('sourceTopicId', context)
        self.assertNotIn('taskTopicIds', context)
        routes = self.context(self.questions['cnm_225_q4'])['candidateRoutes']
        self.assertIn('quadratic-formula', routes[1]['evidenceMarkers'][0])

    def test_semantic_or_source_drift_cannot_receive_fallback_pilot_routes(self):
        changes = {'Bank': 'amc', 'ID': 'cnm_221_q3', 'Question': 'What is 1*3?',
                   'Correct Answer': '3', 'ResponseType': 'choice', 'Choices': {'A': '9'},
                   'Accepted Answers': ['3'], 'Rejected Answers': ['9'], 'Answer Form': 'decimal',
                   'Unordered Answers': True, 'GradingStatus': 'disputed', 'Language': 'zh',
                   'Grade': 7, 'Level': 'High school', 'skill': ['skill:cn:cnm_235']}
        question = self.questions['cnm_221_q2']
        for field, value in changes.items():
            with self.subTest(field=field):
                self.assertEqual(self.context({**question, field: value})['candidateRoutes'], [])
        for field in ('SourceRevision', 'SourceQuestionID', 'SourceTopicID'):
            changed = deepcopy(question)
            changed['Meta'][field] = 'changed'
            self.assertEqual(self.context(changed)['candidateRoutes'], [])
        changed = deepcopy(question)
        changed['Topic']['id'] = 'cnm_235'
        self.assertEqual(self.context(changed)['candidateRoutes'], [])

    def test_unmapped_tasks_remain_gradeless_with_an_explicit_graph_state(self):
        for question in ({'ID': '2023_AMC_8_Q01', 'Bank': 'amc', 'Grade': 8, 'Level': 'AMC 8'},
                         {'ID': 'custom__one', 'Grade': 6},
                         {'ID': 'cnm_s001_q1', 'Grade': 14, 'CurriculumUnit': 'Elective volume'}, {}):
            context = self.context(question)
            self.assertEqual(context['candidateRoutes'], [])
            self.assertIsNone(context['grade'])
            self.assertIsNone(context['curriculumUnit'])
            self.assertEqual(context['knowledgeGraph']['status'], 'missing')
            self.assertNotIn('relevanceHints', context)
        self.assertIsNone(self.context({'Grade': True})['grade'])
        self.assertIsNone(self.context({'Grade': 0})['grade'])
        self.assertIsNone(self.context(None)['grade'])

    def test_every_shipped_task_has_bounded_fallback_without_unreviewed_labels(self):
        seen, pilots = 0, 0
        for bank in ('cn-math-bank', 'amc-bank'):
            for path in (ROOT / bank / 'questions').glob('*.json'):
                question = json.loads(path.read_text(encoding='utf-8'))
                context = self.context(question)
                self.assertIsNone(context['grade'], path.name)
                self.assertIsNone(context['level'], path.name)
                self.assertIsNone(context['curriculumUnit'], path.name)
                self.assertNotIn('relevanceHints', context)
                self.assertNotIn('Original', json.dumps(context))
                self.assertLess(len(json.dumps(context, ensure_ascii=False)), 5000, path.name)
                pilots += bool(context['candidateRoutes'])
                seen += 1
        self.assertGreater(seen, 8000)
        self.assertEqual(pilots, len(ITEMS))

    def test_source_conflict_custom_tags_and_whole_original_are_not_tutor_context(self):
        question = {'Bank': 'custom', 'Topic': {'id': 'cnm_221', 'label': 'Incorrect source method'},
                    'skill': ['skill:cn:cnm_221'], 'domain': ['domain:algebra'],
                    'Meta': {'Concepts': 'Wrong concept', 'Original': {'raw': 'Private original'}}}
        serialized = json.dumps(self.context(question))
        for text in ('Incorrect source method', 'Wrong concept', 'Private original', 'skill:cn:cnm_221'):
            self.assertNotIn(text, serialized)

    def test_returned_route_edits_do_not_mutate_later_context(self):
        question = self.questions['cnm_221_q2']
        first = self.context(question)
        first['candidateRoutes'][0]['localKnowledge'][0]['topicId'] = 'fake'
        self.assertEqual(self.context(question)['candidateRoutes'][0]['localKnowledge'][0]['topicId'], 'cnm_148')

    def test_route_algebra_on_representative_values(self):
        for x in (-5, -1, 0, 2, Fraction(2, 3)):
            self.assertEqual((x + 3) ** 2, x*x + x*3 + 3*x + 3*3)
            self.assertEqual((2*x - 3)**2 - (x + 1)**2, (x - 4)*(3*x - 2))
            self.assertEqual(-x*x + 6*x, -(x - 3)**2 + 9)
        x, y = 2, 3
        self.assertEqual((3*x + 2*y) - (3*x - y), 12 - 3)
        self.assertEqual(3*x + 2*(3*x - 3), 12)
        for x in (4, Fraction(2, 3)):
            self.assertEqual((2*x - 3)**2, (x + 1)**2)
        vertex_x = Fraction(-6, 2 * -1)
        self.assertEqual(-vertex_x**2 + 6*vertex_x, 9)

    def test_pinned_graph_ids_and_original_questions_when_available(self):
        source = ROOT.parent / 'cn-math-bank/source/revisions' / GRAPH_REVISION
        if not source.is_dir():
            self.skipTest('Pinned snapshot is outside the standalone release')
        topics = {entry['id']: entry for entry in json.loads((source / 'topics.json').read_text(encoding='utf-8'))}
        for topic_id, _ in KNOWLEDGE.values():
            self.assertIn(topic_id, topics)
        originals = {entry['id']: entry for entry in json.loads((source / 'questions.json').read_text(encoding='utf-8'))}
        for key, question in self.shipped_questions.items():
            self.assertEqual(question['Meta']['Original'], originals[key])


class CanonicalGraphTutorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='tutor-graph-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.question = json.loads((ROOT / 'cn-math-bank/questions/cnm_221_q2.json').read_text(encoding='utf-8'))
        self.question.pop('KnowledgeGraph', None)
        path = self.root / 'cn-math-bank/questions' / (self.question['ID'] + '.json')
        path.parent.mkdir(parents=True)
        self.question_path = path
        self.nodes = [{'id': node_id, 'name': label, 'nameZh': '', 'description': description,
                       'criteria': ['Carry out this local mathematical step.'], 'level': '8',
                       'kind': 'procedure', 'aliases': [], 'sourceId': 'fixture', 'sourceRevision': 'one',
                       'reviewStatus': 'fixture_reviewed'}
                      for node_id, label, description in [
                          ('cnm_148', 'Perfect-square identity', 'Match the linear and constant terms.'),
                          ('cnm_146', 'Expand a product', 'Multiply each term in the two binomials.'),
                          ('cnm_034', 'Collect like terms', 'Add coefficients of like terms.'),
                          ('math:other', 'Other method', 'An independently described alternative.')]]
        self.mapping = {'questionId': self.question['ID'], 'bank': self.question['Bank'],
                        **question_fingerprint(self.question, self.root), 'status': 'mapped',
                        'reviewStatus': 'fixture_reviewed', 'assessedIds': ['cnm_148'], 'supportIds': [],
                        'routes': [{'id': 'central_identity', 'label': 'Match the identity', 'nodeIds': ['cnm_148']},
                                   {'id': 'central_distribution', 'label': 'Expand the product', 'nodeIds': ['cnm_146', 'cnm_034']}],
                        'sourceTopicAgreement': 'conflicting', 'flags': ['source_label_conflict'],
                        'rationale': 'Displayed task is completing a binomial square.',
                        'answerCheck': {'status': 'checked'}, 'reviews': [{'reviewer': 'fixture'}]}
        self.relationships = [{'id': 'identity-preparation', 'nodeId': 'cnm_148', 'prerequisiteId': 'cnm_146',
                               'relation': 'prepares', 'methodId': None, 'scope': 'One binomial identity.',
                               'reason': 'Expansion can check the identity.', 'status': 'accepted',
                               'reviewStatus': 'fixture_reviewed', 'original': {}, 'reviews': [{'reviewer': 'fixture'}]}]

    def build(self):
        self.question_path.write_text(json.dumps(self.question), encoding='utf-8')
        source = self.root / 'knowledge-graph/source'
        source.mkdir(parents=True, exist_ok=True)
        for field, value in [('metadata', {'version': 'tutor-fixture-v1'}), ('nodes', self.nodes),
                             ('relationships', self.relationships)]:
            (source / (field + '.json')).write_text(json.dumps(value), encoding='utf-8')
        (source / 'mappings.jsonl').write_text(json.dumps(self.mapping) + '\n', encoding='utf-8')
        return build_database(self.root)

    def test_current_mapping_overrides_inaccurate_old_unit_labels(self):
        self.question['Topic'] = {'id': 'cnm_267', 'label': 'Incorrect circle source label'}
        self.question['Meta']['SourceTopicID'] = 'cnm_267'
        self.question['skill'] = ['skill:cn:cnm_267']
        self.build()
        context = context_for(self.question, root=self.root)
        self.assertEqual(context['contextSource'], 'central_graph')
        self.assertEqual(context['knowledgeGraph']['assessedIds'], ['cnm_148'])
        self.assertNotIn('Incorrect circle source label', json.dumps(context))
        for field in ('relevanceHints', 'sourceTopicId', 'taskTopicIds', 'routePlanning', 'contextLimits'):
            self.assertNotIn(field, context)
        self.assertEqual(len(context['candidateRoutes']), 2)

    def test_non_diagnostic_uses_bound_definitions_without_pilot_or_mastery_claim(self):
        self.mapping.update(status='non_diagnostic', assessedIds=[], supportIds=[], routes=[],
                            contextualIds=['cnm_148'], flags=['answer_relation_supplied'])
        self.build()
        before = json.dumps(self.question, sort_keys=True)
        context = context_for(self.question, root=self.root)
        self.assertEqual(context['contextSource'], 'central_graph')
        self.assertEqual(context['candidateRoutes'], [])
        self.assertNotIn('routePlanning', context)
        self.assertNotIn('pilotReview', context)
        self.assertIn('Do not infer mastery', context['diagnosticMeaning'])
        self.assertEqual(context['knowledgeGraph']['status'], 'non_diagnostic')
        self.assertEqual(context['knowledgeGraph']['nodes'], [])
        self.assertEqual(context['knowledgeGraph']['edges'], [])
        self.assertEqual(context['knowledgeGraph']['contextualNodes'][0]['id'], 'cnm_148')
        self.assertEqual(json.dumps(self.question, sort_keys=True), before)

    def test_method_alternatives_remain_canonical_with_only_compatible_pilot_notes(self):
        self.build()
        context = context_for(self.question, root=self.root)
        self.assertEqual(context['knowledgeGraph']['routes'], self.mapping['routes'])
        self.assertEqual([route['id'] for route in context['candidateRoutes']], ['central_identity', 'central_distribution'])
        by_id = {route['id']: route for route in context['knowledgeGraph']['routes']}
        for note in context['candidateRoutes']:
            self.assertEqual({part['topicId'] for part in note['localKnowledge']}, set(by_id[note['id']]['nodeIds']))
        self.assertEqual(context['knowledgeGraph']['assessedIds'], ['cnm_148'])
        self.assertNotIn('mastery', context)
        self.mapping['routes'] = [{'id': 'central_other', 'label': 'A different valid method', 'nodeIds': ['math:other']}]
        self.build()
        self.assertEqual(context_for(self.question, root=self.root)['candidateRoutes'], [])

    def test_route_only_mapping_uses_central_alternatives_without_legacy_fallback(self):
        self.mapping['assessedIds'] = []
        self.mapping['routes'][0] = {'id': 'central_other', 'label': 'Another reviewed method',
                                    'nodeIds': ['math:other']}
        report = self.build()
        self.assertEqual(report['completedMappings'], 1)
        context = context_for(self.question, root=self.root)
        self.assertEqual(context['contextSource'], 'central_graph')
        self.assertEqual(context['knowledgeGraph']['status'], 'mapped')
        self.assertEqual(context['knowledgeGraph']['assessedIds'], [])
        self.assertEqual(context['knowledgeGraph']['routes'], self.mapping['routes'])
        self.assertEqual([route['id'] for route in context['candidateRoutes']], ['central_distribution'])
        from practice_tutor import review_prompt
        prompt = json.loads(review_prompt(self.question, '9', 'I matched the square.',
                                         'partial', 'correct', 'correct', root=self.root))
        self.assertEqual(prompt['teachingContext']['contextSource'], 'central_graph')
        self.assertEqual(prompt['teachingContext']['knowledgeGraph']['assessedIds'], [])
        self.assertEqual(prompt['teachingContext']['knowledgeGraph']['routes'], self.mapping['routes'])
        for field in ('pilotReview', 'routePlanning', 'contextLimits', 'mastery'):
            self.assertNotIn(field, context)
        # Omitting every complete route for the character budget must still use
        # the current central binding, not the exact older pilot or source tags.
        for node in self.nodes:
            node['description'] *= 1000
        self.build()
        compact = context_for(self.question, root=self.root)
        self.assertEqual(compact['contextSource'], 'central_graph')
        self.assertEqual(compact['knowledgeGraph']['binding']['status'], 'current')
        self.assertEqual(compact['knowledgeGraph']['status'], 'mapped')
        self.assertEqual(compact['knowledgeGraph']['routes'], [])
        self.assertEqual(compact['knowledgeGraph']['nodes'], [])
        self.assertEqual(compact['knowledgeGraph']['omissions']['routes'], 2)
        self.assertEqual(compact['candidateRoutes'], [])
        self.assertNotIn('pilotReview', compact)
        self.assertNotIn('routePlanning', compact)

    def test_changed_stale_task_and_unresolved_mapping_use_displayed_task(self):
        self.build()
        changed = {**self.question, 'Question': 'What is $2+3$?'}
        context = context_for(changed, root=self.root)
        self.assertEqual(context['knowledgeGraph']['status'], 'stale')
        self.assertEqual(context['contextSource'], 'displayed_task')
        self.assertEqual(context['candidateRoutes'], [])
        self.assertNotIn('relevanceHints', context)
        self.mapping['status'] = 'unresolved'
        self.build()
        context = context_for(self.question, root=self.root)
        self.assertEqual(context['knowledgeGraph']['status'], 'unresolved')
        self.assertEqual(context['candidateRoutes'], [])
        self.assertEqual(context['knowledgeGraph']['nodes'], [])

    def test_missing_database_and_missing_mapping_are_explicit(self):
        missing = context_for(self.question, root=self.root)
        self.assertEqual(missing['knowledgeGraph']['reason'], 'database_missing')
        self.assertEqual(missing['contextSource'], 'displayed_task')
        self.assertEqual(len(missing['candidateRoutes']), 2)
        self.build()
        unknown = {**self.question, 'ID': 'cnm_221_q3'}
        context = context_for(unknown, root=self.root)
        self.assertEqual(context['knowledgeGraph']['reason'], 'mapping_missing')
        self.assertEqual(context['candidateRoutes'], [])

    def test_actual_root_bank_and_binding_are_respected(self):
        self.build()
        context = context_for(self.question, root=self.root)
        self.assertEqual(context['knowledgeGraph']['graphVersion'], 'tutor-fixture-v1')
        self.assertEqual(context['knowledgeGraph']['binding']['contentHash'], self.mapping['contentHash'])
        wrong_bank = {**self.question, 'Bank': 'amc'}
        self.assertEqual(context_for(wrong_bank, root=self.root)['knowledgeGraph']['status'], 'stale')
        with tempfile.TemporaryDirectory(prefix='other-tutor-root-') as other:
            self.assertEqual(context_for(self.question, root=other)['knowledgeGraph']['reason'], 'database_missing')

    def test_graph_context_is_bounded_deterministic_and_independent_of_returned_edits(self):
        self.build()
        first = context_for(self.question, root=self.root)
        self.assertEqual(first, context_for(self.question, root=self.root))
        self.assertLessEqual(len(first['knowledgeGraph']['nodes']), 16)
        self.assertLessEqual(len(json.dumps(first['knowledgeGraph'], ensure_ascii=False, separators=(',', ':'))), 8000)
        self.assertLess(len(json.dumps(first, ensure_ascii=False)), 9000)
        first['candidateRoutes'][0]['localKnowledge'][0]['topicId'] = 'tampered'
        first['knowledgeGraph']['nodes'][0]['description'] = 'tampered'
        self.assertNotIn('tampered', json.dumps(context_for(self.question, root=self.root)))


if __name__ == '__main__':
    unittest.main()
