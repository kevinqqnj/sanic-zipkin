# sanic-zipkin
sanic plugin/extension to integrate reporting opentracing aiozipkin

## Features
* Initial release
* adding "Request span" by default
* if Request is from another micro-service endpoint, span will be attached to that endpoint
* use "logger" decorator to create span for "methods" calls
* use "sz_rpc" method to create sub-span for RPC calls, attaching to parent span

## Examples
1. run `examples/servic_a.py` and `examples/service_b.py`
2. use Docker to run zipkin or jaeger:
`docker run -d -p9411:9411 openzipkin/zipkin:latest`
or
`docker run -d -e COLLECTOR_ZIPKIN_HTTP_PORT=9411 -p5775:5775/udp -p6831:6831/udp -p6832:6832/udp -p5778:5778 -p16686:16686 -p14268:14268 -p9411:9411 jaegertracing/all-in-one`
3. access the endpoint:
- `curl localhost:8000/` to see plugin's basic usage

```
from sanic_zipkin import SanicZipkin, logger, sz_rpc

app = Sanic(__name__)
# initilize plugin, default parameters:
#        zipkin_address = 'http://127.0.0.1:9411/api/v2/spans'
#        service = __name__
#        host = '127.0.0.1'
#        port = 8000
sz = SanicZipkin(app, service='service-a')


@app.route("/")
async def index(request):
    return response.json({"hello": "from index"})
```
This "/" endpoint will add trace span to zipkin automatically


- `curl localhost:8000/2` to see how to decorate methods and chain-calls

```
@logger()
async def db_access(context, data):
    await asyncio.sleep(0.1)
    print(f'db_access done. data: {data}')
    return

@sz.route("/2")
async def method_call(request, context):
    await db_access(context, 'this is method_call data')
    return response.json({"hello": 'method_call'})
```
Use "@logger" decorator to generate span for methods. Note: in this case, you need to use "@sz.route", and pass `context` parameter to method calls.

- `curl localhost:8000/3` to see how RPC calls working, both GET/POST is supported

```
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
    rsp = await sz_rpc(context, backend_service1, data) # default method='POST'
    print(rsp.status, await rsp.text())
    return response.json({"hello": 'rpc_call'})
```
method `sz_rpc` just wrapper span injection to RPC POST/GET calls. In peer server, span-context will be automatically extracted and generate a chain-view in zipkin.

4. check the tracing output in Zipkin/Jaeger UI 
