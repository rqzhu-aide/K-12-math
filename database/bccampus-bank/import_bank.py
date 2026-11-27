"""Rebuild the selected BCcampus v3 questions from the pinned publisher EPUBs."""

import argparse
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from math import gcd, lcm
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile


BANK = 'bccampus'
TITLE = 'Adult Literacy Fundamental Mathematics'
LICENSE_URL = 'https://creativecommons.org/licenses/by/4.0/'
SOLUTION_LICENSE_URL = 'https://creativecommons.org/licenses/by-nc/4.0/'
AUTHORS = {
    4: 'Katherine Arendt, Mercedes de la Nuez, and Liz Girard',
    5: 'Liz Girard, Wendy Tagami, and Leanne Caillier-Smith',
}
EDITION = {
    4: ('2.05', 'e0eba7105326a64d04c9f50725605d7d0c8b3d071879caf9832b083ec477ea2c'),
    5: ('2.02', 'f21e9c12c716cb5a480c5749206a8b9bd9506f232b522f66ed3952c7edb87be2'),
}
CHAPTERS = {
    (4, '01b'): ('002-reading-writing-decimals', 'Reading & Writing Decimals'),
    (4, '01c'): ('003-comparing-decimals', 'Comparing Decimals'),
    (5, '04a'): ('010-adding-common-fractions', 'Adding Common Fractions'),
    (5, '04b'): ('011-subtracting-common-fractions', 'Subtracting Common Fractions'),
}
UNIT_TITLES = {4: 'Working with Decimals', 5: 'Adding & Subtracting Common Fractions'}
PLACES = ['ones', 'tenths', 'hundredths', 'thousandths', 'ten-thousandths']
FRACTION = r'(\d*)\\(?:d?frac|tfrac)\s*\{(\d+)\}\s*\{(\d+)\}'
NODE_GRADES = {
    'cnm_p118': 4, 'cnm_p119': 4, 'cnm_p159': 5, 'cnm_p168': 5,
    'cnm_p170': 5, 'cnm_p172': 5, 'cnm_p173': 5,
}


def require(condition, issue):
    if not condition:
        raise ValueError(issue)


def text(element):
    return ' '.join(''.join(element.itertext()).split())


def math_text(element):
    return ' '.join(image.get('alt', '') for image in element.iter('img')
                    if 'latex' in image.get('class', '').split())


def reproduction(element):
    return {'text': text(element), 'latex': math_text(element)}


def chapter(archive, book, section):
    name, _ = CHAPTERS[book, section]
    root = ET.fromstring(archive.read(f'EPUB/chapter-{name}.xhtml'))
    for element in root.iter():
        element.tag = element.tag.split('}')[-1]
    return root


def exercise(root, number):
    def tagged(class_name):
        return (element for element in root.iter() if class_name in element.get('class', '').split())

    label = f'Exercise {number}'
    box, = [box for box in tagged('textbox') if any(
        'textbox__title' in element.get('class', '').split()
        and text(element).split(':', 1)[0] == label for element in box.iter())]
    body, = [element for element in box.iter() if element.get('class') == 'textbox__content']
    boundary = next(i for i, element in enumerate(body) if element.tag == 'p'
                    and re.match(r'Answers?\b', text(element)))
    return body[:boundary], body[boundary + 1:]


def list_items(elements):
    return {i: item for group in elements if group.tag == 'ol'
            for i, item in enumerate(group, int(group.get('start', '1')))}


def table_rows(elements):
    table, = [element for element in elements if element.tag == 'table']
    return {text(row[0]).rstrip(')'): row for row in table.iter('tr') if len(row)}


def read_fractions(element):
    return [(int(whole or '0'), int(n), int(d))
            for whole, n, d in re.findall(FRACTION, math_text(element))]


def terms(n, d, whole=0):
    return (str(whole) if whole else '') + rf'\frac{{{n}}}{{{d}}}'


def math(value):
    return rf'\({value}\)'


def mixed(n, d):
    whole, remainder = divmod(n, d)
    return math(terms(remainder, d, whole)) if remainder else math(str(whole))


def choice(correct, alternatives, position):
    options = list(alternatives)
    index = position % (len(options) + 1)
    options.insert(index, correct)
    require(len(options) == len(set(options)), f'Duplicate answer choices: {options}')
    choices = [{'id': chr(65 + i), 'content': value} for i, value in enumerate(options)]
    return {'type': 'choice', 'accepted': [choices[index]['id']]}, choices


