from fastapi.routing import APIRoute
print([a for a in dir(APIRoute) if not a.startswith("_")])
route = APIRoute("/test", lambda: None, methods=["GET"], deprecated=True)
print("deprecated:", getattr(route, 'deprecated', 'N/A'))
