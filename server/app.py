import sqlite3
from collections import Counter
from flask import Flask, request, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

class Node:
    def __init__(self, type, left=None, right=None, value=None):
        self.type = type
        self.left = left
        self.right = right
        self.value = value

    def __repr__(self):
        if self.type == 'operand':
            return f'Operand({self.value})'
        return f'Operator({self.type}, {self.left}, {self.right})'

    def evaluate(self, data):
        if self.type == 'operand':
            return self.evaluate_condition(data)
        elif self.type == 'operator':
            if self.value == 'AND':
                return self.left.evaluate(data) and self.right.evaluate(data)
            elif self.value == 'OR':
                return self.left.evaluate(data) or self.right.evaluate(data)
        return False

    def evaluate_condition(self, data):
        condition = self.value.strip()
        print(f"Evaluating condition: {condition}")
        
        condition = condition.replace('\n', ' ')
        left, operator, right = condition.split(maxsplit=2)
        left_value = data.get(left.strip())
        
        if left_value is None:
            print(f"Warning: The key '{left}' was not found in the input data.")
            return False
        
        try:
            if isinstance(left_value, int):
                right_value = int(right)
            elif isinstance(left_value, float):
                right_value = float(right)
            else:
                right_value = right.strip("'")
        except ValueError:
            print(f"Error: Type mismatch for key '{left}' with value '{left_value}' and condition '{right}'.")
            return False

        print(f"Evaluating: {left_value} {operator} {right_value}")
        if operator == '>':
            return left_value > right_value
        elif operator == '<':
            return left_value < right_value
        elif operator == '=':
            return left_value == right_value
        elif operator == '>=':
            return left_value >= right_value
        elif operator == '<=':
            return left_value <= right_value
        return False

def tokenize(expression):
    token_pattern = r'(\bAND\b|\bOR\b|[()])'
    tokens = re.split(token_pattern, expression)
    return [token.strip() for token in tokens if token.strip()]

def parse_expression(tokens):
    def parse_subexpression():
        subexpr_stack = []
        operator_stack = []
        
        def reduce_stacks():
            right = subexpr_stack.pop()
            operator = operator_stack.pop()
            left = subexpr_stack.pop()
            subexpr_stack.append(Node(type='operator', left=left, right=right, value=operator))
        
        precedence = {'AND': 2, 'OR': 1}
        
        while tokens:
            token = tokens.pop(0)
            if token == '(':
                subexpr_stack.append(parse_subexpression())
            elif token == ')':
                break
            elif token in ('AND', 'OR'):
                while (operator_stack and
                       precedence[operator_stack[-1]] >= precedence[token]):
                    reduce_stacks()
                operator_stack.append(token)
            else:
                subexpr_stack.append(Node(type='operand', value=token))
        
        while operator_stack:
            reduce_stacks()
        
        return subexpr_stack[0]

    return parse_subexpression()

def init_db():
    conn = sqlite3.connect('rules.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS nodes
                 (id INTEGER PRIMARY KEY, type TEXT, left INTEGER, right INTEGER, value TEXT)''')
    conn.commit()
    conn.close()

def clear_db(conn, cursor):
    cursor.execute("DELETE FROM nodes")

def save_node(node, conn, cursor):
    cursor.execute("INSERT INTO nodes (type, left, right, value) VALUES (?, ?, ?, ?)",
                   (node.type, None, None, node.value))
    node_id = cursor.lastrowid

    if node.left:
        left_id = save_node(node.left, conn, cursor)
        cursor.execute("UPDATE nodes SET left = ? WHERE id = ?", (left_id, node_id))

    if node.right:
        right_id = save_node(node.right, conn, cursor)
        cursor.execute("UPDATE nodes SET right = ? WHERE id = ?", (right_id, node_id))

    return node_id

def save_ast(ast):
    conn = sqlite3.connect('rules.db')
    cursor = conn.cursor()
    clear_db(conn, cursor)
    root_id = save_node(ast, conn, cursor)
    conn.commit()
    conn.close()
    print(f"AST saved with root ID: {root_id}")
    print_ast(ast)
    return root_id

def load_node(node_id, conn, cursor):
    cursor.execute("SELECT * FROM nodes WHERE id=?", (node_id,))
    row = cursor.fetchone()
    if row:
        node_type, left_id, right_id, value = row[1], row[2], row[3], row[4]
        left = load_node(left_id, conn, cursor) if left_id else None
        right = load_node(right_id, conn, cursor) if right_id else None
        return Node(type=node_type, left=left, right=right, value=value)
    return None

def load_ast(root_id):
    conn = sqlite3.connect('rules.db')
    cursor = conn.cursor()
    root_node = load_node(root_id, conn, cursor)
    conn.close()
    print(f"Loaded AST with root ID: {root_id}")
    print_ast(root_node)
    return root_node

def print_ast(node, level=0):
    indent = '  ' * level
    if node.type == 'operator':
        print(f"{indent}{node.value}")
        if node.left:
            print_ast(node.left, level + 1)
        if node.right:
            print_ast(node.right, level + 1)
    else:
        print(f"{indent}{node.value}")

def evaluate_ast(ast, data):
    return ast.evaluate(data)

def combine_multiple_rules(rules):
    operator_counter = Counter()
    asts = []

    for rule in rules:
        tokens = tokenize(rule)
        ast = parse_expression(tokens)
        asts.append(ast)
        count_operators(ast, operator_counter)
    
    root_operator = 'AND' if operator_counter['AND'] >= operator_counter['OR'] else 'OR'
    
    combined_ast = asts[0]
    for ast in asts[1:]:
        combined_ast = Node(type='operator', left=combined_ast, right=ast, value=root_operator)

    return combined_ast

def count_operators(node, counter):
    if node.type == 'operator':
        counter[node.value] += 1
        if node.left:
            count_operators(node.left, counter)
        if node.right:
            count_operators(node.right, counter)

@app.route('/parse_rule', methods=['POST'])
def parse_rule_endpoint():
    rule = request.json['rule']
    tokens = tokenize(rule)
    ast = parse_expression(tokens)
    rule_id = save_ast(ast)
    return jsonify({'ruleId': rule_id})

@app.route('/combine_rules', methods=['POST'])
def combine_rules_endpoint():
    rules = request.json['rules']
    combined_ast = combine_multiple_rules(rules)
    rule_id = save_ast(combined_ast)
    return jsonify({'ruleId': rule_id})

@app.route('/evaluate', methods=['POST'])
def evaluate_endpoint():
    rule_id = request.json['ruleId']
    data = request.json['data']
    print(data)  # Debugging line to print input data
    ast = load_ast(rule_id)
    result = evaluate_ast(ast, data)
    return jsonify({'result': result})

@app.route('/get_ast', methods=['GET'])
def get_ast_endpoint():
    rule_id = request.args.get('ruleId')
    ast = load_ast(int(rule_id))
    ast_dict = node_to_dict(ast)
    return jsonify(ast_dict)

def node_to_dict(node):
    if node is None:
        return None
    return {
        'type': node.type,
        'value': node.value,
        'left': node_to_dict(node.left),
        'right': node_to_dict(node.right)
    }

if __name__ == '__main__':
    init_db()
    app.run(port=5001)
