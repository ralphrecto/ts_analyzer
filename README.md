# TypeScript Codebase Analyzer

A tool for analyzing TypeScript codebases using TreeSitter, designed to be used from a Jupyter notebook.

## Features

- Find all imports of specific classes or modules
- Find all calls to specific functions and extract their arguments
- Find class definitions
- Execute custom TreeSitter queries
- Generate codebase statistics
- Analyze code patterns with lexical analysis

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Clone the TreeSitter TypeScript grammar:

```bash
mkdir -p vendor
git clone https://github.com/tree-sitter/tree-sitter-typescript vendor/tree-sitter-typescript
```

## Usage

1. Start a Jupyter notebook:

```bash
jupyter notebook typescript_analysis.ipynb
```

2. Update the `CODEBASE_PATH` variable in the notebook to point to your TypeScript codebase.

3. Run the cells to perform different types of analyses.

## Examples

### Find imports of a specific class

```python
imports = analyzer.find_imports('UserService')
```

### Find function calls and extract first arguments

```python
function_calls = analyzer.find_function_calls('fetchData', extract_first_arg=True)
```

### Find class definitions

```python
classes = analyzer.find_class_definitions()
```

### Use custom TreeSitter queries

```python
query_string = """
(call_expression
  function: (identifier) @function_name (#eq? @function_name "useEffect")
  arguments: (arguments
    (_)
    (array) @dependencies))
"""
query_results = analyzer.custom_query(query_string)
```

## Custom Analysis

You can extend the `TypeScriptAnalyzer` class to add custom functionality specific to your codebase's patterns and architecture.

## Tree-sitter Query Language

The Tree-sitter query language allows you to define complex patterns to search for in your code. More information can be found in the [Tree-sitter documentation](https://tree-sitter.github.io/tree-sitter/using-parsers#pattern-matching-with-queries).