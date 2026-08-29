import inspect
import sys
import typing


def print_message(*args):
    if "--debug" in sys.argv or "--explain" in sys.argv or "--help" in sys.argv:
        print(*args)


def print_error(*args):
    print(*args, file=sys.stderr)


def execute_function(leaf_node: typing.Callable[..., typing.Any], *args) -> int:
    from clios.actions import CliOSError

    print_message("executing function:", leaf_node)
    print_message("with args:", args)
    try:
        leaf_node(*args)
    except CliOSError as e:
        # Already a message meant for the user. An empty one means the command
        # has printed its own listing.
        if str(e):
            print_error(str(e))
        return 1
    except Exception as e:
        print_error("Error:", e)
        if isinstance(e, TypeError):
            signature = str(inspect.signature(leaf_node))
            print_error(f"Usage: {leaf_node.__name__}{signature}")
        return 1
    return 0


def record_traversed_path(traversed_path: str, path: str) -> str:
    return traversed_path + " " + path


def clean_traversed_path(traversed_path: str) -> str:
    clean_traversed_path = list(
        filter(
            lambda item: item in get_all_keys_from_mapper(load_command_mapper()),
            traversed_path.split(" "),
        )
    )
    return " ".join(clean_traversed_path)


def leaf_summary(node: typing.Any) -> str:
    """First docstring line of a node's leaf, used as its one line help."""
    if not isinstance(node, dict):
        return ""
    leaf = node.get("leaf node")
    if callable(leaf) and leaf.__doc__:
        return leaf.__doc__.strip().split("\n")[0]
    return ""


def show_options(
    current_node: typing.Dict[str, typing.Any],
    traversed_path: str,
):
    options = sorted(key for key in current_node.keys() if key != "leaf node")
    if options:
        for key in options:
            label = f"{traversed_path} {key}".strip()
            summary = leaf_summary(current_node[key])
            print_error(f"  {label} - {summary}" if summary else f"  {label}")
        return
    function_to_explain = current_node.get("leaf node")
    if callable(function_to_explain):
        summary = leaf_summary(current_node)
        if summary:
            print_error(summary)
        signature = str(inspect.signature(function_to_explain))
        print_error(f"Usage: {function_to_explain.__name__}{signature}")


def handle_errors(
    error_message: str,
    traversed_path: str,
    path: str,
    current_node: typing.Dict[str, typing.Any],
):
    traversed_path = clean_traversed_path(traversed_path)
    if error_message == "No such path found":
        print_error(f"no such command '{path}'")
        print_error("try one of the following:")
        show_options(current_node, ("run " + traversed_path).strip())

    elif error_message == "Help flag found.":
        print_error(f"run {traversed_path}".replace("  ", " ").strip())
        has_sub_commands = any(key != "leaf node" for key in current_node)
        if has_sub_commands:
            print_error("try one of the following:")
        show_options(current_node, ("run " + traversed_path).strip())

    else:
        print_error(traversed_path.strip())
        print_error("No error message found for:", error_message)


def load_command_mapper() -> typing.Dict[str, typing.Any]:
    from clios.user_input_map import mapper

    return mapper


def get_all_keys_from_mapper(
    main_dict: typing.Dict[str, typing.Any]
) -> typing.List[str]:
    mapper_keys = []

    def get_all_keys(main_dict):
        if not isinstance(main_dict, dict):
            return

        for key in main_dict.keys():
            mapper_keys.append(key)
            if isinstance(main_dict[key], dict):
                get_all_keys(main_dict[key])

    get_all_keys(main_dict)
    return mapper_keys


def explain_function(
    current_node: typing.Dict[str, typing.Any],
):
    function_to_explain = current_node.get(
        "leaf node", lambda: print_message("No leaf node found")
    )
    print_message(function_to_explain.__name__)
    print_message("Signature:", str(inspect.signature(function_to_explain)))
    print_message(function_to_explain.__doc__)
    return


def traverse_command_mapper(
    user_command: typing.List[str],
    command_mapper: typing.Optional[typing.Dict[str, typing.Any]] = None,
) -> int:
    if command_mapper is None:
        command_mapper = load_command_mapper()

    if not user_command:
        print_error("run - commands:")
        show_options(command_mapper, "run")
        return 0

    traversed_path = ""

    # Traverse the user command.
    for path_index, path in enumerate(user_command):
        # The traversed path is used in error messages.
        traversed_path = record_traversed_path(traversed_path, path)

        # Traverse the command mapper dictionary with the user command.
        current_node: typing.Union[
            str,
            typing.Dict[str, typing.Any],
            typing.Dict[str, typing.Callable[..., typing.Any]],
        ] = command_mapper.get(path, "No such path found")

        # If the command is a string, it means that the path is not found.
        if isinstance(current_node, str):
            # Check for help flag in params.
            if "--help" in user_command[len(user_command) - 1]:
                current_node = "Help flag found."
                handle_errors(current_node, traversed_path, path, command_mapper)
                return 0

            # Check for explanation flag in params early to avoid extra checks in the loop.
            if "--explain" in user_command[len(user_command) - 1]:
                explain_function(command_mapper)
                return 0

            # Check if leaf node is the only key in the dictionary.
            command_mapper_has_a_leaf_node = "leaf node" in command_mapper.keys()

            # If the command mapper has a leaf node, execute the function.
            if command_mapper_has_a_leaf_node:
                function_to_execute = command_mapper.get(
                    "leaf node", lambda: print_message("No leaf node found")
                )
                return execute_function(function_to_execute, *user_command[path_index:])

            handle_errors(current_node, traversed_path, path, command_mapper)
            return 1

        is_last_path_in_user_command = path_index == len(user_command) - 1
        if is_last_path_in_user_command:
            function_to_execute = current_node.get(
                "leaf node", lambda: print_message("No leaf node found")
            )
            return execute_function(function_to_execute, *user_command[path_index + 1 :])

        # Update the command mapper to the current node.
        command_mapper = current_node  # type: ignore

    return 0


def main():
    from clios.actions import log_invocation

    # --dry-run is read from sys.argv by the actions, so it is stripped here
    # rather than travelling through the mapper as a command word.
    arguments = [arg for arg in sys.argv[1:] if arg != "--dry-run"]
    status = traverse_command_mapper(arguments)
    log_invocation(status)
    sys.exit(status)


if __name__ == "__main__":
    main()
