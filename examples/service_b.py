from sanic import Sanic, response
from sanic_zipkin import SanicZipkin, logger


app = Sanic(__name__)
sz = SanicZipkin(app, service='backend-b')


@sz.route("/api/get", methods=['GET'])
async def handler_get(request, context):
    message = 'get method'
    return response.json({"hello": "handler_get"})

@sz.route("/api/post", methods=['POST'])
async def handler_post(request, context):
    message = 'post method'
    return response.json({"hello": "handler_post"})

@app.route("/")
async def index(request):
    return response.json({"hello": 'service-b'})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8001, debug=True)
