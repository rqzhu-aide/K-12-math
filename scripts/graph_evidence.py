"""A narrow, source-checked CN item attribution pilot, returned only as shadow data.

This is not a mastery estimator or a general mathematical reasoning classifier.
It parses a bounded grammar of complete mathematical clauses for one reviewed
item. Unknown prose or claims outside that grammar remain unobserved.
No model wording, client criterion, or graph prerequisite is used as evidence.

Source checked against cn-math-bank/source/revisions/62b341d.../topics.json and
questions.json, and the packaged English cnm_221_q2 record. The upstream node's
first criterion is broader than this item. The local criterion below identifies
only the constant-term substep and does not claim to solve quadratic equations.
Independent educator labels are still required before leaving shadow mode.
"""
import ast
from fractions import Fraction
import re

from question_answers import exact_answer_category, numeric_value


GRAPH_REVISION = '62b341d4b66b175413d6e3f697e37639fd96aa2d'
PILOT_ITEM = 'cnm_221_q2'
MAPPING_VERSION = 'cn-square-constant-shadow-v2'
CRITERION_ID = 'cnm_221.mc0.square-half-coefficient.v1'
SOURCE_CRITERION_TEXT = '能完成配方'
CRITERION = 'Identify and justify the constant that makes the expression a perfect square.'
QUESTION_TEXT = r'What constant must be added to \(x^2+6x\) to make it a perfect square?'
SOURCE_QUESTION_TEXT = '要把 x²+6x 配成完全平方式，需要加上的常数是多少？'
ASSISTANCE = frozenset(('none', 'coach', 'hint', 'solution', 'unknown'))


def _mapped(question):
    """Bind to the actual reviewed item content, not its topic tag alone."""
    if not isinstance(question, dict):
        return False
    expected = {'ID': PILOT_ITEM, 'Bank': 'cn-math', 'Language': 'en',
                'ResponseType': 'numeric', 'Question': QUESTION_TEXT,
                'Correct Answer': '9', 'Choices': {},
                'Topic': {'id': 'cnm_221', 'label': 'Completing the Square'}}
    if any(question.get(key) != value for key, value in expected.items()):
        return False
    if (question.get('Accepted Answers', []) or question.get('Rejected Answers', [])
            or question.get('Unordered Answers', False) or question.get('Answer Form')
            or question.get('GradingStatus')):
        return False
    meta = question.get('Meta')
    if not isinstance(meta, dict):
        return False
    expected_meta = {'SourceRevision': GRAPH_REVISION,
                     'SourceQuestionID': 'cnm_221_q2', 'SourceTopicID': 'cnm_221'}
    if any(meta.get(key) != value for key, value in expected_meta.items()):
        return False
    original = meta.get('Original')
    expected_original = {'id': 'cnm_221_q2', 'topicId': 'cnm_221',
                         'type': 'numeric', 'prompt': SOURCE_QUESTION_TEXT, 'answer': '9'}
    return (isinstance(original, dict)
            and all(original.get(key) == value for key, value in expected_original.items()))


def criterion_for_prompt(question):
    """Return at most one backend-owned, item-specific criterion in English."""
    return CRITERION if _mapped(question) else None


def _poly_constant(value):
    return (Fraction(value), Fraction(0), Fraction(0))


