from collections import defaultdict

from H_utils import load_from_path


class State:
    def __init__(self, name, hooks, events):
        self.name = name
        self.hooks = hooks
        self.events = events

    @property
    def outgoing(self):
        return {i for target_ids in self.events.values() for i in target_ids}

    def __str__(self):
        return f"<State {self.name} with {sum(len(hook) for hook in self.hooks.values())} hook(s)" \
               f" and with transition(s) to {self.outgoing}>"


class Agent:
    def __init__(self, name):
        self.name = name
        self.states = []
        self.state = None

    @classmethod
    def from_T(cls, T, start_state_name):
        # get all 'class' node id's
        State_id, Message_id, Hook_id, Event_id = map(T.get_node_id, 'State Message Hook Event'.split())

        # load states and identify start-state
        state_ids = list(T.all_children(State_id))
        start_state_id = T.get_node_id(start_state_name, allowed=state_ids)

        # warn about unreachable states
        unreachable_state_ids = {sid for sid in state_ids if not any(
                sid in set(T.all_children(sid_)) for sid_ in state_ids if sid != sid_)}
        if unreachable_state_ids - {start_state_id}:
            print(f"State(s) {unreachable_state_ids} are unreachable.")

        # build states
        states = []
        hook_type_ids = list(T.all_children(Hook_id))
        hook_type_names = list(T.get_info(hook_type_ids, 'data'))

        event_type_ids = list(T.all_children(Event_id))
        event_type_names = list(T.get_info(event_type_ids, 'data'))

        for nid, name in T.get_info(state_ids, 'id', 'data'):
            hooks = {}
            for hid, hook_name in zip(hook_type_ids, hook_type_names):
                hooks[hook_name] = list(T.get_info(T.all_children(nid, hid), 'data'))

            events = {}
            for eid, event_name in zip(event_type_ids, event_type_names):
                events[event_name] = list(map(state_ids.index, T.get_info(T.all_children(nid, eid), 'id')))

            states.append(State(name, hooks, events))

        new_agent = cls(T['name'])
        new_agent.states = states
        new_agent.state = states[state_ids.index(start_state_id)]
        return new_agent


if __name__ == "__main__":
    T = load_from_path("diagram.json", mode='T')
    agent = Agent.from_T(T, start_state_name="Setup")
    print(*map(str, agent.states))
