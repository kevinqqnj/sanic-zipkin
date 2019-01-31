from sanic import Sanic, response
from sanic_zipkin import SanicZipkin, logger, sz_rpc

import asyncio

backend_service = 'http://127.0.0.1:8001/api/consume'
backend_service1 = 'http://127.0.0.1:8001/api/post'
backend_service2 = 'http://127.0.0.1:8001/api/get'

app = Sanic(__name__)
sz = SanicZipkin(app, service='service-a')


@app.route("/")
async def index(request):
    return response.json({"hello": "from index"})

@logger()
async def db_access(context, data):
    await asyncio.sleep(0.1)
    print(f'db_access done. data: {data}')
    return

@sz.route("/2")
async def method_call(request, context):
    await db_access(context, 'this is method_call data')
    return response.json({"hello": 'method_call'})

@logger()
async def decorate_demo(context, data):
    await db_access(context, data)
    data = {'payload': 'rpc call data of decorate_demo'}
    rsp = await sz_rpc(context, backend_service2, data, method='GET')
    print(rsp.status, await rsp.text())
    return

@sz.route("/3")
async def rpc_call(request, context):
    await decorate_demo(context, 'this is index4 data')
    data = {'payload': 'rpc call data of rpc_call'}
    rsp = await sz_rpc(context, backend_service1, data) # default is 'POST'
    print(rsp.status, await rsp.text())
    return response.json({"hello": 'rpc_call'})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
