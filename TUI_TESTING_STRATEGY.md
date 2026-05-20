# Switchboard TUI Testing Strategy

## Overview
This document outlines the testing strategy for the Switchboard TUI foundation layer, providing guidance for implementing comprehensive test coverage across all components.

## Expected File Structure

```
switchboard/
├── tui/
│   ├── __init__.py
│   ├── __main__.py          # CLI entry point
│   ├── cli.py               # Argument parsing
│   ├── app.py               # Textual app shell
│   ├── state.py             # State dataclasses
│   ├── polling.py           # Log parser, bd CLI, file tailer
│   └── switchboard.tcss     # Theme CSS
├── tests/
│   └── tui/
│       ├── __init__.py
│       ├── test_state.py                 # State dataclasses tests
│       ├── test_log_parser.py           # Log parsing tests  
│       ├── test_bd_cli_wrappers.py      # bd CLI wrapper tests
│       ├── test_file_tailer.py          # File tailing tests
│       ├── test_app_shell.py            # Textual app tests
│       ├── test_cli_entry.py            # CLI entry point tests
│       ├── conftest.py                  # Shared fixtures
│       └── test_integration.py          # Integration tests
└── pyproject.toml           # Dependencies: textual, pytest, pytest-asyncio
```

## Testing Framework Configuration

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --cov=switchboard.tui
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90
    -v
asyncio_mode = auto
```

### Dependencies Required
```toml
[tool.poetry.dependencies]
python = "^3.11"
textual = "^0.44.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
pytest-asyncio = "^0.21.0"
pytest-mock = "^3.11.0"
```

## Testing Principles

### 1. Test-Driven Development
- Write tests BEFORE implementation
- Red-Green-Refactor cycle
- Focus on behavior, not implementation details

### 2. Testing Pyramid
- **Unit Tests (70%)**: Fast, isolated, comprehensive coverage
- **Integration Tests (20%)**: Component interaction verification
- **End-to-End Tests (10%)**: Full workflow validation

### 3. Async Testing Strategy
- Use `pytest-asyncio` for async function testing
- Mock external async operations (subprocess, file I/O)
- Test async generators with `aiohttp` patterns
- Verify proper async resource cleanup

### 4. Mock Strategy
- Mock external dependencies (subprocess, file system)
- Mock at the boundary (not internal implementation)
- Use dependency injection where possible
- Verify mock interactions

## Component Testing Strategies

### State Management (state.py)
**Testing Focus**: Data structure integrity and business logic
- **Dataclass Validation**: Type checking, field validation, immutability
- **State Transitions**: Valid/invalid state changes
- **Collection Management**: Dict/deque operations, size limits
- **Serialization**: JSON conversion for persistence

**Key Test Patterns**:
```python
def test_dataclass_field_types():
    # Verify type annotations enforced
    
def test_state_update_immutability():
    # Verify updates create new instances
    
def test_collection_size_limits():
    # Verify deque max size enforced
```

### Log Parser (polling.py)
**Testing Focus**: Robust parsing of log formats
- **Format Recognition**: All log line patterns
- **Error Handling**: Malformed lines, invalid dates
- **Event Classification**: Correct event type extraction  
- **Performance**: Handle high-volume log streams

**Key Test Patterns**:
```python
@pytest.mark.parametrize("log_line,expected", [
    ("2026-05-20 14:23:01 [INFO] Claimed mol-2hn", LogEvent(...)),
    # ... more test cases
])
def test_parse_log_line_patterns(log_line, expected):
    # Parameterized testing for all log patterns
```

### bd CLI Wrappers (polling.py) 
**Testing Focus**: External command integration
- **Command Execution**: Proper subprocess usage
- **JSON Parsing**: Handle all response formats
- **Error Scenarios**: Network failures, command not found
- **Timeout Handling**: Long-running commands

**Key Test Patterns**:
```python
@pytest.mark.asyncio
async def test_bd_json_with_mock():
    with patch('subprocess.run') as mock_run:
        # Mock subprocess behavior
        
@pytest.mark.asyncio  
async def test_bd_json_timeout():
    # Test timeout scenarios
```

### File Tailer (polling.py)
**Testing Focus**: Async file monitoring
- **File Watching**: New line detection
- **File Lifecycle**: Creation, rotation, deletion
- **Performance**: Large files, high write rates
- **Error Recovery**: Permission errors, file system issues

**Key Test Patterns**:
```python
@pytest.mark.asyncio
async def test_tail_file_new_lines():
    # Test async iteration over new lines
    
@pytest.mark.asyncio
async def test_file_rotation_handling():
    # Test file replacement scenarios
