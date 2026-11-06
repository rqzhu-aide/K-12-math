"""Validate and install a question-bank-template bank for the practice UI."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from question_banks import BankError, ROOT, browser_bank, custom_root, read_bank, valid_bank_id


def remove_generated(path, base):
    resolved = path.resolve()
    if resolved == base or not resolved.is_relative_to(base):
        raise BankError('Generated bank cleanup must stay inside custom-banks.')
    shutil.rmtree(path)


def import_bank(source, root=ROOT, replace=False, check=False):
    manifest, records, figures = read_bank(source, graph_root=root)
    result = {'id': manifest['id'], 'questions': len(records), 'figures': len(figures)}
    if check:
        return result
    base = custom_root(Path(root))
    target = base / manifest['id']
    if target.exists() and not replace:
        raise BankError(f'{manifest["id"]} is already installed. Use --replace to update it, keeping stable question IDs for notebook history.')
    if target.resolve() != target:
        raise BankError('The installed bank folder must not be a link to another folder.')
    # Read and validate every installed bank before changing any installed data.
    banks = []
    if base.exists():
        for existing in sorted(base.iterdir()):
            if existing != target and valid_bank_id(existing.name) and existing.is_dir():
                if not existing.resolve().is_relative_to(base):
                    raise BankError('Installed banks must stay inside custom-banks.')
                old_manifest, old_records, _ = read_bank(existing, graph_root=root)
                if old_manifest['id'] != existing.name:
                    raise BankError(f'{existing.name}: folder name must match bank.json id.')
                banks.append(browser_bank(old_manifest, old_records))
    banks.append(browser_bank(manifest, records))
    banks.sort(key=lambda bank: bank['id'])
    bundle = 'window.CUSTOM_MATH_BANKS = ' + json.dumps(banks, ensure_ascii=True, separators=(',', ':')) + ';\n'
    base.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.import-', dir=base))
    backup = None
    installed = False
    try:
        (stage / 'questions').mkdir()
        (stage / 'figures').mkdir()
        (stage / 'bank.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for question in records:
            (stage / 'questions' / (question['ID'] + '.json')).write_text(json.dumps(question, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for relative, data in figures.items():
            (stage / relative).write_bytes(data)
        # Prepare the complete bundle before replacing the installed bank.
        pending = stage / 'banks.js'
        pending.write_text(bundle, encoding='utf-8')
        if target.exists():
            backup = Path(tempfile.mkdtemp(prefix='.previous-', dir=base))
            backup.rmdir()
            os.replace(target, backup)
        try:
            os.replace(stage, target)
            installed = True
            os.replace(target / 'banks.js', base / 'banks.js')
        except OSError:
            if installed:
                remove_generated(target, base)
            if backup is not None:
                os.replace(backup, target)
                backup = None
            raise
        if backup is not None:
            remove_generated(backup, base)
    finally:
        if stage.exists():
            remove_generated(stage, base)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Folder containing bank.json, questions/ and optional figures/.')
    parser.add_argument('--check', action='store_true', help='Validate only, without installing or changing files.')
    parser.add_argument('--replace', action='store_true', help='Replace an installed bank with this version.')
    args = parser.parse_args()
    try:
        result = import_bank(args.source, replace=args.replace, check=args.check)
    except (BankError, OSError) as exc:
        parser.exit(1, f'Bank not imported: {exc}\n')
    verb = 'Validated' if args.check else 'Installed'
    print(f'{verb} {result["id"]}: {result["questions"]} questions, {result["figures"]} figures.')
    if not args.check:
        print('Reload Math Practice and select the bank. Imported content stays in ignored custom-banks/.')


if __name__ == '__main__':
    main()
