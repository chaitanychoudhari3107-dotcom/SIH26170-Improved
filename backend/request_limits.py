"""Bound buffered API request bodies, including chunked uploads."""
from starlette.responses import JSONResponse
class RequestLimits:
    def __init__(self, app, max_bytes=2_100_000):
        self.app, self.max_bytes = app, max_bytes
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in {'POST','PUT','PATCH'}:
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            size += len(message.get('body',b''))
            if size > self.max_bytes:
                return await JSONResponse({'detail':'Request body exceeds 2.1 MB'},413)(scope,receive,send)
            chunks.append(message)
            if not message.get('more_body',False):
                break
        async def replay():
            return chunks.pop(0) if chunks else await receive()
        await self.app(scope,replay,send)
