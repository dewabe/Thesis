import variables as VAR

def wsGetIp(s):
    '''
    Returns an IP address from [websocket].peer
    '''
    try:
        return s.split(':')[1]
    except:
        return 'unknown'


def generate_message():
    data = {
        "init": VAR.OPC_SERVERS['init']
    }
    for server_name in VAR.OPC_SERVERS.keys():
        if server_name != "init":
            for namespace in VAR.OPC_SERVERS[server_name]["namespaces"].keys():
                for node in VAR.OPC_SERVERS[server_name]["namespaces"][namespace]["nodes"]:
                    this_node = VAR.OPC_SERVERS[server_name]["namespaces"][namespace]["nodes"][node]
                    id = this_node["hmi"]["id"]
                    data[id] = {
                        "timestamp": str(this_node["timestamp"]),
                        "value": str(this_node["value"]),
                        "hmi": {
                            "building": this_node["hmi"]["building"],
                            "level": this_node["hmi"]["level"],
                            "type": this_node["hmi"]["type"],
                            "position": {
                                "x": this_node["hmi"]["position"]["x"],
                                "y": this_node["hmi"]["position"]["y"]
                            }
                        }
                    }
    return data