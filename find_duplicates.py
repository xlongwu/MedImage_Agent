from fastapi.routing import APIRoute

from src.backend.app.main import create_app

app = create_app()
seen = {}
duplicates = []

for route in app.routes:
    if not isinstance(route, APIRoute):
        continue
    for method in route.methods or set():
        if method in {'HEAD', 'OPTIONS'}:
            continue
        key = (method, route.path)
        if key in seen:
            r1 = seen[key]
            r2 = route
            print(f'Duplicate: {key}')
            m1 = getattr(r1, 'endpoint', None)
            m2 = getattr(r2, 'endpoint', None)
            print(f'  Route 1 module: {m1.__module__ if m1 else "unknown"}')
            print(f'  Route 2 module: {m2.__module__ if m2 else "unknown"}')
            duplicates.append(key)
        else:
            seen[key] = route

print(f'\nTotal duplicates: {len(duplicates)}')
