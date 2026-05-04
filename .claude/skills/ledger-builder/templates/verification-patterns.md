# Verification Patterns

Patterns for generating behavioral verification commands.

---

## Strategy: Test Suite First

If a test exists or will be created, reference it:

```markdown
# TypeScript/Jest
Verify: `npm test -- --testPathPattern="event.test" --testNamePattern="constructor sets id"`

# Python/pytest
Verify: `pytest tests/test_event.py::test_constructor -v`

# Go
Verify: `go test ./pkg/event -run TestConstructor`

# Rust
Verify: `cargo test event::test_constructor -- --nocapture`
```

**This is the most reliable verification.** Use inline assertions only when no test exists.

---

## Task Complexity Detection

| Complexity | Indicators | Verification Strategy |
|------------|------------|----------------------|
| Simple | File creation, config, no logic | Structural (`test -f`, `grep`) |
| Complex | Classes, functions, state, behavior | Behavioral (run code, assert) |

**Default to behavioral** for anything with code logic. Only use structural for:
- `__init__.py` files
- Config/data files (JSON, YAML, TOML)
- CSS/styling
- Documentation

---

## TypeScript/JavaScript

### Simple (Structural)

```bash
# File exists
test -f {path}

# Export exists
grep -E "export.*(class|function|const) {Name}" {path}

# Multiple exports
grep -cE "export.*(Name1|Name2|Name3)" {path} | grep -q "3"
```

### Complex (Behavioral)

```bash
# Module loads without error
npx ts-node -e "import '{path}'"

# Class instantiates
npx ts-node -e "import {C} from '{path}'; new C()"

# Constructor sets properties
npx ts-node -e "import {C} from '{path}'; const c = new C('x', 1); if(c.id !== 'x') process.exit(1)"

# Method returns expected value
npx ts-node -e "import {C} from '{path}'; if(new C().method() !== expected) process.exit(1)"

# State machine transition
npx ts-node -e "import {SM} from '{path}'; const sm = new SM(); sm.transition('NEXT'); if(sm.state !== 'NEXT') process.exit(1)"
```

### With Dependencies (using project's test runner)

```bash
# Run specific test
npm test -- --testPathPattern="{file}" --testNamePattern="{name}"

# Run test file
npm test -- {path}

# Jest with coverage threshold
npm test -- --coverage --coverageThreshold='{"global":{"lines":80}}'
```

---

## Python

### Simple (Structural)

```bash
# File exists
test -f {path}

# Class exists
grep -E "class {Name}" {path}

# Function exists
grep -E "def {name}" {path}

# Multiple definitions
grep -cE "class (Name1|Name2)|def (name1|name2)" {path}
```

### Complex (Behavioral)

```bash
# Module imports
python -c "from {module} import {Name}"

# Class instantiates
python -c "from {module} import {C}; {C}()"

# Constructor sets attributes
python -c "from {module} import {C}; c = {C}('x', 1); assert c.id == 'x' and c.version == 1"

# Method works
python -c "from {module} import {C}; assert {C}().method() == expected"

# Enum has values
python -c "from {module} import {Enum}; assert hasattr({Enum}, 'VALUE1') and hasattr({Enum}, 'VALUE2')"

# State machine
python -c "from {module} import {SM}; sm = {SM}(); sm.transition('NEXT'); assert sm.state == 'NEXT'"
```

### With Test Runner

```bash
# pytest specific test
pytest {test_path}::{test_class}::{test_method} -v

# pytest with pattern
pytest -k "{pattern}" -v

# unittest
python -m pytest {test_path} -v
```

---

## Go

### Simple (Structural)

```bash
# File exists
test -f {path}

# Package builds
go build ./{dir}

# Symbol documented
go doc {pkg}.{Symbol}
```

### Complex (Behavioral)

```bash
# Test passes
go test ./{dir} -run {TestPattern} -v

# Test with race detection
go test ./{dir} -race -run {TestPattern}

# Build and type check
go vet ./{dir}
```

---

## Rust

### Simple (Structural)

```bash
# File exists
test -f {path}

# Crate compiles
cargo check -p {package}

# No warnings
cargo clippy -p {package} -- -D warnings
```

### Complex (Behavioral)

```bash
# Test passes
cargo test -p {package} {test_pattern} -- --nocapture

# Integration test
cargo test --test {test_name}

# Doc tests pass
cargo test --doc -p {package}
```

---

## Shell/Bash Scripts

### Structural

```bash
# File exists and executable
test -x {path}

# Has shebang
head -1 {path} | grep -E "^#!.*(bash|sh)"

# Shellcheck passes
shellcheck {path}
```

### Behavioral

```bash
# Script runs without error (dry run if supported)
{path} --help || {path} -h

# Script with test args
{path} --test || echo "No test mode"
```

---

## Config Files (JSON, YAML, TOML)

Config files can't be behaviorally verified. Use schema validation:

```bash
# JSON syntax valid
python -c "import json; json.load(open('{path}'))"

# YAML syntax valid
python -c "import yaml; yaml.safe_load(open('{path}'))"

# JSON has required keys
python -c "import json; d = json.load(open('{path}')); assert all(k in d for k in ['key1', 'key2'])"

# TOML syntax valid
python -c "import tomllib; tomllib.load(open('{path}', 'rb'))"
```

---

## When Behavioral Verification is Impossible

Some tasks can only be structurally verified:

| Task Type | Verification | Notes |
|-----------|--------------|-------|
| Config files | Schema/syntax check | See above |
| CSS/SCSS | File exists | Consider stylelint |
| Documentation | File exists | Consider markdownlint |
| Binary assets | File exists + size check | `test -s {path}` |
| Generated files | File exists | Verify generator ran |

For these, use structural verification and ensure DoD explicitly states what manual review is required (if any).

---

## Composing Verification Commands

For complex DoDs with multiple requirements, chain assertions:

```bash
# Python - multiple assertions
python -c "
from {module} import {C}
c = {C}()
assert hasattr(c, 'prop1'), 'missing prop1'
assert callable(getattr(c, 'method', None)), 'missing method'
assert c.method() == expected, 'wrong return value'
"

# TypeScript - multiple assertions
npx ts-node -e "
import {C} from '{path}';
const c = new C();
if (!('prop' in c)) process.exit(1);
if (typeof c.method !== 'function') process.exit(1);
if (c.method() !== expected) process.exit(1);
"
```

Keep verification commands **self-contained** - they should work with no external setup beyond the code being verified.
