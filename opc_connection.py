from opcua import ua, Client
import datetime
import json
import variables as VAR
import math


def sendMessageToAll(message=None, isBinary=False):
    '''
    Send message to all websocket clients that are connected to from_server
    '''
    try:
        for client in VAR.WEBSOCKET_CLIENTS:
            client.sendMessage(json.dumps(message), isBinary)
    except Exception as e:
        print('error', e)


class OpcProtocol():
    '''
    OPC Protocol settings
    '''
    def string_to_node_type(self, type='string'):
        if type == 'string':
            return ua.NodeIdType.String
        elif type == 'numeric':
            return ua.NodeIdType.Numeric
        else:
            return ua.NodeIdType.ByteString

    def __del__(self):
        self.Disconnect()

    def __init__(self, server_name):
        self.server_name = server_name

        namespaces = VAR.OPC_SERVERS[server_name]["namespaces"]

        # Get OPC UA node type
        for namespace in namespaces.keys():
            nodes = VAR.OPC_SERVERS[server_name]["namespaces"][namespace]["nodes"]
            for node in nodes:
                type = nodes[node]["opc_type"]
                nodes[node]["opc_type"] = self.string_to_node_type(type)

        self.Connect()

    def Connect(self):
        '''
        For creating connection to OPC UA Server
        '''
        server = VAR.OPC_SERVERS[self.server_name]["opc_server"]
        namespaces = VAR.OPC_SERVERS[self.server_name]["namespaces"]
        
        self.client = Client(server)
        try:
            self.client.connect()
            
            for namespace in namespaces.keys():
                VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["index"] = self.client.get_namespace_index(namespace)

        except Exception as e:
            print('Connect error:', e)
        finally:
            self.firstrun()


    def remove_subscribe(self):
        namespaces = VAR.OPC_SERVERS[self.server_name]["namespaces"]
        for namespace in namespaces.keys():
            nodes = VAR.OPC_SERVERS[self.server_name]['namespaces'][namespace]["nodes"]
            for node in nodes.keys():
                VAR.OPC_SERVERS[self.server_name]['namespaces'][namespace]["nodes"][node]["subscribe"].unsubscribe(
                    VAR.OPC_SERVERS[self.server_name]['namespaces'][namespace]["nodes"][node]["handler"]
                )
                VAR.OPC_SERVERS[self.server_name]['namespaces'][namespace]["nodes"][node]["subscribe"].delete()
        return True


    def Disconnect(self):
        '''
        Disconnect from OPC UA Server
        '''
        try:
            self.remove_subscribe()
            self.client.disconnect()
        except Exception as e:
            print('Disconnect error:', e)
        return "disconnect done"

    def create_node(self, node, namespace, type):
        return ua.NodeId(identifier=node, namespaceidx=namespace, nodeidtype=type)

    def firstrun(self):
        '''
        When OPC UA Server connection has been established, do this once
        '''
        try:
            if VAR.FIRST_RUN:
                namespaces = VAR.OPC_SERVERS[self.server_name]["namespaces"]

                for namespace in namespaces.keys():
                    index = VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["index"]
                    nodes = VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["nodes"]
                    for node in nodes.keys():
                        type = VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["nodes"][node]["opc_type"]
                        nodeid = self.create_node(node, index, type)
                        VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["nodes"][node]["opc_nodeid"] = nodeid

                        this_node = self.client.get_node(nodeid)
                        VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["nodes"][node]["opc_variable"] = this_node

                        value = this_node.get_value()

                        VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["nodes"][node]["value"] = value
                        VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["nodes"][node]["timestamp"] = str(datetime.datetime.utcnow())

                        VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["nodes"][node]["handler"] = NodeHandler(self.server_name, namespace)
                        VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["nodes"][node]["subscribe"] = self.client.create_subscription(
                            100,
                            VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["nodes"][node]["handler"]
                        )
                        VAR.OPC_SERVERS[self.server_name]["namespaces"][namespace]["nodes"][node]["subscribe"].subscribe_data_change(this_node)
        except Exception as e:
            print('firstRun error:', e)
        finally:
            VAR.FIRST_RUN = False

    def reset(self):
        self.remove_subscribe()
        VAR.FIRST_RUN = True
        self.firstrun()


class NodeHandler():
    '''
    OPC UA Node handler
    '''
    def __init__(self, server, namespace):
        self.server = server
        self.namespace = namespace

    def __trunc__(self):
        return math.trunc(1)

    def data_change(self, handle, node, item, attr):
        value = str(item)
        timestamp = str(datetime.datetime.utcnow())

        n = str(node)
        this_node = n[n.find(";s=")+3:n.find(")")]
        hmi_type = VAR.OPC_SERVERS[self.server]["namespaces"][self.namespace]["nodes"][this_node]['hmi']['type']
        current_value = VAR.OPC_SERVERS[self.server]["namespaces"][self.namespace]["nodes"][this_node]["value"]
        id = VAR.OPC_SERVERS[self.server]["namespaces"][self.namespace]["nodes"][this_node]['hmi']['id']
        
        VAR.OPC_SERVERS[self.server]["namespaces"][self.namespace]["nodes"][this_node]["value"] = value
        message = {
            id: {
                "value": value,
                "timestamp": timestamp,
                "type": hmi_type
            }
        }
        sendMessageToAll(message)
        '''
        if current_value != "1" and current_value != "True" and hmi_type == "firealarm":
            VAR.OPC_SERVERS[self.server]["namespaces"][self.namespace]["nodes"][this_node]["value"] = value
            VAR.OPC_SERVERS[self.server]["namespaces"][self.namespace]["nodes"][this_node]["timestamp"] = timestamp
            message = {
                id: {
                    "value": value,
                    "timestamp": timestamp,
                    "type": hmi_type
                }
            }
            sendMessageToAll(message)

        if hmi_type == "motion":
            VAR.OPC_SERVERS[self.server]["namespaces"][self.namespace]["nodes"][this_node]["value"] = value
            VAR.OPC_SERVERS[self.server]["namespaces"][self.namespace]["nodes"][this_node]["timestamp"] = timestamp
            message = {
                id: {
                    "value": value,
                    "timestamp": timestamp,
                    "type": hmi_type
                }
            }
            sendMessageToAll(message)
        '''


    def event(self, handle, event):
        pass