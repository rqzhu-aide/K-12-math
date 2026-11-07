"""Compare explicit answer formats without running imported code or symbolic guesses."""
from fractions import Fraction
import re
import unicodedata

NUMBER = re.compile(r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:e([+-]?[0-9]+))?$', re.I)
DECIMAL = re.compile(r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$')


def numeric_value(text):
    parts = text.strip().split('/')
    if len(parts) > 2:
        raise ValueError('Unsupported number')
    for part in parts:
        match = NUMBER.fullmatch(part.strip())
        if not match or abs(int(match.group(1) or 0)) > 308:
            raise ValueError('Unsupported number')
    return Fraction(parts[0].strip()) / (Fraction(parts[1].strip()) if len(parts) == 2 else 1)


def answer_category(correct):
    return 'cannot_judge' if correct is None else 'correct' if correct else 'wrong'


def normalized(value):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value).replace('−', '-')).casefold()


def form_text(value):
    value = normalized(value)
    for left, right in (('\\(', '\\)'), ('$', '$')):
        if value.startswith(left) and value.endswith(right):
            return value[len(left):-len(right)]
    return value


def numeric_list(value):
    return [numeric_value(x) for x in unicodedata.normalize('NFKC', value).replace('−', '-').split(',')]


def choice_list(value):
    """A complete multi-select submission, including its bounded revision history."""
    return (isinstance(value, list) and 0 < len(value) <= 2000
            and all(isinstance(item, str) and item.strip() for item in value)
            and sum(map(len, value)) <= 2000 and len(set(value)) == len(value))


def answer_form_feedback(question, answer):
    """Explain an explicit form requirement without asserting value correctness."""
    form = question.get('Answer Form')
    if not form or not isinstance(answer, str):
        return ''
    text = form_text(answer)
    if form == 'decimal' and not DECIMAL.fullmatch(text):
        return 'Write your final answer as a decimal numeral rather than a fraction or expression.'
    if form == 'standard-monomial' and not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?)?[a-z]+', text):
        return 'Write the numerical coefficient first and omit multiplication signs between the coefficient and letters.'
    if form == 'ordered-list':
        try:
            actual = numeric_list(text.strip('()'))
            targets = [numeric_list(value) for value in question.get('Accepted Responses', [question['Correct Answer']])]
            if actual not in targets and any(sorted(actual) == sorted(target) for target in targets):
                return 'Write the values in the order requested in the problem.'
        except (ValueError, ZeroDivisionError):
            pass
    return ''


def enforce_answer_form(question, answer, category):
    return 'partial' if category == 'correct' and answer_form_feedback(question, answer) else category


def not_graded_result(question, answer):
    return {'questionId': question['ID'], 'answer': answer, 'answerCorrect': None,
            'answerCategory': 'not_graded', 'exactAnswerCategory': 'not_graded', 'category': 'not_graded',
            'gradingStatus': question['GradingStatus'],
            'gradingNote': question.get('GradingNote', 'This problem is disputed and is available for study without grading.'),
            'modelUsed': False, 'decisionRequests': 0}


def confirmed_grading_notice(answer_check):
    """Project only adjudicated central outcomes, never first-pass uncertainty."""
    status = answer_check.get('status') if isinstance(answer_check, dict) else None
    notes = {
        'confirmed_conflict': 'A review found a mathematical inconsistency in this question or its answer key. You can study it without grading.',
        'confirmed_ambiguous': 'This question does not identify one unambiguous answer. You can study it without grading.',
    }
    if status not in notes:
        return None
    return {'gradingStatus': 'disputed', 'gradingNote': notes[status]}


def effective_grading_question(question, root=None):
    """Return a temporary grading view after binding the unchanged source record.

    Only the central reader can authorize a new dispute. A portable stub or an
    unreviewed disagreement cannot do so. The returned view is never persisted.
    """
    if question.get('GradingStatus') == 'disputed':
        return question
    from knowledge_graph import context_for_question
    context = context_for_question(question, **({'root': root} if root is not None else {}))
    if context.get('binding', {}).get('status') != 'current':
        return question
    notice = confirmed_grading_notice(context.get('answerCheck'))
    if notice is None:
        return question
    return {**question, 'GradingStatus': notice['gradingStatus'], 'GradingNote': notice['gradingNote']}


def exact_answer_category(question, answer):
    """Return a proven category, or None when explicit formats cannot decide."""
    if question.get('GradingStatus') == 'disputed':
        return 'not_graded'
    kind = question.get('ResponseType', 'choice')
    expected = question['Correct Answer']
    if kind == 'multiSelect':
        if not choice_list(answer) or not set(answer).issubset(question['Choices']):
            return 'wrong'
        selected = set(answer)
        accepted = [set(response) for response in question['Accepted Responses']]
        if selected in accepted:
            return 'correct'
        return 'partial' if any(selected < response for response in accepted) else 'wrong'
    if normalized(answer) in {normalized(x) for x in question.get('Rejected Answers', [])}:
        return 'wrong'
    if kind == 'choice':
        return 'correct' if answer in question.get('Accepted Responses', [expected]) else 'wrong'
    if kind == 'self':
        return None
    if kind == 'short':
        accepted = question.get('Accepted Responses', [expected, *question.get('Accepted Answers', [])])
        if normalized(answer) in {normalized(x) for x in accepted}:
            return enforce_answer_form(question, answer, 'correct')
        if question.get('Answer Form') == 'standard-monomial':
            # This is a notation check, not general symbolic simplification.
            without_signs = re.sub(r'\*|·|×|\\times|\\cdot', '', form_text(answer))
            if without_signs in {form_text(x) for x in accepted}:
                return 'partial' if answer_form_feedback(question, answer) else 'correct'
        return None
    if kind != 'numeric':
        return None
    results = {_numeric_category(question, answer, target)
               for target in question.get('Accepted Responses', [expected])}
    return next(category for category in ('correct', 'partial', None, 'wrong') if category in results)


def _numeric_category(question, answer, expected):
    try:
        actual, target = numeric_list(answer), numeric_list(expected)
        close = lambda a, b: abs(a-b) <= Fraction(1, 10**9)
        if question.get('Unordered Answers') or question.get('Answer Form') == 'ordered-list':
            # Match occurrences once, not just membership: 3,3 cannot replace 3,-3.
            remaining = sorted(target)
            for value in sorted(actual):
                index = next((i for i, item in enumerate(remaining) if close(value, item)), None)
                if index is None:
                    return 'wrong'
                remaining.pop(index)
            in_order = len(actual) == len(target) and all(close(a, b) for a, b in zip(actual, target))
            return 'partial' if remaining or (question.get('Answer Form') == 'ordered-list' and not in_order) else enforce_answer_form(question, answer, 'correct')
        if len(actual) < len(target):
            return 'partial' if all(close(a, b) for a, b in zip(actual, target)) else None
        if len(actual) == len(target) and all(close(a, b) for a, b in zip(actual, target)):
            return enforce_answer_form(question, answer, 'correct')
        return 'wrong'
    except (ValueError, ZeroDivisionError):
        return None


def answer_correct(question, answer):
    """Compatibility for callers that only support true/false/unresolved."""
    return {'correct': True, 'wrong': False}.get(exact_answer_category(question, answer))
