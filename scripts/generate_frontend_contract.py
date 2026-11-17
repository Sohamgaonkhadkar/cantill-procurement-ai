"""Generate TypeScript models and Zod validators from the authoritative OpenAPI."""
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
# Git checkouts can use CRLF on Windows; normalize before hashing so the
# generated contract is identical to the committed LF source on Linux.
source=(ROOT/'openapi.json').read_text(encoding='utf-8').encode('utf-8')
schemas=json.loads(source)['components']['schemas']
def name(value): return re.sub(r'\W','_',value)
def ref(s): return name(s['$ref'].rsplit('/',1)[1])
def ts(s):
    if '$ref' in s: return ref(s)
    if 'const' in s: return json.dumps(s['const'])
    if 'enum' in s: return ' | '.join(json.dumps(x) for x in s['enum'])
    if 'anyOf' in s: return '('+' | '.join(ts(x) for x in s['anyOf'])+')'
    t=s.get('type')
    if t=='array': return f'Array<{ts(s.get("items",{}))}>'
    if t=='object' or 'properties' in s:
        props=s.get('properties',{}); required=s.get('required',[])
        members=[json.dumps(k)+('' if k in required else '?')+': '+ts(v) for k,v in props.items()]
        additional=s.get('additionalProperties')
        if additional: members.append('[key: string]: '+(ts(additional) if isinstance(additional,dict) and not props else 'unknown'))
        return '{ '+'; '.join(members)+' }'
    return {'string':'string','integer':'number','number':'number','boolean':'boolean','null':'null'}.get(t,'unknown')
def zod(s):
    if '$ref' in s: return 'z.lazy(() => '+ref(s)+'Schema)'
    if 'const' in s: return 'z.literal('+json.dumps(s['const'])+')'
    if 'enum' in s: return 'z.enum('+json.dumps(s['enum'])+')'
    if 'anyOf' in s: return 'z.union(['+', '.join(zod(x) for x in s['anyOf'])+'])'
    t=s.get('type')
    if t=='array': return 'z.array('+zod(s.get('items',{}))+')'
    if t=='object' or 'properties' in s:
        props=s.get('properties',{}); required=s.get('required',[])
        if not props: return 'z.record(z.string(),'+(zod(s['additionalProperties']) if isinstance(s.get('additionalProperties'),dict) else 'z.unknown()')+')'
        members=[json.dumps(k)+': '+zod(v)+('' if k in required else '.optional()') for k,v in props.items()]
        return 'z.object({'+', '.join(members)+'})'+('.passthrough()' if s.get('additionalProperties') else '.strict()' if s.get('additionalProperties') is False else '')
    base={'string':'z.string()','integer':'z.number().int()','number':'z.number()','boolean':'z.boolean()','null':'z.null()'}.get(t,'z.unknown()')
    if t=='string':
        for key,method in [('minLength','min'),('maxLength','max')]:
            if key in s: base+=f'.{method}({s[key]})'
        if 'pattern' in s: base+='.regex(new RegExp('+json.dumps(s['pattern'])+'))'
    return base
parts=['// Generated from root openapi.json; do not edit.','// sha256: '+hashlib.sha256(source).hexdigest(),'import { z } from "zod";']
for key,schema in schemas.items(): parts.append('export type '+name(key)+' = '+ts(schema)+';')
for key,schema in schemas.items(): parts.append('export const '+name(key)+'Schema: z.ZodType<'+name(key)+'> = '+zod(schema)+';')
result='\n'.join(parts)+'\n'; target=ROOT/'frontend/src/api/generated.ts'
if '--check' in sys.argv:
    if target.read_text(encoding='utf-8')!=result: raise SystemExit('Frontend contract is stale; run python -m scripts.generate_frontend_contract')
    print('Generated frontend contract matches OpenAPI')
else: target.write_text(result,encoding='utf-8'); print('Generated frontend TypeScript and Zod contract')
