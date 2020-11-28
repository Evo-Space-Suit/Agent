import logging
from argparse import ArgumentParser


def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.state = agent.state.name if args[7] == "update" else "/"
    return record


parser = ArgumentParser()
parser.add_argument("-diagram-path", help="Path of state diagram.", type=str, default="diagram.json")
parser.add_argument("-start-state", help="State to start the agent in.", type=str, default="Setup")
parser.add_argument("--debug", action='store_const', const=True, help="Set debug logging level", default=True)
parser.add_argument("--manual", action='store_const', const=True, help="Allow manual event triggers", default=True)
parser.add_argument("--dev", action='store_const', const=True, help="Allow eval inspection", default=True)
cli_args = parser.parse_args()

DISPLAY = 25
logging.addLevelName(DISPLAY, 'DISPLAY')
logging.basicConfig(format="State: %(state)-8s %(levelname)-8s %(message)s", level=logging.DEBUG if cli_args.debug else logging.INFO)
old_factory = logging.getLogRecordFactory()
logging.setLogRecordFactory(record_factory)


if __name__ == '__main__':
    from HEdit.utils import HDict
    from agent import Agent

    T = HDict.load_from_path(cli_args.diagram_path, mode='T')
    agent = Agent.from_T(T, start_state_name=cli_args.start_state,
                         manual=cli_args.manual or cli_args.dev, dev=cli_args.dev)
    agent.init()
    agent.repl()

    # For now you can go through the states by triggering events.
    # An event like read message is triggered by !Read.
    # You can run Python expressions prefixed by >.
    # An example conversation:
