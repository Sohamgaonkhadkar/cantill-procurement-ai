"""Keep the checked-in OpenAPI synchronized without starting a server."""
import json
from pathlib import Path
from backend.api import app
Path('openapi.json').write_text(json.dumps(app.openapi(),indent=2)+'\n',encoding='utf-8')
print('Exported openapi.json')