def numeric(answer, form=None):
    return {'type': 'numeric', 'accepted': [str(answer)], **({'form': form} if form else {})}


class Selection:
    def __init__(self):
        self.questions = {}
        self.sources = {}

    def add(self, location, family, nodes, prompt, answer, title, solution,
            original, original_key, change, choices=None, answer_example=None, method_nodes=None):
        book, section, exercise_no, part = location
        chapter_file, chapter_title = CHAPTERS[book, section]
        slug = chapter_file.split('-', 1)[1]
        page = f'https://opentextbc.ca/alfm{book}/chapter/{slug}/'
        author = AUTHORS[book]
        suffix = f'{part:02}' if isinstance(part, int) else part
        source_id = f'b{book:02}_u{section}_e{exercise_no:02}_q{suffix}'
        question_id = f'{BANK}__{source_id}'
        method_id = f'{source_id}:ailleoworked'
        label_part = chr(96 + part) if isinstance(part, int) else part
        part_number = ord(label_part) - 96
        locator = (f'Book {book}, Unit {int(section[:2])}, Topic {section[2].upper()}, '
                   f'Exercise {exercise_no}({label_part})')
        credit = {'sourceURL': page, 'revision': f'2nd edition, EPUB revision {EDITION[book][0]}',
                  'license': 'CC BY 4.0', 'licenseURL': LICENSE_URL}
        author_credit = f'© 2023 {author}. {TITLE}, Book {book}, 2nd edition. BCcampus.'
        if method_nodes is None:
            method_nodes = nodes
        topic_id = f'bccampus_b{book:02}_u{section}'
        classification = {'topicIds': [topic_id], 'level': f'Book {book}', 'unit': UNIT_TITLES[book]}
        if nodes:
            classification['grade'] = min(NODE_GRADES[node] for node in nodes)
        require(question_id not in self.questions, f'Duplicate source locator: {locator}')
        self.questions[question_id] = {
            'schemaVersion': '3.0', 'bank': BANK, 'language': 'en', 'id': question_id,
            'question': {'prompt': prompt, **({'choices': choices} if choices else {}),
                         **({'answerExample': answer_example} if answer_example else {})},
            'answer': answer, 'assessedNodeIds': nodes,
            'solutions': [{'id': 'ailleoworked', 'title': title, 'explanation': solution,
                           **({'directNodeIds': method_nodes} if method_nodes else {}), 'sourceRef': method_id}],
            'classification': classification, 'sourceRef': source_id,
        }
        self.sources[source_id] = {
            **credit, 'kind': 'exercise', 'label': locator, 'attribution': author_credit,
            'position': {'number': exercise_no * 100 + part_number},
            'topicLabels': {topic_id: chapter_title},
            'meta': {'locator': locator, 'familyId': f'bccampus:{family}', 'changes': change,
                     'licenseNoticeURL': f'https://opentextbc.ca/alfm{book}/',
                     'originalPrompt': original, 'originalKey': original_key,
                     'officialKey': {'sourceURL': page, 'locator': f'Answers to Exercise {exercise_no}({label_part})'}},
        }
        self.sources[method_id] = {
            **credit, 'license': 'CC BY-NC 4.0', 'licenseURL': SOLUTION_LICENSE_URL,
            'kind': 'solution', 'label': 'Ailleo worked solution', 'attribution': 'Ailleo',
            'meta': {'locator': locator,
                     'changes': ('Ailleo wrote the explanation and checked the keyed result against the publisher. '
                                 'Ailleo calculated any extra steps required by the adaptation.'),
                     'officialKey': {'sourceURL': page, 'attribution': author_credit,
                                     'license': 'CC BY 4.0', 'licenseURL': LICENSE_URL}},
            'provenance': {'source': 'Ailleo worked solution', 'officialSolution': False,
                           'reviewStatus': 'Worked result checked against the publisher answer key.'},
        }


