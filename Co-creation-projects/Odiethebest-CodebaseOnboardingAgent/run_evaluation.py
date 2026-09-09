"""Execute notebook code in order, always skipping the paid Agent demo.

Run from this directory: python run_evaluation.py [--check-reference]
The notebook file remains free of outputs; report goes to results/h1_report.json.
"""
import argparse
import json
import math
import os
from pathlib import Path


def compare(actual, expected, path='report'):
    if isinstance(expected, dict):
        if actual.keys() != expected.keys():
            raise AssertionError(f'{path}: keys differ')
        for key in expected:
            compare(actual[key], expected[key], f'{path}.{key}')
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            raise AssertionError(f'{path}: length differs')
        for i, (a, e) in enumerate(zip(actual, expected)):
            compare(a, e, f'{path}[{i}]')
    elif isinstance(expected, float):
        if not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-6):
            raise AssertionError(f'{path}: {actual} != {expected}')
    elif actual != expected:
        raise AssertionError(f'{path}: {actual} != {expected}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-reference', action='store_true')
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    os.chdir(base)
    os.environ['RUN_AGENT_DEMO'] = '0'
    os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
    from IPython.display import display
    notebook = json.loads((base / 'main.ipynb').read_text(encoding='utf-8'))
    scope = {'display': display, '__name__': '__main__'}
    for i, cell in enumerate(notebook['cells']):
        if cell['cell_type'] == 'code':
            exec(compile(''.join(cell['source']), f'main.ipynb:cell_{i}', 'exec'), scope)
    if args.check_reference:
        actual = json.loads((base / 'results/h1_report.json').read_text())
        expected = json.loads((base / 'reference/h1_report.json').read_text())
        # Environment metadata is reported, not required to be identical.
        for key in ('protocol', 'questions_sha256', 'embed_model', 'embed_revision',
                    'evaluation_sha256', 'code_cells_sha256'):
            compare(actual['provenance'][key], expected['provenance'][key], key)
        for key in expected.keys() - {'provenance'}:
            compare(actual[key], expected[key], key)
        print('Reference matched: scores within 1e-6; rankings and verdict identical.')


if __name__ == '__main__':
    main()
