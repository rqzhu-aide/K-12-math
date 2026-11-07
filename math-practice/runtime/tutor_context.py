"""Current central graph context and compatible optional pilot route details."""
from copy import deepcopy
from pathlib import Path

from knowledge_graph import context_for_question


GRAPH_REVISION = '62b341d4b66b175413d6e3f697e37639fd96aa2d'
ROOT = Path(__file__).resolve().parents[2]
MAPPING_VERSION = 'reviewed-tutor-routes-v1'
LEVEL_MEANING = (
    'The bank grade index and curriculum unit locate the item; indexes may name course '
    'volumes rather than school years. This is not a learner profile or a claim about prior knowledge.'
)
CONTEXT_LIMITS = (
    'Optional OR examples, not an exhaustive menu or required sequence. '
    'A shared intermediate or bare answer does not identify a route. '
    'These local substeps do not establish topic mastery or a persistent gap.'
)
ROUTE_PLANNING = (
    'Infer useful local knowledge from the displayed task and the student work. '
    'Consider valid alternatives; follow the method shown and keep uncertainty when steps are missing.'
)


def _text(value, limit=160):
    return value.strip()[:limit] if isinstance(value, str) and value.strip() else None


# Reused local knowledge descriptions, with actual IDs from the pinned graph.
# A route may use only this substep of a source concept, not its other criteria.
KNOWLEDGE = {
    'square_identity': ('cnm_148', 'Match the linear and constant terms in a perfect-square identity.'),
    'distribute_product': ('cnm_146', 'Multiply each term of one binomial by each term of the other.'),
    'combine_terms': ('cnm_034', 'Combine like terms by adding their coefficients.'),
    'signed_parentheses': ('cnm_035', 'Distribute a leading sign or coefficient to every term in parentheses.'),
    'linear_equation': ('cnm_042', 'Preserve equality while collecting terms and solving a linear equation.'),
    'substitution': ('cnm_089', 'Express one variable in terms of another and substitute into the other equation.'),
    'elimination': ('cnm_090', 'Add or subtract whole equations so matching coefficients cancel a variable.'),
    'absolute_square_root': ('cnm_075', 'Use the absolute value when taking the square root of a squared real expression.'),
    'difference_squares': ('cnm_152', 'Factor a difference of two squares as the product of their sum and difference.'),
    'zero_product': ('cnm_224', 'For a product equal to zero, consider each factor equal to zero.'),
    'complete_vertex_form': ('cnm_232', 'Rewrite a quadratic in vertex form by completing the square.'),
    'vertex_location': ('cnm_232', 'Locate the axis or vertex of a quadratic using its general-form coefficients.'),
    'opening_direction': ('cnm_230', 'Use the sign of the leading coefficient to determine the opening direction.'),
    'attained_extremum': ('cnm_235', 'Justify an upper or lower bound and show where it is attained.'),
}


def _route(key, method, knowledge, marker):
    return {'id': key, 'method': method,
            'localKnowledge': [{'topicId': KNOWLEDGE[name][0], 'substep': KNOWLEDGE[name][1]}
                               for name in knowledge],
            'evidenceMarkers': [marker]}


ITEMS = {
    'cnm_221_q2': {
        'question': r'What constant must be added to \(x^2+6x\) to make it a perfect square?',
        'answer': '9', 'unordered': False, 'grade': 9, 'sourceTopic': 'cnm_221', 'taskTopics': ['cnm_221'],
        'routes': [
            _route('identity_match', 'Match a perfect-square identity', ['square_identity'],
                   'Matches the coefficient of x in (x+t)^2 and identifies the corresponding constant term.'),
            _route('distributed_product', 'Reconstruct the squared binomial by distribution',
                   ['distribute_product', 'combine_terms'],
                   'Shows individual products in (x+t)(x+t), then collects the two linear terms. '
                   'Both approaches establish the same identity; a bare squared number does not distinguish them.'),
        ],
    },
    'cnm_090_q3': {
        'question': r'Solve the system \(\begin{cases}3x+2y=12\\3x-y=3\end{cases}\). '
                    r'(Write the values of \(x\) and \(y\), in that order, separated by a comma.)',
        'answer': '2，3', 'unordered': False, 'grade': 7, 'sourceTopic': 'cnm_090', 'taskTopics': ['cnm_090'],
        'routes': [
            _route('subtract_equations', 'Eliminate by subtracting equations',
                   ['elimination', 'signed_parentheses', 'combine_terms', 'linear_equation'],
                   'Combines the two whole equations to cancel a variable; an isolated reduced equation '
                   'may also come from substitution.'),
            _route('substitute_variable', 'Express and substitute a variable',
                   ['substitution', 'signed_parentheses', 'combine_terms', 'linear_equation'],
                   'Replaces one variable in an equation using an expression obtained from the other equation.'),
        ],
    },
    'cnm_225_q4': {
        'question': r'Solve \((2x-3)²=(x+1)²\). (Separate the two roots with a comma, '
                    r'writing them as integers or fractions in lowest terms.)',
        'answer': '4，2/3', 'unordered': True, 'grade': 9, 'sourceTopic': 'cnm_225', 'taskTopics': ['cnm_225'],
        'routes': [
            _route('equal_square_branches', 'Consider equal and opposite expressions',
                   ['absolute_square_root', 'signed_parentheses', 'linear_equation'],
                   'Uses equality of squares to consider equal or opposite expressions. '
                   'Whether both sign cases are present is a separate completeness check.'),
            _route('difference_square_product', 'Factor a difference of squares',
                   ['difference_squares', 'signed_parentheses', 'zero_product', 'linear_equation'],
                   'Moves the squares to one side, forms a product, and considers zero factors. '
                   'A quadratic-formula solution is another valid unlisted route.'),
        ],
    },
    'cnm_267_q2': {
        'question': r'What is the maximum value of the quadratic function \(y=-x^2+6x\)?',
        'answer': '9', 'unordered': False, 'grade': 9, 'sourceTopic': 'cnm_267', 'taskTopics': ['cnm_235'],
        'routes': [
            _route('complete_square_bound', 'Complete the square and justify the bound',
                   ['square_identity', 'complete_vertex_form', 'attained_extremum'],
                   'Rewrites as a signed real square plus a constant, uses square nonnegativity, '
                   'and considers when equality holds.'),
            _route('vertex_properties', 'Use the vertex and opening direction',
                   ['vertex_location', 'opening_direction', 'attained_extremum'],
                   'Uses vertex coefficients or symmetry, evaluates the function there, '
                   'and explains why the vertex is a maximum. This does not demonstrate completing the square.'),
        ],
    },
}