def decimal_choices(selection, root):
    for number, last in [(3, 5), (4, 5), (6, 5), (8, 6)]:
        body, answers = exercise(root, number)
        prompts, keys = list_items(body), list_items(answers)
        for part in range(3, last + 1):
            source, key = prompts[part], keys[part]
            raw, = re.findall(r'0\.\d+', text(source))
            require(not math_text(source) and text(source).replace(raw, '').strip(' =') == '', raw)
            digits = raw.split('.')[1]
            n, places = int(digits), len(digits)
            d = 10 ** places
            words = text(key).lstrip(', ')
            require(read_fractions(key) == [(0, n, d)], f'Incorrect source key for {raw}')
            require(words.endswith(PLACES[places]) or words == 'one tenth', f'Place wording for {raw}')
            # The distractors move the same count to a different place-value unit.
            count = words.rsplit(' ', 1)[0]
            alternative_places = [i for i in range(1, 5) if i != places]
            alternatives = [math(terms(n, 10 ** i)) + f' ({count} {PLACES[i].removesuffix("s") if n == 1 else PLACES[i]})'
                            for i in alternative_places]
            value = math(terms(n, d))
            answer, choices = choice(f'{value} ({words})', alternatives, part + number)
            explanation = (f'The decimal {math(raw)} has {places} decimal {"place" if places == 1 else "places"}. '
                           f'Its last digit is in the {PLACES[places].removesuffix("s")} place. '
                           f'The digits after the decimal point give {words}, or {value}.')
            nodes = ['cnm_p118', 'cnm_p170'] if places <= 2 else []
            selection.add((4, '01b', number, part), 'decimal-fraction-and-words', nodes,
                          f'Which fraction and words match {math(raw)} using the place of the last digit?',
                          answer, 'Read the last decimal place', explanation,
                          {'directions': text(body[0]), **reproduction(source)}, reproduction(key),
                          'Turned a fill-in exercise into a choice question with new distractors.', choices)


def fraction_to_decimal(selection, root):
    for number, last in [(5, 10), (7, 8), (9, 6)]:
        body, answers = exercise(root, number)
        prompts, keys = list_items(body), list_items(answers)
        for part in range(3, last + 1):
            source, key = prompts[part], keys[part]
            (_, n, d), = read_fractions(source)
            raw = text(key)
            require(not text(source) and Fraction(raw) == Fraction(n, d), f'Incorrect source key for {n}/{d}')
            places = len(str(d)) - 1
            frac = math(terms(n, d))
            explanation = (f'A denominator of {math(str(d))} counts {PLACES[places]}. Put the last digit '
                           f'of {math(str(n))} in the {PLACES[places].removesuffix("s")} place and fill '
                           f'any empty places on the left of that digit with zeros. '
                           f'This gives {math(raw)}.')
            nodes = ['cnm_p170'] if places <= 2 else []
            selection.add((4, '01b', number, part), 'fraction-to-decimal', nodes,
                          f'Write {frac} as a decimal.', numeric(raw, 'decimal'),
                          f'Count {PLACES[places]}', explanation,
                          {'directions': text(body[0]), **reproduction(source)}, reproduction(key),
                          'Presented one subpart at a time and typeset the fraction as LaTeX.')


def decimal_review(selection, root):
    body, answers = exercise(root, '13')
    prompts, keys = table_rows(body), table_rows(answers)
    for part in 'cfgijl':
        source, key = prompts[part], keys[part]
        raw = text(key[1])
        whole, fractional = raw.split('.')
        (key_whole, n, d), = read_fractions(key[2])
        require((key_whole, n, d) == (int(whole), int(fractional), 10 ** len(fractional)), raw)
        words = text(key[3])
        place = PLACES[len(fractional)]
        if part in 'gj':
            require(text(source[1]) == raw, raw)
            prompt = (f'In {math(raw)}, what is the whole-number part, and how many {place} are in the '
                      'fractional part? Enter those two numbers in order, separated by a comma.')
            answer = numeric(f'{whole}, {n}', 'ordered-list')
            solution = (f'The digits to the left of the decimal point give {math(whole)}. The digits to the right '
                        f'give {math(terms(n, d))}, or {math(str(n))} {place}.')
            family, title = 'decimal-parts', 'Split at the decimal point'
            example = '2, 9'
            change = ('Turned the mixed-number and words columns into a two-number response naming the '
                      'whole-number part and the count of fractional units.')
        else:
            require(text(source[3]) == words, words)
            prompt = f'Write {words} as a decimal.'
            answer = numeric(raw, 'decimal')
            setup = (f'{whole} goes to the left of the decimal point.' if key_whole
                     else 'There are no whole units, so write 0 to the left of the decimal point.')
            solution = (f'{setup} The fractional part is {math(terms(n, d))}. Use {len(fractional)} '
                        f'decimal {"place" if len(fractional) == 1 else "places"} to write {math(raw)}.')
            family = 'mixed-decimal-from-words' if key_whole else 'decimal-from-words'
            title, example = 'Write the whole number and decimal places', None
            change = 'Asked for the decimal column of this review row as a standalone response.'
        selection.add((4, '01b', 13, part), family, ['cnm_p118'], prompt, answer, title, solution,
                      {'directions': text(body[0]), **reproduction(source)}, reproduction(key), change,
                      answer_example=example)


