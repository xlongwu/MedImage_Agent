import pathlib
import re

p = pathlib.Path('D:/deep_learning_code/MedImage_Agent/src/backend/app/api/dashboard_routes.py')
text = p.read_text(encoding='utf-8')
lines = text.splitlines()

# Just check the conversion/dry-run route
target_line = '@router.post("/api/projects/{project_id}/conversion/dry-run", response_model=ConversionDryRunResponse)'
for i, line in enumerate(lines):
    if 'conversion/dry-run' in line:
        print(f'Found at line {i+1}: {line}')
        # Check regex
        m = re.match(r'^(\s*@router\.(?:get|post|put|delete|patch)\()(".*?")(,.*)$', line)
        print(f'Regex match: {m is not None}')
        if m:
            print(f'Path: {m.group(2)}')
        break
