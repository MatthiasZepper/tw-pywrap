"""
This script is used to build a Tower instance from a YAML configuration file.
Requires a YAML file that defines the resources to be created in Tower and
the required options for each resource based on the Tower CLI.
"""
import argparse
import logging

from pathlib import Path
from twkit import tower, helper, overwrite
from twkit.tower import ResourceExistsError


logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--log_level",
        default="INFO",
        choices=("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"),
        help="The desired log level (default: INFO).",
        type=str.upper,
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Print the commands that would be executed without running them.",
    )
    parser.add_argument(
        "yaml",
        type=Path,
        nargs="+",  # allow multiple YAML paths
        help="One or more YAML files with Tower resources to create",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Recursively delete all resources defined in the YAML file(s)",
    )
    parser.add_argument(
        "--cli",
        dest="cli_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to the Tower CLI",
    )
    return parser.parse_args()


class BlockParser:
    """
    Manages blocks of commands defined in a configuration file and calls appropriate
    functions for each block for custom handling of command-line arguments to _tw_run().
    """

    def __init__(self, tw, list_for_add_method):
        """
        Initializes a BlockParser instance.

        Args:
        tw: A Tower class instance.
        list_for_add_method: A list of blocks that need to be
        handled by the 'add' method.
        """
        self.tw = tw
        self.list_for_add_method = list_for_add_method
        # Create an instance of Overwrite class
        self.overwrite_method = overwrite.Overwrite(self.tw)

    def handle_block(self, block, args, destroy=False):
        # Check if delete is set to True, and call delete handler
        if destroy:
            logging.debug(" The '--delete' flag has been specified.\n")
            self.overwrite_method.handle_overwrite(
                block, args["cmd_args"], overwrite=False, destroy=True
            )
            return

        # Handles a block of commands by calling the appropriate function.
        block_handler_map = {
            "teams": (helper.handle_teams),
            "participants": (helper.handle_participants),
            "compute-envs": (helper.handle_compute_envs),
            "pipelines": (helper.handle_pipelines),
            "launch": lambda tw, args: helper.handle_generic_block(
                tw, "launch", args, method_name=None
            ),
        }

        # Check if overwrite is set to True, and call overwrite handler
        overwrite_option = args.get("overwrite", False)
        if overwrite_option:
            logging.debug(f" Overwrite is set to 'True' for {block}\n")
            self.overwrite_method.handle_overwrite(
                block, args["cmd_args"], overwrite_option
            )
        else:
            self.overwrite_method.handle_overwrite(block, args["cmd_args"])

        if block in self.list_for_add_method:
            helper.handle_generic_block(self.tw, block, args["cmd_args"])
        elif block in block_handler_map:
            block_handler_map[block](self.tw, args["cmd_args"])
        else:
            logger.error(f"Unrecognized resource block in YAML: {block}")


def main():
    options = parse_args()
    logging.basicConfig(level=options.log_level)

    tw = tower.Tower(cli_args=options.cli_args, dryrun=options.dryrun)
    block_manager = BlockParser(
        tw,
        [
            "organizations",  # all use method.add
            "workspaces",
            "credentials",
            "secrets",
            "actions",
            "datasets",
        ],
    )

    # Parse the YAML file(s) by blocks
    # and get a dictionary of command line arguments
    cmd_args_dict = helper.parse_all_yaml(options.yaml, destroy=options.delete)

    for block, args_list in cmd_args_dict.items():
        for args in args_list:
            try:
                # Run the 'tw' methods for each block
                block_manager.handle_block(block, args, destroy=options.delete)
            except ResourceExistsError as e:
                logging.error(e)
                continue


if __name__ == "__main__":
    main()