def decimal_comparisons(selection, root):
    for number, label, first in [(2, 'Two', 3), (3, 'Three', 1)]:
        body, answers = exercise(root, label)
        prompts, keys = list_items(body), list_items(answers)
        for part in range(first, len(keys) + 1):
            source, key = prompts[part], keys[part]
            values = re.findall(r'\d+\.\d+', text(source))
            ordered = sorted(values, key=Decimal)
            print_values = [math(value) for value in values]
            places = max(len(value.split('.')[1]) for value in values)
            trail = ' < '.join(format(Decimal(value), f'.{places}f') for value in ordered)
            if number == 2:
                a, b = values
                op = '>' if Decimal(a) > Decimal(b) else '<'
                require(op == text(key), f'Incorrect comparison key for {a}, {b}')
                prompt = f'Which comparison of {print_values[0]} and {print_values[1]} is true?'
                choices = [{'id': 'A', 'content': math(f'{a} < {b}')},
                           {'id': 'B', 'content': math(f'{a} > {b}')}]
                answer = {'type': 'choice', 'accepted': ['A' if op == '<' else 'B']}
                family, result = 'larger-decimal', math(f'{a} {op} {b}')
                change = 'Used a choice between the two comparison statements.'
            else:
                require(ordered[0] == text(key), f'Incorrect minimum key for {values}')
                prompt = f'Which decimal is smallest among {", ".join(print_values)}?'
                choices = [{'id': chr(65 + i), 'content': value} for i, value in enumerate(print_values)]
                answer = {'type': 'choice', 'accepted': [choices[values.index(ordered[0])]['id']]}
                family, result = 'smallest-decimal', f'{math(ordered[0])} is smallest'
                change = 'Presented each group as a choice question.'
            solution = (f'Align the decimal places by adding trailing zeros where needed. The order is '
                        f'{math(trail)}, so {result}.')
            selection.add((4, '01c', number, part), family, ['cnm_p119'], prompt, answer,
                          'Compare matching decimal places', solution,
                          {'directions': text(body[0]), **reproduction(source)}, reproduction(key), change, choices)


def least_multiple(a, b, result):
    small, large = sorted((a, b))
    if large % small == 0:
        return (f'{math(str(large))} is a multiple of {math(str(small))}, so the least common multiple '
                f'is {math(str(result))}.')
    candidates = ', '.join(str(i) for i in range(large, result + 1, large))
    return (f'List the multiples of {math(str(large))} in order: {math(candidates)}. '
            f'The first one that is also a multiple of {math(str(small))} is {math(str(result))}.')