def _expression(text):
    """Evaluate a tiny arithmetic/polynomial AST exactly, without executing it.

    The only variable is x; degree is at most two, powers must be squares,
    divisors constant, and literals/AST size bounded. Structural flags distinguish
    a justified square from an arbitrary true equality whose value happens to be 9.
    """
    text = re.sub(r'\b(\d+)\s*x\b', r'\1*x', text)
    text = re.sub(r'(?<=[0-9x)])\s*\(', '*(', text)
    text = re.sub(r'\)\s*(?=[0-9x])', ')*', text).replace('^', '**')
    # Python's parser would otherwise silently discard a trailing # comment.
    # Only mathematical characters may reach it; all prose must have been
    # consumed by the closed clause grammar above.
    if len(text) > 180 or not re.fullmatch(r'[0-9x+\-*/().\s]+', text):
        raise ValueError('Expression is outside the pilot grammar')
    tree = ast.parse(text.strip(), mode='eval')
    if len(list(ast.walk(tree))) > 70:
        raise ValueError('Expression is outside the pilot grammar')

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = Fraction(str(node.value))
            if abs(value) > 100 or value.denominator > 1000:
                raise ValueError('Literal is outside the pilot grammar')
            return _poly_constant(value), set()
        if isinstance(node, ast.Name) and node.id == 'x':
            return (Fraction(0), Fraction(1), Fraction(0)), set()
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value, flags = visit(node.operand)
            return tuple(-v for v in value) if isinstance(node.op, ast.USub) else value, flags
        if not isinstance(node, ast.BinOp):
            raise ValueError('Unknown expression')
        left, _ = visit(node.left)
        right, _ = visit(node.right)
        # A square hidden inside a cancelled or unrelated expression is not the
        # stated method. Keep structural evidence on the operation it verifies.
        flags = set()
        if isinstance(node.op, (ast.Add, ast.Sub)):
            sign = -1 if isinstance(node.op, ast.Sub) else 1
            value = tuple(a + sign * b for a, b in zip(left, right))
        elif isinstance(node.op, ast.Div) and right[1:] == (0, 0) and right[0]:
            value = tuple(v / right[0] for v in left)
            if left == _poly_constant(6) and right == _poly_constant(2):
                flags.add('half')
        elif isinstance(node.op, (ast.Mult, ast.Pow)):
            if isinstance(node.op, ast.Pow):
                if right != _poly_constant(2):
                    raise ValueError('Only squares are supported')
                right = left
            if left == right == _poly_constant(3):
                flags.add('square')
            if left == right == (3, 1, 0):
                flags.add('binomial')
            product = [sum(left[i] * right[j] for i in range(3) for j in range(3) if i + j == k)
                       for k in range(5)]
            if any(product[3:]):
                raise ValueError('Degree exceeds two')
            value = tuple(product[:3])
        else:
            raise ValueError('Unknown operation')
        if any(abs(v.numerator) > 10000 or v.denominator > 10000 for v in value):
            raise ValueError('Arithmetic is outside the pilot bounds')
        return value, flags

    return visit(tree.body)


def _math_words(text):
    # These compositional substitutions cover arithmetic language, not arbitrary
    # prose. The AST parser must consume the entire resulting expression.
    for number, word in enumerate(('zero', 'one', 'two', 'three', 'four', 'five',
                                    'six', 'seven', 'eight', 'nine', 'ten')):
        text = re.sub(r'\b' + word + r'\b', str(number), text)
    atom = r'(?:\([^()]+\)|\d+(?:\.\d+)?|x)'
    text = re.sub(r'half (?:of )?(?:the )?(?:linear coefficient|coefficient of x)', '(6/2)', text)
    text = re.sub(r'half of (' + atom + r')', r'(\1/2)', text)
    text = re.sub(r'(?:the )?square of (' + atom + r')', r'(\1)^2', text)
    text = re.sub(r'(' + atom + r') (?:squared|to the power of 2)', r'(\1)^2', text)
    text = re.sub(r'\b(?:multiplied by|times)\b', '*', text)
    text = re.sub(r'\b(?:divided by|over)\b', '/', text)
    return re.sub(r'\b(?:is|equals|gives|yields)\b', '=', text)


