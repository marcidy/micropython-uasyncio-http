import gc
import re
import os


url_pat = re.compile(
    r'^(([^:/\\?#]+):)?' +  # scheme                # NOQA
    r'(//([^/\\?#]*))?' +   # user:pass@host:port   # NOQA
    r'([^\\?#]*)' +         # route                 # NOQA
    r'(\\?([^#]*))?' +      # query                 # NOQA
    r'(#(.*))?')            # fragment              # NOQA


def pre_route(file):

    async def _func(writer):
        await send_file(writer, file)

    return _func


routes = {}

# b'/': pre_route('/www/page.htm'),
# b'/static/jquery.js': pre_route('/www/jquery-3.5.1.min.js')}


def route(location, resource):
    global routes
    routes[location] = pre_route(resource)


async def send_file(writer, file):
    fstat = os.stat(file)
    fsize = fstat[6]

    writer.write(b'HTTP/1.1 200 OK\r\n')
    writer.write(b'Content-Type: text/html\r\n')
    writer.write('Content-Length: {}\r\n'.format(fsize).encode('utf-8'))
    writer.write(b'Accept-Ranges: none\r\n')
    writer.write(b'Transfer-Encoding: chunked\r\n')
    writer.write(b'\r\n')
    await writer.drain()
    gc.collect()
    max_chunk_size = 1024
    with open(file, 'rb') as f:
        for x in range(0, fsize, max_chunk_size):
            chunk_size = min(max_chunk_size, fsize-x)
            chunk_header = "{:x}\r\n".format(chunk_size).encode('utf-8')
            writer.write(chunk_header)
            writer.write(f.read(chunk_size))
            writer.write(b'\r\n')
            await writer.drain()
            gc.collect()
    writer.write(b"0\r\n")
    writer.write(b"\r\n")
    await writer.drain()
    writer.close()
    await writer.wait_closed()
    gc.collect()


async def server(reader, writer):
    req = await reader.readline()
    print(req)
    try:
        method, uri, proto = req.split(b" ")
        m = re.match(url_pat, uri)
        route_req = m.group(5)
    except Exception as e:
        print("Malformed request: {}".format(req))
        writer.close()
        await writer.wait_closed()
        return

    while True:
        h = await reader.readline()
        if h == b"" or h == b"\r\n":
            break
        print(h)

    print("route: {}".format(route_req.decode('utf-8')))
    test = route_req in routes
    print("Route found?: {}".format(test))

    if route_req in routes:
        await routes[route_req](writer)
    else:
        writer.write(b'HTTP/1.0 404 Not Found\r\n')
        writer.write(b'\r\n')
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    gc.collect()
