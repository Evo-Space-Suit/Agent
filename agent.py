import logging

DISPLAY = logging.getLevelName('DISPLAY')


def detect_event(user_utterance):
    raise NotImplementedError()


class State:
    def __init__(self, name, hooks, events):
        self.name = name
        self.hooks = hooks
        self.events = events

    @property
    def outgoing(self):
        return {i for target_ids in self.events.values() for i in target_ids}

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<State {self.name} with {sum(len(hook) for hook in self.hooks.values())} hook(s)" \
               f" and with transition(s) to {self.outgoing}>"

    def show_events(self):
        return ', '.join(f'!{e}' for e, ss in self.events.items() if ss)


class Agent:
    def __init__(self, name, **kwargs):
        self.name = name
        self.allow_manual = kwargs.get('manual', False)
        self.allow_execution = kwargs.get('dev', False)
        self.states = []
        self.state = None
        self.ready = False

    def init(self):
        if self.state is None:
            raise ValueError("Please set a start state or import a configuration.")
        else:
            logging.debug("Agent ready to go.")
            logging.log(DISPLAY, '\n'.join(self.state.hooks['OnEnter']))
            if self.allow_manual:
                logging.debug(f"Possible events: {self.state.show_events()}")
        self.ready = True

    @classmethod
    def from_T(cls, T, start_state_name, **kwargs):
        # get all 'class' node id's
        State_id, Message_id, Hook_id, Event_id = map(T.get_node_id, 'State Message Hook Event'.split())

        # load states and identify start-state
        state_ids = list(T.connected(State_id))
        start_state_id = T.get_node_id(start_state_name, allowed=state_ids)

        # warn about unreachable states
        unreachable_state_ids = {sid for sid in state_ids if not list(T.connected(sid, direction='incoming'))}
        if unreachable_state_ids - {start_state_id}:
            logging.warning(f"State(s) {unreachable_state_ids} are unreachable.")

        # build states
        new_agent = cls(T['name'], **kwargs)
        new_agent.states = []

        hook_type_ids = list(T.connected(Hook_id))
        hook_type_names = list(T.get_info(hook_type_ids, 'data'))

        event_type_ids = list(T.connected(Event_id))
        event_type_names = list(T.get_info(event_type_ids, 'data'))

        for nid, name in T.get_info(state_ids, 'id', 'data'):
            hooks = {hook_name: list(T.get_info(T.connected(nid, hid), 'data'))
                     for hid, hook_name in zip(hook_type_ids, hook_type_names)}
            events = {event_name: list(map(state_ids.index, T.get_info(T.connected(nid, eid), 'id')))
                      for eid, event_name in zip(event_type_ids, event_type_names)}

            state = State(name, hooks, events)
            if nid == start_state_id:
                new_agent.state = state
            new_agent.states.append(state)

        logging.debug(f"Finished loading {T['name']} with {len(new_agent.states)} states.")
        return new_agent

    def update(self, e):
        if not self.ready:
            raise RuntimeError("Agent not ready, please run init.")

        if e not in self.state.events:
            logging.debug(f"State {self.state.name} is not sensitive for {e}.")
            return

        possible_indices = self.state.events[e]

        if len(possible_indices) > 1:
            logging.warning(f"Multiple target states not yet implemented (State {self.state.name}, Event {e}).")
        else:
            new_state = self.states[possible_indices[0]]
            logging.debug(f"Transitioning to state {new_state.name}")
            logging.log(DISPLAY, '\n'.join(self.state.hooks['OnExit']))
            self.state = new_state
            logging.log(DISPLAY, '\n'.join(self.state.hooks['OnEnter']))
            if self.allow_manual:
                logging.debug(f"Possible events: {self.state.show_events()}")

    def repl(self):
        if not self.ready:
            raise RuntimeError("Agent not ready, please run init.")

        for user_utterance in iter(input, ''):
            if self.allow_manual and user_utterance.startswith('!'):
                self.update(user_utterance[1:])
            elif self.allow_execution and user_utterance.startswith('>'):
                logging.info(str(eval(user_utterance[1:])))
            else:
                self.update(detect_event(user_utterance))


if __name__ == "__main__":
    print("Please run `run.py` to test the agent.")