```

### App Shell (app.py)
**Testing Focus**: Textual application lifecycle
- **Application Startup**: Widget mounting, CSS loading
- **Event Handling**: Key bindings, user input
- **Layout Management**: Responsive design, terminal resize
- **Error Display**: User-friendly error messages

**Key Test Patterns**:
```python
def test_app_with_textual_tester():
    with AppTester(SwitchboardApp) as tester:
        # Test UI interactions
        
def test_css_theme_loading():
    # Verify amber CRT theme applied
```

### CLI Entry Point (cli.py, __main__.py)
**Testing Focus**: Command-line interface
- **Argument Parsing**: All CLI options and validation
- **Error Handling**: Invalid arguments, missing files  
- **Module Execution**: `python -m switchboard.tui`
- **Integration**: CLI arguments passed to app

**Key Test Patterns**:
```python
def test_cli_argument_parsing():
    # Test argparse behavior
    
def test_module_execution():
    # Test __main__ entry point
```

## Integration Testing Strategy

### Test Scenarios
1. **End-to-End Workflow**: CLI → App → State → Polling → Display
2. **Real Log Processing**: Use sample agent_router.log files
3. **Mock bd Integration**: Test with mock bd command responses
4. **Error Recovery**: Simulate failures and verify recovery

### Sample Integration Test
```python
@pytest.mark.asyncio
async def test_full_workflow_integration():
    """Test complete workflow from CLI to state updates."""
    # 1. Start app with test configuration
    # 2. Mock bd command responses
    # 3. Feed sample log data
    # 4. Verify state updates correctly
    # 5. Verify UI displays correct information
```

## Performance Testing

### Benchmarks
- **Log Parsing**: Process 10,000 log lines in < 1 second
- **State Updates**: Handle 100 worker updates in < 100ms
- **Memory Usage**: Stable memory over 24-hour simulation
- **UI Responsiveness**: < 16ms frame time for 60fps

### Performance Test Examples
```python
def test_log_parser_performance():
    """Verify log parsing performance requirements."""
    start_time = time.time()
    for line in large_log_sample:
        parse_log_line(line)
    elapsed = time.time() - start_time
    assert elapsed < 1.0  # 1 second for 10k lines

@pytest.mark.asyncio
async def test_memory_stability():
    """Verify memory usage remains stable."""
    # Simulate long-running session
    # Monitor memory usage over time
    # Assert no significant memory leaks
```

## Test Data Management

### Sample Data Sets
- **log_samples.txt**: Representative agent_router log lines
- **bd_responses.json**: Sample bd command JSON outputs  
- **worker_states.json**: Various worker state scenarios
- **error_cases.txt**: Malformed inputs for error testing

### Test Data Generation
```python
def generate_sample_log_lines(count=1000):
    """Generate realistic log lines for performance testing."""
    # Create varied log entries with proper timestamps
    
def generate_worker_scenarios():
    """Generate worker state test scenarios."""
    # Create various worker state combinations
```

## Continuous Integration

### CI Pipeline Requirements
1. **Test Execution**: Run all tests on Python 3.11+
2. **Coverage Report**: Generate and publish coverage reports
3. **Performance Benchmarks**: Track performance over time
4. **Dependency Security**: Scan for security vulnerabilities
5. **Code Quality**: Run linting and type checking

### GitHub Actions Example
```yaml
name: TUI Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        run: pytest
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Success Criteria

### Test Metrics
- **Line Coverage**: ≥ 90%
- **Branch Coverage**: ≥ 85% 
- **Function Coverage**: 100%
- **Test Execution Time**: < 30 seconds for full suite
- **Performance Benchmarks**: All benchmarks passing

### Quality Gates
- All tests passing in CI
- No critical security vulnerabilities
- Code quality score > 8.0
- Documentation coverage > 80%

## Development Workflow

### For Tests Agent
1. **Read Specifications**: Study acceptance criteria and test specifications
2. **Set Up Structure**: Create test files and directory structure
3. **Write Unit Tests**: Start with individual component tests
4. **Add Integration Tests**: Test component interactions
5. **Performance Tests**: Add benchmark and stress tests
6. **Documentation**: Update test documentation

### Test Implementation Order
1. **State dataclasses** (foundation, no dependencies)
2. **Log parser** (standalone functionality)  
3. **bd CLI wrappers** (external dependency mocking)
4. **File tailer** (async file operations)
5. **CLI entry point** (argument parsing)
6. **App shell** (Textual integration)
7. **Integration tests** (full workflow)

This testing strategy ensures comprehensive coverage while maintaining maintainable and performant tests that support rapid development of the Switchboard TUI foundation layer.