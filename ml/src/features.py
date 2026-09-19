"""Explainable AST features; no rule reports, names, comments or category inputs."""
from .data import digest

SCHEMA = 'uec-ast-v1'
FEATURE_NAMES = (
    'standalone_expression', 'assigned_result', 'later_result_references',
    'guard_ancestor', 'condition_ancestor', 'unary_ancestor',
    'delegatecall', 'staticcall', 'value_option', 'argument_count',
    'function_statement_count',
)


class UnsupportedFeatures(ValueError):
    pass


def walk(node, parents=()):
    if isinstance(node, dict):
        if 'nodeType' in node:
            yield node, parents
            parents = (*parents, node)
        for value in node.values():
            yield from walk(value, parents)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value, parents)


def type_id(node):
    return node.get('typeDescriptions', {}).get('typeIdentifier', '')


def operation(node):
    if node.get('nodeType') != 'FunctionCall':
        return None
    typed = type_id(node.get('expression', {}))
    for prefix, name in [('t_function_baredelegatecall_', 'delegatecall'),
                         ('t_function_barestaticcall_', 'staticcall'),
                         ('t_function_barecall_', 'call')]:
        if typed.startswith(prefix):
            return name
    return None


def span(node, source):
    try:
        start, length, file_id = map(int, node['src'].split(':'))
    except (KeyError, ValueError):
        raise UnsupportedFeatures('Missing compiler source span') from None
    data = source.encode()
    if file_id != 0 or start < 0 or length < 1 or start + length > len(data):
        raise UnsupportedFeatures('Source span outside the single input file')
    return {'offset': start, 'length': length,
            'line': data[:start].count(b'\n')+1,
            'endLine': data[:start+length].count(b'\n')+1}


def extract(ast, source):
    """Same operation records for notebook, tests and potential inference callers.

    Syntactic feature coverage is not a claim that the operation is reachable.
    Unsupported operations are emitted explicitly, not silently dropped.
    """
    if not isinstance(ast, dict) or ast.get('nodeType') != 'SourceUnit':
        raise UnsupportedFeatures('Expected a typed compiler SourceUnit')
    records = []
    for call, parents in walk(ast):
        name = operation(call)
        if name is None:
            continue
        location = span(call, source)
        record = {'id': f'{digest(source.encode())[:16]}:{location["offset"]}',
                  'operation': name, 'span': location, 'schema': SCHEMA}
        functions = [n for n in parents if n['nodeType'] == 'FunctionDefinition']
        if not functions:
            record.update(status='unsupported', reason='Call outside a function')
            records.append(record)
            continue
        function = functions[-1]
        record['function'] = function.get('name') or '<fallback>'
        nodes = list(walk(function))
        if function.get('modifiers') or any(n['nodeType'] in {'ForStatement', 'WhileStatement', 'DoWhileStatement', 'InlineAssembly'} for n, _ in nodes):
            record.update(status='unsupported', reason='Function has modifiers, loops or assembly')
            records.append(record)
            continue
        parent = parents[-1]
        assigned = parent['nodeType'] == 'VariableDeclarationStatement' and parent.get('initialValue', {}).get('id') == call['id']
        refs = set()
        if assigned:
            declarations = [n for n in parent.get('declarations', []) if n]
            # Only the first tuple component is success, not returndata.
            if declarations and type_id(declarations[0]) == 't_bool':
                refs.add(declarations[0]['id'])
            else:
                record.update(status='unsupported', reason='Unresolved success binding')
                records.append(record)
                continue
        elif parent['nodeType'] in {'Assignment', 'Return'}:
            record.update(status='unsupported', reason='Assignment/return data flow outside feature domain')
            records.append(record)
            continue
        later_refs = sum(n['nodeType'] == 'Identifier' and n.get('referencedDeclaration') in refs
                         and int(n['src'].split(':')[0]) > location['offset'] for n, _ in nodes)
        guards = sum(n['nodeType'] == 'FunctionCall' and type_id(n.get('expression', {})).startswith(('t_function_require_', 't_function_assert_')) for n in parents)
        conditions = sum(n['nodeType'] == 'IfStatement' and any(c.get('id') == call['id'] for c, _ in walk(n.get('condition'))) for n in parents)
        chain = [n for n, _ in walk(call.get('expression', {}))]
        values = [
            int(parent['nodeType'] == 'ExpressionStatement'), int(assigned), later_refs,
            guards, conditions, sum(n['nodeType'] == 'UnaryOperation' for n in parents),
            int(name == 'delegatecall'), int(name == 'staticcall'),
            int(any(n.get('memberName') == 'value' or 'value' in n.get('names', []) for n in chain)),
            len(call.get('arguments', [])),
            sum(n['nodeType'].endswith('Statement') for n, _ in nodes),
        ]
        record.update(status='supported', features=dict(zip(FEATURE_NAMES, values)))
        records.append(record)
    return records


def vector(record):
    if record.get('schema') != SCHEMA or record.get('status') != 'supported':
        raise UnsupportedFeatures('Unsupported operation/schema')
    if set(record['features']) != set(FEATURE_NAMES):
        raise UnsupportedFeatures('Feature schema mismatch')
    return [record['features'][key] for key in FEATURE_NAMES]
