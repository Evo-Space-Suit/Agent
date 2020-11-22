import json
from collections import UserDict


class HDict(UserDict):
    def get_info(self, node_ids, *fields):
        if isinstance(node_ids, int):
            node_ids = [node_ids]

        for node_id in node_ids:
            for node in self['data']:
                if node['id'] == node_id:
                    if not fields: yield node
                    elif len(fields) == 1: yield node[fields[0]]
                    else: yield tuple(map(node.get, fields))
                    break
            else:
                raise KeyError(f"No node in data with id {node_id}.")

    def find_nodes(self, data, fits=lambda provided, other: provided == other):
        for node in self['data']:
            if fits(data, node['data']):
                yield node

    def get_node_id(self, data, allowed=None, disallowed=()):
        results = [n['id'] for n in self.find_nodes(data) 
                   if (allowed is None or n['id'] in allowed) and n['id'] not in disallowed]
        if not results:
            raise KeyError(f"No node with data {data!r} found.")
        if len(results) > 1:
            raise ValueError(f"Ambigious id retrieval for {data!r}," 
                             "following nodes have this data:\n" + '\n'.join(map(str, results)))
        return results[0]

    def all_children(self, source_id, *via_ids):
        for edge in self['conn']:
            if edge['src'] != source_id:
                continue
            if all(any(conn == edge for conn in self.all_children(via_id))
                    for via_id in via_ids):
                yield edge['dst']


def load_from_path(path, mode='T'):
    modes = ['H', 'T', 'property_graph', 'edge_colored_graph', 'graph']

    with open(path) as f:
        dct = json.load(f)

    if not ('data' in dct and 'conn' in dct):
        raise ValueError("HEdit json at least contains 'data' and 'conn'.")

    if 'mode' in dct and not modes.index(mode) >= modes.index(dct['mode']):
        print(f"Required mode {mode!r} is stricter than found mode {dct['mode']!r}.")
    return HDict(dct)
