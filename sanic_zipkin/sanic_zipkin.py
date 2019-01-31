from spf.plugin import SanicPlugin
from spf.context import ContextDict
from spf.plugins.contextualize import Contextualize
from sanic.response import text
from sanic.request import Request
from sanic.log import logger as _logger

import aiozipkin as az
import aiohttp, asyncio, time, json
import logging, functools
from logging import DEBUG


def gen_span(name, context):
    if context.span:
        # _logger.debug(context.span)
        with context.tracer.new_child(context.span[-1].context) as child_span:
            child_span.name(name)
            child_span.tag('event', 'server')
            context.span.append(child_span)
            return child_span
    else:
        with context.tracer.new_trace() as span:
            span.name(name)
            span.tag('event', 'server')
            context.span.append(child_span)
            return span

def request_span(request, context):
    # [print(i, eval(f'request.{i}')) for i in dir(request) if hasattr(request,i) and not i.startswith('__')]
    context.log(DEBUG, f'REQUEST json: {request.json}, args: {request.args}')
    headers = request.parsed_json.get('zipkin_headers', None) if request.json else \
                request.args.get('zipkin_headers', None)
    if headers:
        # calling from another service
        headers = json.loads(headers)
        span_context = az.make_context(headers)
        with context.tracer.new_child(span_context) as span:
            span.name(f'{request.method} {request.path}')
            request_headers = {
                'http.path':request.path,
                'http.method':request.method,
                'http.path':request.path,
                'http.route':request.url,
                'peer.ip':request.remote_addr or request.ip,
                'peer.port':request.port,
            }
            [span.tag(k, v) for k,v in request_headers.items()]
            span.kind(az.SERVER)
    else:
        # calling from end-user
        with context.tracer.new_trace() as span:
            span.name(f'{request.method} {request.path}')
            request_headers = {
                'http.path':request.path,
                'http.method':request.method,
                'http.path':request.path,
                'http.route':request.url,
                'peer.ip':request.remote_addr or request.ip,
                'peer.port':request.port,
            }
            [span.tag(k, v) for k,v in request_headers.items()]
            span.kind(az.CLIENT)
    return span

class SanicZipkin(Contextualize):
    def __init__(self, *args, **kwargs):
        super(SanicZipkin, self).__init__(*args, **kwargs)
        self.zipkin_address = None
        self.service = None
        self.host = None
        self.port = None

    def on_before_registered(self, context, *args, **kwargs):
        self.zipkin_address = kwargs.get('zipkin_address', 'http://127.0.0.1:9411/api/v2/spans')
        self.service = kwargs.get('service', __name__)
        self.host = kwargs.get('host', '127.0.0.1')
        self.port = kwargs.get('port', 8000)
        _logger.info(f'SanicZipkin: before registered: service={self.service}')

    def on_registered(self, context, reg, *args, **kwargs):
        # print(f'After Registered')
        ...

    @staticmethod
    def logger(type=None, category=None, detail=None, description=None,
               tracing=True, level=logging.INFO, *args, **kwargs):
        def decorator(fn=None):
            @functools.wraps(fn)
            async def _decorator(*args, **kwargs):
                # print('_decorator args: ', args, kwargs)
                context = args[0] if len(args) > 0 and isinstance(args[0], ContextDict) else None
                if context is None:
                    _logger.error('decorator "logger" must use "context" as first args.')
                log = {
                    # 'category': category or request.app.name if request else '',  #服务名
                    'fun_name': fn.__name__,
                    'detail': detail or fn.__name__,  # 方法名或定义URL列表
                    'log_type': type or 'method',
                    'description': description if description else fn.__doc__ if fn.__doc__ else '',
                }

                span = gen_span(fn.__name__, context)
                context.zipkin_headers.append(span.context.make_headers())

                # _args = list(args).remove(context)  # args is tuple
                start_time = time.time()
                log.update({
                    'start_time': time.time(),
                    "args": ",".join([str(a) for a in args[1:]]) if isinstance(args, (list, tuple)) else str(args),
                    "kwargs": kwargs.copy() if kwargs else {},
                })
                
                try:
                    exce = False
                    res = await fn(*args, **kwargs)
                    return res
                except Exception as e:
                    exce = True
                    raise e
                finally:
                    try:
                        if tracing:
                            end_time = time.time()
                            log.update({
                                'component': '{}-{}'.format(fn.__name__, log['log_type']),
                                'end_time': end_time,
                                'duration': end_time - start_time
                            })
                        [span.tag(k,v) for k,v in log.items()]

                        # clean up tmp vars for this wrapper
                        context.span.pop()
                        context.zipkin_headers.pop()

                        if exce:
                            _logger.error('{} has error'.format(fn.__name__), log)
                        else:
                            _logger.info('{} is success'.format(fn.__name__), log)
                    except Exception as e:
                        _logger.error(e)
            _decorator.detail = detail
            _decorator.description = description
            _decorator.level = level
            return _decorator
        decorator.detail = detail
        decorator.description = description
        decorator.level = level
        return decorator

sanic_zipkin = instance = SanicZipkin()


@sanic_zipkin.listener('before_server_start')
async def setup_zipkin(app, loop, context):
    endpoint = az.create_endpoint(sanic_zipkin.service, ipv4=sanic_zipkin.host,
                                port=sanic_zipkin.port)
    context.tracer = await az.create(sanic_zipkin.zipkin_address, endpoint, 
                                sample_rate=1.0)
    trace_config = az.make_trace_config(context.tracer)
    context.aio_session = aiohttp.ClientSession(trace_configs=[trace_config])
    context.span = []
    context.zipkin_headers = []
    # context.log(DEBUG, 'before_server_start: '+str(context))

@sanic_zipkin.middleware(priority=2, with_context=True)
def mw1(request, context):
    context.log(DEBUG, f'mw-request: add span and headers before request')
    span = request_span(request, context)
    context.span.append(span)
    context.zipkin_headers.append(span.context.make_headers())
    # for k,v in context.items(): print(f'[context:{k:8}]: {v}')

@sanic_zipkin.middleware(priority=8, attach_to='response', relative='post',
                      with_context=True)
def mw2(request, response, context):
    # del context['span']
    context.span.pop()  # TODO = []?
    context.zipkin_headers.pop()
    context.log(DEBUG, 'mw-response: clear span/zipkin_headers after Response')
    # for k,v in context.items(): print(f'[context:{k:8}]: {v}')

@sanic_zipkin.route('/test_plugin', with_context=True)
def t1(request, context):
    for k,v in context.items(): print(f'[context:{k:8}]: {v}')
    return text('from plugin!')

def logger(*args, **kwargs):
    return sanic_zipkin.logger(*args, with_context=True,
                              run_middleware=True, **kwargs)

async def sz_rpc(context, url, data, method='POST'):
    data.update({'zipkin_headers': json.dumps(context.zipkin_headers[-1])})
    if method.upper() == 'POST':
        return await context.aio_session.post(url, json=data)
    else: 
        return await context.aio_session.get(url, params=data)

__all__ = ['sanic_zipkin', 'logger', 'sz_rpc']