def _pilot_item(question, *, require_source):
    """The mathematical task must match before any local route details are reused."""
    question_id = question.get('ID')
    item = ITEMS.get(question_id) if isinstance(question_id, str) else None
    if not item:
        return None
    expected = {'Bank': 'cn-math', 'Language': 'en', 'Question': item['question'],
                'Grade': item['grade'], 'Level': 'Middle school',
                'Correct Answer': item['answer'], 'ResponseType': 'numeric', 'Choices': {},
                'Accepted Answers': [], 'Rejected Answers': [], 'Answer Form': None,
                'Unordered Answers': item['unordered'], 'GradingStatus': None}
    if require_source:
        expected['skill'] = ['skill:cn:' + topic_id for topic_id in item['taskTopics']]
    if any(question.get(key, [] if key in ('Accepted Answers', 'Rejected Answers') else None) != value
           for key, value in expected.items()):
        return None
    if not require_source:
        return item
    meta = question.get('Meta')
    if not isinstance(meta, dict) or any(meta.get(key) != value for key, value in {
            'SourceRevision': GRAPH_REVISION, 'SourceQuestionID': question['ID'],
            'SourceTopicID': item['sourceTopic']}.items()):
        return None
    topic = question.get('Topic')
    if not isinstance(topic, dict) or topic.get('id') != item['sourceTopic']:
        return None
    return item


def _compatible_pilot_notes(question, graph):
    item = _pilot_item(question, require_source=False)
    if not item:
        return []
    resolved_ids = {node['id'] for node in graph['nodes']}
    notes = []
    for canonical in graph['routes']:
        for pilot in item['routes']:
            local_ids = {entry['topicId'] for entry in pilot['localKnowledge']}
            if local_ids == set(canonical['nodeIds']) and local_ids <= resolved_ids:
                notes.append({'id': canonical['id'], 'method': canonical['label'],
                              'localKnowledge': deepcopy(pilot['localKnowledge']),
                              'evidenceMarkers': list(pilot['evidenceMarkers']),
                              'reviewStatus': 'local_pilot_content_review'})
                break
    return notes


def context_for(question, root=ROOT, layer='ailleo', selected_node_id=None):
    """Use current content-bound graph data, otherwise tutor from the displayed task.

    Legacy unit/skill labels never override a central mapping or supply inferred
    prerequisites. The canonical reader reports absent/stale/unresolved states.
    The four older pilot tasks retain only compatible local mathematical detail.
    """
    if not isinstance(question, dict):
        question = {}
    graph = context_for_question(question, root=Path(root), layer=layer, selected_node_id=selected_node_id)
    context = {'layer': layer, 'grade': None, 'level': None, 'curriculumUnit': None,
               'levelMeaning': 'Ailleo is gradeless. Use the displayed mathematics and the learner method.' if layer == 'ailleo' else
                   'Placements belong to the selected native curriculum. Crosswalks can be partial and do not establish mastery.',
               'candidateRoutes': [], 'contextSource': 'displayed_task', 'knowledgeGraph': graph}
    if graph['status'] == 'non_diagnostic' and graph.get('binding', {}).get('status') == 'current':
        context['contextSource'] = 'central_graph'
        context['diagnosticMeaning'] = (
            'This item supplies the answer relation. Its contextual definitions are not assessed '
            'knowledge. Do not infer mastery or a gap from the response, or require topic prerequisites.'
        )
        return context
    if graph['status'] == 'mapped' and graph.get('binding', {}).get('status') == 'current':
        context['contextSource'] = 'central_graph'
        context['candidateRoutes'] = _compatible_pilot_notes(question, graph)
        return context
    context['routePlanning'] = ROUTE_PLANNING
    # An unavailable graph may use these independently checked exact pilot tasks.
    # A known stale or unresolved record cannot regain authority through old tags.
    if graph['status'] == 'missing' and graph.get('reason') == 'database_missing':
        item = _pilot_item(question, require_source=True)
        if item:
            context.update(pilotReview={'version': MAPPING_VERSION, 'sourceRevision': GRAPH_REVISION},
                           contextLimits=CONTEXT_LIMITS, candidateRoutes=deepcopy(item['routes']))
    return context
