import sys
import logging
from argparse import ArgumentParser

from HEdit.utils import HDict


parser = ArgumentParser()
parser.add_argument("--debug", action='store_const', const=True, help="Set debug logging level", default=True)
parser.add_argument("--override", action='store_const', const=True, help="Allow manual event triggers", default=True)
parser.add_argument("--dev", action='store_const', const=True, help="Allow eval inspection", default=True)
args = parser.parse_args()

DISPLAY = 25
logging.addLevelName(DISPLAY, 'DISPLAY')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG if args.debug else logging.INFO)
stdout_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
logger.addHandler(stdout_handler)

# TODO implement handler for Discord interaction or integrate with BEVO
# file_handler = logging.Handler()
# file_handler.setLevel(logging.DEBUG)
# file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
# logger.addHandler(file_handler)


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
    def __init__(self, name):
        self.name = name
        self.states = []
        self.state = None
        self.ready = False

    def init(self):
        if self.state is None:
            raise ValueError("Please set a start state or import a configuration.")
        else:
            logger.debug("Agent ready to go.")
            logger.log(DISPLAY, '\n'.join(self.state.hooks['OnEnter']))
            if args.override:
                logger.debug(f"Possible events: {self.state.show_events()}")
        self.ready = True

    @classmethod
    def from_T(cls, T, start_state_name):
        # get all 'class' node id's
        State_id, Message_id, Hook_id, Event_id = map(T.get_node_id, 'State Message Hook Event'.split())

        # load states and identify start-state
        state_ids = list(T.connected(State_id))
        start_state_id = T.get_node_id(start_state_name, allowed=state_ids)

        # warn about unreachable states
        unreachable_state_ids = {sid for sid in state_ids if not list(T.connected(sid, direction='incoming'))}
        if unreachable_state_ids - {start_state_id}:
            logger.warning(f"State(s) {unreachable_state_ids} are unreachable.")

        # build states
        new_agent = cls(T['name'])
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

        logger.debug(f"Finished loading {T['name']} with {len(new_agent.states)} states.")
        return new_agent

    def update(self, e):
        if not self.ready:
            raise RuntimeError("Agent not ready, please run init.")

        if e not in self.state.events:
            logger.debug(f"State {self.state.name} is not sensitive for {e}.")
            return

        possible_indices = self.state.events[e]

        if len(possible_indices) > 1:
            logger.warning(f"Multiple target states not yet implemented (State {self.state.name}, Event {e}).")
        else:
            new_state = self.states[possible_indices[0]]
            logger.debug(f"Transitioning to state {new_state.name}")
            logger.log(DISPLAY, '\n'.join(self.state.hooks['OnExit']))
            self.state = new_state
            logger.log(DISPLAY, '\n'.join(self.state.hooks['OnEnter']))
            if args.override:
                logger.debug(f"Possible events: {self.state.show_events()}")

    def repl(self):
        if not self.ready:
            raise RuntimeError("Agent not ready, please run init.")

        for user_utterance in iter(input, ''):
            if args.override and user_utterance.startswith('!'):
                self.update(user_utterance[1:])
            elif args.dev and user_utterance.startswith('>'):
                logger.debug(str(eval(user_utterance[1:])))
            else:
                self.update(detect_event(user_utterance))


if __name__ == "__main__":
    T = HDict.load_from_path("diagram.json", mode='T')
    agent = Agent.from_T(T, start_state_name="Setup")
    agent.init()
    agent.repl()
    # For now you can go through the states by triggering events.
    # An event like read message is triggered by !Read.
    # You can run Python expressions prefixed by >.
    # An example conversation:
    """
    DEBUG Finished loading AgentFSMColored with 4 states.
    DEBUG Agent ready to go.
    DISPLAY Hi, I'm ESSI, your spacesuit's personal assistant.
    DEBUG Possible events: !Read
    !Read
    DEBUG Transitioning to state GetName
    DISPLAY Let's set you up.
    DISPLAY What's your name?
    DEBUG Possible events: !Invalid, !Valid
    !Valid
    DEBUG Transitioning to state Main
    DISPLAY 
    DISPLAY Alright, ask me anything!
    DEBUG Possible events: !Invalid
    !Invalid
    DEBUG Transitioning to state Error
    DISPLAY 
    DISPLAY Sorry, I didn't get that, can you reformulate it?
    DEBUG Possible events: !Read
    !Read
    DEBUG Transitioning to state Main
    DISPLAY 
    DISPLAY Alright, ask me anything!
    DEBUG Possible events: !Invalid
    >quit()
    """
