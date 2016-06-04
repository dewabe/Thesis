'''
Protocol converter from OPC UA to WebSocket

Written by dewabe in 2015

Application uses mainly autobahn framework and OPC UA module
All other modules that are required for those two, are mentioned
somewhere else.

Even though it looks like that you can add multiple OPC UA servers
or multiple namespaces, it is not tested and cannot be guaranteed
that those features would work properly.
However, if you would like to test those features,
ALL NODES HAVE TO HAVE UNIQUE ID
'''

from autobahn.asyncio.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory
import json
import trollius as asyncio
import variables as VAR
import opc_connection as opc
import toolbox
import threading


def init():
    try:
        VAR.OPC_SERVERS.clear()
    except:
        pass
    init_load_configuration_file()
    init_add_required_objects()

def init_load_configuration_file():
    with open('configuration.json') as config_file:
        config = json.load(config_file)
    VAR.OPC_SERVERS.update(config)

def init_add_required_objects():
    for server_name in VAR.OPC_SERVERS:
        if server_name != "init":
            VAR.OPC_SERVERS[server_name]["connection"] = opc.OpcProtocol(server_name)


class MyServerProtocol(WebSocketServerProtocol):
    '''
    WebSocket server settings
    '''
    def onConnect(self, request):
        print("Client connecting: {0}").format(toolbox.wsGetIp(request.peer))
        VAR.WEBSOCKET_CLIENTS.append(self)

    def onOpen(self):
        print("WebSocket connection open.\nOpen connections: {}").format(len(VAR.WEBSOCKET_CLIENTS))
        try:
            message = toolbox.generate_message()
        except Exception as e:
            message = {'init':'failed'}
        finally:
            self.sendMessage(json.dumps(message))

    def onMessage(self, message, isBinary):
        print message
        if message == "reset":
            VAR.FIRST_RUN = True
            for server in VAR.OPC_SERVERS.keys():
                if server != "init":
                    VAR.OPC_SERVERS[server]['connection'].remove_subscribe()
                    VAR.OPC_SERVERS[server]['connection'].firstrun()

    def onClose(self, wasClean, code, reason):
        for wss in VAR.WEBSOCKET_CLIENTS:
            if wss == self:
                VAR.WEBSOCKET_CLIENTS.remove(wss)
        print("WebSocket connection closed because: {}\nOpen connections: {}").format(reason, len(VAR.WEBSOCKET_CLIENTS))



def stop_loop():
    raw_input("Press ENTER to quit\n")
    loop.call_soon_threadsafe(loop.stop)

if __name__ == '__main__':
    init()

    factory = WebSocketServerFactory("ws://localhost:9000", debug=False)
    factory.protocol = MyServerProtocol

    loop = asyncio.get_event_loop()
    coro = loop.create_server(factory, '0.0.0.0', 9000)

    server = loop.run_until_complete(coro)

    try:
        threading.Thread(target=stop_loop).start()
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print e
    finally:
        for server in VAR.OPC_SERVERS.keys():
            if server != "init":
                VAR.OPC_SERVERS[server]["connection"].Disconnect()
                del VAR.OPC_SERVERS[server]["connection"]
        del VAR.OPC_SERVERS
        server.close()
        loop.close()