def common_denominators(selection, root):
    body, answers = exercise(root, 10)
    keys = list_items(answers)
    for part, source in list_items(body).items():
        if part == 7:  # The same denominator pair appears in Exercise 11(e).
            continue
        a, b = map(int, text(source).split(','))
        key = keys[part]
        result = lcm(a, b)
        require(result == int(text(key)), f'Incorrect LCM source key for {a}, {b}')
        selection.add((5, '04a', 10, part), 'least-common-multiple', ['cnm_p159'],
                      f'Find the least common multiple of {math(str(a))} and {math(str(b))}.', numeric(result),
                      'Find the first shared multiple', least_multiple(a, b, result),
                      {'directions': text(body[0]), **reproduction(source)}, reproduction(key),
                      'Presented one pair at a time as a standalone question.')

    body, answers = exercise(root, 11)
    rows, keys = table_rows(body), list_items(answers)
    for part in 'bcde':
        source, key = rows[part], keys[ord(part) - 96]
        (_, a, b), (_, c, d) = read_fractions(source)
        common = lcm(b, d)
        require(common == int(text(key)), f'Incorrect LCD source key for denominators {b}, {d}')
        require(not text(source[-1]), f'Part {part} is already worked.')
        left, right = a * (common // b), c * (common // d)
        prompt = (f'Find the least common denominator of {math(terms(a, b))} and {math(terms(c, d))}. '
                  'Rewrite both fractions using that denominator. Enter the denominator, then the two new '
                  'numerators in the order of the original fractions. Separate the three numbers with commas.')
        explanation = (f'{least_multiple(b, d, common)} Multiply the numerator and denominator of '
                       f'{math(terms(a, b))} by {math(str(common // b))} to get {math(terms(left, common))}. '
                       f'Multiply the numerator and denominator of {math(terms(c, d))} by '
                       f'{math(str(common // d))} to get {math(terms(right, common))}.')
        selection.add((5, '04a', 11, part), 'least-denominator-and-rewrite', ['cnm_p172'],
                      prompt, numeric(f'{common}, {left}, {right}', 'ordered-list'),
                      'Find the denominator and rewrite both fractions', explanation,
                      {'directions': text(body[0]), **reproduction(source)}, reproduction(key),
                      'Added the two equivalent numerators to the original LCD exercise. The publisher key '
                      'gives the denominator. Ailleo computed and checked both numerators.',
                      answer_example='6, 3, 2', method_nodes=['cnm_p159', 'cnm_p172'])


def fraction_operations(selection, root, section, number, parts, *, simplify=False):
    body, answers = exercise(root, number)
    prompts, keys = list_items(body), list_items(answers)
    subtract = section == '04b'
    operator = ' - ' if subtract else ' + '
    task = 'difference' if subtract else 'sum'
    for part in parts:
        source, key = prompts[part], keys[part]
        original = read_fractions(source)
        require(len(original) in (2, 3) and len({d for _, _, d in original}) > 1,
                f'No unlike denominators for {section}, Exercise {number}({part})')
        require(len(read_fractions(key)) <= 1, f'Ambiguous key: {reproduction(key)}')
        target = read_fractions(key)
        expected = Fraction(target[0][1], target[0][2]) + target[0][0] if target else Fraction(text(key))
        require(not subtract or all(not w for w, _, _ in original), 'Mixed-number subtraction is outside this selection.')
        whole = sum(w for w, _, _ in original)
        d = lcm(*(d for _, _, d in original))
        expanded = [n * (d // bottom) for _, n, bottom in original]
        numerator = expanded[0] - expanded[1] if subtract else sum(expanded)
        result = Fraction(numerator, d) + whole
        require(result == expected, f'Incorrect publisher key for {section}, Exercise {number}({part})')
        display = operator.join(terms(n, d, w) for w, n, d in original)
        same_denom = operator.join(terms(n, d) for n in expanded)
        fraction_work = f'{same_denom} = {terms(numerator, d)}'
        reduced = math(terms(result.numerator, result.denominator)) if result.denominator > 1 else math(str(result))
        gcd_value = gcd(numerator, d)
        chosen = mixed(result.numerator, result.denominator)
        solution = f'The least common denominator is {math(str(d))}. '
        if whole:
            solution += (f'Add the whole-number parts to get {math(str(whole))}. '
                         f'For the fractional parts, use {math(fraction_work)}. ')
            if gcd_value > 1:
                solution += (f'Divide that fraction’s numerator and denominator by {math(str(gcd_value))} '
                             f'to get {math(terms(numerator // gcd_value, d // gcd_value))}. ')
            solution += ('Add the whole-number total '
                         f'to this fraction to get {chosen}.')
        else:
            solution += f'Rewrite each fraction with that denominator and {"subtract" if subtract else "add"}: {math(fraction_work)}.'
            if gcd_value > 1:
                solution += f' Divide the numerator and denominator by {math(str(gcd_value))} to simplify to {reduced}.'
            if chosen != reduced:
                solution += f' As a mixed number, this is {chosen}.'
        answer_example = None
        if simplify:
            prompt = (f'Find the {task} and write it as a fraction in lowest terms. Use an improper fraction '
                      'if the result is greater than 1. Enter the numerator first and the denominator second, '
                      f'separated by a comma. For example, enter 7, 4 for {math(terms(7, 4))}.\n\n{math(display)}')
            pair = f'{result.numerator}, {result.denominator}'
            answer = numeric(pair, 'ordered-list')
            answer_example = '7, 4'
            final_whole, remainder = divmod(result.numerator, result.denominator)
            if final_whole and remainder:
                conversion = math(rf'{final_whole}\times {result.denominator}+{remainder}={result.numerator}')
                solution += f' For the improper fraction, the numerator is {conversion}.'
            final_fraction = math(terms(result.numerator, result.denominator))
            solution += f' The fraction in lowest terms is {final_fraction}. Enter {pair}.'
            change = ('Used one horizontal expression and asked for the numerator and denominator of the '
                      'reduced fraction in order. Mixed-number answers in the source use improper fractions here.')
        elif target and target[0][0]:
            prompt = (f'Find the {task}. Enter a mixed number such as 2 1/3, an improper fraction, '
                      f'or an exact decimal.\n\n{math(display)}')
            answer = numeric(result)
            change = 'Used one horizontal expression and kept the published mixed-number key and its equivalent improper fraction.'
        else:
            prompt = f'Find the {task}. Enter a whole number, decimal, or fraction such as 7/4.\n\n{math(display)}'
            answer = numeric(result)
            change = 'Used one horizontal expression and score the value as a fraction or a decimal.'
        family = 'mixed-number-addition' if whole else (
            'unlike-fraction-subtraction' if subtract else f'unlike-fraction-addition-{len(original)}-terms')
        nodes = ['cnm_p173', 'cnm_p168'] if simplify else ['cnm_p173']
        method_nodes = ['cnm_p173', 'cnm_p172']
        if gcd_value > 1:
            method_nodes.append('cnm_p168')
        directions = text(body[0])
        selection.add((5, section, number, part), family, nodes, prompt, answer,
                      'Use a common denominator', solution,
                      {'directions': directions, **reproduction(source)}, reproduction(key), change,
                      answer_example=answer_example, method_nodes=method_nodes)


def rebuild(epub4, epub5):
    for book, file in [(4, epub4), (5, epub5)]:
        require(hashlib.sha256(file.read_bytes()).hexdigest() == EDITION[book][1], f'Unreviewed EPUB: {file}')
    selection = Selection()
    with ZipFile(epub4) as book4, ZipFile(epub5) as book5:
        decimals = chapter(book4, 4, '01b')
        decimal_choices(selection, decimals)
        fraction_to_decimal(selection, decimals)
        decimal_review(selection, decimals)
        decimal_comparisons(selection, chapter(book4, 4, '01c'))
        adding = chapter(book5, 5, '04a')
        common_denominators(selection, adding)
        fraction_operations(selection, adding, '04a', 12, range(3, 9), simplify=True)
        fraction_operations(selection, adding, '04a', 13, range(3, 9))
        fraction_operations(selection, adding, '04a', 14, [2, 4, 6, 7, 8])
        fraction_operations(selection, adding, '04a', 15, range(2, 7), simplify=True)
        fraction_operations(selection, chapter(book5, 5, '04b'), '04b', 2, range(3, 17), simplify=True)
    return selection


def write_bank(selection, output):
    output.mkdir(parents=True, exist_ok=True)
    questions = output / 'questions'
    questions.mkdir(exist_ok=True)
    extra = {path.stem for path in questions.glob('*.json')} - selection.questions.keys()
    require(not extra, f'Unexpected existing question records: {sorted(extra)}')

    def write_json(path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

    write_json(output / 'bank.json', {
        'id': BANK, 'label': 'BCcampus Fundamental Mathematics',
        'attribution': f'{AUTHORS[4]} (Book 4); {AUTHORS[5]} (Book 5). BCcampus.',
        'license': 'CC BY 4.0', 'licenseURL': LICENSE_URL,
        'sourceURL': 'https://opentextbc.ca/alfm4/',
    })
    write_json(output / 'source-index.json', {
        'schemaVersion': '3.0', 'bank': BANK, 'sources': dict(sorted(selection.sources.items())),
    })
    for qid, record in sorted(selection.questions.items()):
        write_json(questions / f'{qid}.json', record)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('book4', type=Path)
    parser.add_argument('book5', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    selection = rebuild(args.book4, args.book5)
    write_bank(selection, args.output)
    print(f'Wrote {len(selection.questions)} questions.')