def _clause(text, previous):
    text = text.casefold().replace('²', '^2').replace('^{2}', '^2')
    for source, target in ((r'\(', ''), (r'\)', ''), ('$', ''), (r'\times', '*'),
                           (r'\cdot', '*'), ('×', '*'), ('·', '*'), ('−', '-')):
        text = text.replace(source, target)
    text = re.sub(r'\s+', ' ', text).strip().rstrip('.')
    referential = bool(re.search(r'\b(?:it|that|the result)\b', text))
    if referential:
        if not previous or previous['value'] != _poly_constant(3) or 'half' not in previous['flags']:
            raise ValueError('Ambiguous antecedent')
        text = re.sub(r'\b(?:it|that|the result)\b', '3', text)
    constant, operation = False, False
    match = re.fullmatch(r'(?:the )?(?:(?:missing|required) )?(?:constant(?: term)?|last term|number to add) (?:is|equals|=) (.+)', text)
    if match:
        text, constant = match[1], True
    else:
        match = re.fullmatch(r'(?:(?:i|we) )?(?:add|added|need|choose|chose) (.+)', text)
        if match:
            text, constant = match[1], True
    coefficient = re.fullmatch(r'(?:the )?(?:linear coefficient|coefficient of x) (?:is|equals|=) (.+)', text)
    if coefficient:
        value, flags = _expression(_math_words(coefficient[1]))
        if value != _poly_constant(6):
            raise ValueError('Incorrect coefficient')
        return {'value': value, 'flags': flags, 'constant': False, 'referential': False}
    match = re.fullmatch(r'(?:(?:i|we) )?(?:square|squared) (.+?)(?: (?:to get|and get|to obtain|giving) (.+))?', text)
    if not match:
        match = re.fullmatch(r'squaring (.+?) (?:gives|yields) (.+)', text)
    if match:
        operation = True
        text = '(' + _math_words(match[1]) + ')^2' + ('=' + _math_words(match[2]) if match[2] else '')
    else:
        match = re.fullmatch(r'(?:(?:i|we) )?(?:multiply|multiplied) (.+?) by (.+?) (?:to get|and get|to obtain|giving) (.+)', text)
        if match:
            operation = True
            text = '(' + _math_words(match[1]) + ')*(' + _math_words(match[2]) + ')=' + _math_words(match[3])
        else:
            match = re.fullmatch(r'(?:(?:i|we) )?(?:take|took) (half of .+?) (?:to get|and get|to obtain|giving) (.+)', text)
            if match:
                text = _math_words(match[1]) + '=' + _math_words(match[2])
            else:
                match = re.fullmatch(r'(?:expanding|the expansion of) (.+?) (?:gives|yields|is) (.+)', text)
                if not match:
                    match = re.fullmatch(r'(?:(?:i|we) )?expand (.+?) to get (.+)', text)
                text = match[1] + '=' + match[2] if match else text
    parts = [_expression(part) for part in _math_words(text).split('=')]
    value = parts[0][0]
    if any(other != value for other, _ in parts):
        raise ValueError('Contradictory arithmetic identity')
    flags = set().union(*(flags for _, flags in parts))
    if (value == (9, 6, 1) and 'binomial' in flags and len(parts) > 1
            and any('binomial' not in part_flags for _, part_flags in parts)):
        flags.add('demonstrated')
    elif (value == _poly_constant(9) and 'square' in flags
          and (constant or operation or (len(parts) > 1 and any('square' not in f for _, f in parts)))):
        flags.add('demonstrated')
    elif value == _poly_constant(3) and ('half' in flags or constant):
        pass
    elif value == _poly_constant(9) and (constant or len(parts) == 1):
        pass
    else:
        raise ValueError('Claim is outside this item substep')
    return {'value': value, 'flags': flags, 'constant': constant, 'referential': referential}


def _evidence(text):
    """Require every clause to be understood, true, and relevant to this item.

    The closed grammar deliberately rejects quotation, negation, unknown prose,
    unsupported pronouns, contradictory equations, and other methods it cannot
    verify. It does not treat a matching fragment inside other text as evidence.
    """
    if len(text) > 600 or re.search(r'["“”‘’]', text):
        return None
    separator = re.compile(r'\.(?!\d)|[;,]|\b(?:because|since|so|therefore|thus|then|and(?!\s+(?:get|obtain)\b))\b', re.I)
    clauses, previous, start = [], None, 0
    spans = [(match.start(), match.end(), match.group()) for match in separator.finditer(text)]
    spans.append((len(text), len(text), ''))
    try:
        for end, next_start, delimiter in spans:
            source = text[start:end].strip()
            if source:
                left = start + len(text[start:end]) - len(text[start:end].lstrip())
                right = end - len(text[start:end]) + len(text[start:end].rstrip())
                if delimiter == '.':
                    right = end + 1
                parsed = _clause(source, previous)
                parsed.update(start=left, end=right)
                clauses.append(parsed)
                previous = parsed
            start = next_start
        if not clauses or len(clauses) > 8:
            return None
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
        return None
    demonstrates = [clause for clause in clauses if 'demonstrated' in clause['flags']]
    wrong_constants = [clause for clause in clauses if clause['constant'] and clause['value'] == _poly_constant(3)]
    halves = [clause for clause in clauses if 'half' in clause['flags'] and clause['value'] == _poly_constant(3)]
    nines = [clause for clause in clauses if clause['value'] == _poly_constant(9)]
    if wrong_constants and nines:
        return None
    if demonstrates:
        candidates = []
        for clause in demonstrates:
            index = clauses.index(clause)
            left = clauses[index - 1]['start'] if clause['referential'] else clause['start']
            candidates.append(text[left:clause['end']])
        return 9, min(candidates, key=len), 'exact_square_or_binomial_identity'
    if wrong_constants and halves:
        candidates = [text[min(wrong['start'], half['start']):max(wrong['end'], half['end'])]
                      for wrong in wrong_constants for half in halves]
        return 3, min(candidates, key=len), 'explicit_unsquared_half_coefficient'
    return None


def observation_for(question, attempt, result):
    """Attribute only a bound frozen submission; return None outside the pilot.

    The HTTP caller must first load this question from the installed bank and
    validate its frozen turn. A result must carry that same revision ID, question
    ID, and final answer. Browser freshness checks are still needed before local
    storage: this pure function cannot know that a draft changed during a call.
    Rejudging a revision produces the same observation rather than new evidence.
    """
    if not _mapped(question) or not isinstance(attempt, dict) or not isinstance(result, dict):
        return None
    turn = attempt.get('turn')
    if not isinstance(turn, dict):
        return None
    revision = turn.get('revisionId')
    if not isinstance(revision, str) or not revision or len(revision) > 200:
        return None
    answer, thoughts = attempt.get('answer'), attempt.get('thoughts', '')
    if not isinstance(answer, str) or not isinstance(thoughts, str):
        return None
    if (attempt.get('questionId') != question['ID']
            or attempt.get('bank', question['Bank']) != question['Bank']
            or result.get('questionId') != question['ID']
            or result.get('revisionId') != revision
            or result.get('answer') != answer.strip()):
        return None
    answer_category = exact_answer_category(question, answer)
    if result.get('answerCategory') != (answer_category or 'cannot_judge'):
        return None

    status, quote = 'unobserved', ''
    reason = 'unsupported_or_ambiguous_reasoning' if thoughts.strip() else 'blank_reasoning'
    evidence = _evidence(thoughts)
    if evidence:
        expected, supporting_quote, supported_reason = evidence
        try:
            consistent = numeric_value(answer) == expected
        except (ValueError, ZeroDivisionError):
            consistent = False
        if consistent:
            status = 'demonstrated' if expected == 9 else 'needs_review'
            quote, reason = supporting_quote, supported_reason
            # A whole-reasoning "partial" or "cannot_judge" does not deny a
            # verified substep. An explicit opposite verdict is preserved as an
            # unresolved disagreement rather than selecting either source.
            if ((status == 'demonstrated' and result.get('category') == 'wrong')
                    or (status == 'needs_review' and result.get('category') == 'correct')):
                status, quote, reason = 'unobserved', '', 'assessment_disagreement'
        else:
            reason = 'answer_reasoning_conflict'

    assistance = turn.get('assistance', 'unknown')
    if not isinstance(assistance, str) or assistance not in ASSISTANCE:
        assistance = 'unknown'
    action = turn.get('action')
    if action not in ('submit', 'revise'):
        action = 'unknown'
    return {'bank': question['Bank'], 'questionId': question['ID'], 'revisionId': revision,
            'topicId': 'cnm_221', 'topicLabel': 'Completing the Square',
            'criterionId': CRITERION_ID, 'criterion': CRITERION,
            'sourceCriterionIndex': 0, 'sourceCriterionText': SOURCE_CRITERION_TEXT,
            'graphRevision': GRAPH_REVISION, 'mappingVersion': MAPPING_VERSION,
            'mappingQuality': 'source_checked_shadow', 'scope': 'item_substep',
            'status': status, 'assistance': assistance, 'action': action,
            'assistanceSource': 'reported_item_history', 'quote': quote,
            'answerCategory': answer_category or 'cannot_judge',
            'judgmentSource': 'deterministic_bounded_math_parser',
            'observationReason': reason, 'shadow': True}
