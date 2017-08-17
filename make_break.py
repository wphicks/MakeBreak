#!/usr/bin/env python3
import os
import sys
import json
import argparse
import subprocess


def raw_name(filename):
    """Return basename without extension"""
    return os.path.splitext(os.path.split(filename)[1])[0]


def canon_path(filename):
    """Return "canonical" path to file"""
    return os.path.abspath(os.path.normpath(filename))


class DbgConfig(object):
    """Stores breakpoint information for debugging with lldb"""
    def __init__(self, dbg_directory=".dbg"):
        self.dbg_directory = dbg_directory
        self.config_filename = os.path.join(dbg_directory, "config.json")
        if not os.path.isdir(self.dbg_directory):
            os.mkdir(self.dbg_directory)
        self._data = {}
        self.load()

    def load(self):
        """Load data from config file"""
        try:
            with open(self.config_filename) as config_file:
                self._data = json.load(config_file)
        except FileNotFoundError:
            pass

    def save(self):
        """Save data to config file"""
        self.export_commands()
        with open(self.config_filename, 'w') as config_file:
            json.dump(self._data, config_file)

    def add_executable(self, filename):
        """Add executable to debug configuration"""
        filename = canon_path(filename)
        if filename not in self._data.keys():
            self._data[filename] = {"Breakpoints": {}}

    def toggle_breakpoint(self, executable, source_file, line):
        source_file = os.path.split(source_file)[1]
        executable = canon_path(executable)
        self.add_executable(executable)
        try:
            breakpoints = self._data[executable]["Breakpoints"][source_file]
        except KeyError:
            self._data[executable]["Breakpoints"][source_file] = [line]
            return

        if line in breakpoints:
            breakpoints.remove(line)
        else:
            breakpoints.append(line)

    def print_breakpoints(self, executable):
        for source_file, lines in self._data[
                executable]["Breakpoints"].items():
            for line_ in lines:
                print("{}:{}".format(source_file, line_))

    def debug(self, executable):
        """Launch debugging session

        .. warn:: Must run export_commands first
        """
        command_filename = os.path.join(
            self.dbg_directory, "{}.lldb".format(raw_name(executable))
        )
        executable = canon_path(executable)
        if executable in self._data:
            subprocess.call(["lldb", "-S", command_filename])
        else:
            subprocess.call(["lldb", executable])

    def export_commands(self):
        """Export commands to files suitable for loading with lldb -S"""
        for filename in self._data.keys():
            commands = []
            commands.append("file {}".format(filename))
            for source_file, lines in self._data[
                    filename]["Breakpoints"].items():
                for line_ in lines:
                    commands.append(
                        "breakpoint set --file {} --line {}".format(
                            source_file, line_
                        )
                    )
            command_filename = os.path.join(
                self.dbg_directory, "{}.lldb".format(raw_name(filename))
            )
            with open(command_filename, 'w') as command_file:
                command_file.write("\n".join(commands))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Persistent debugging options for lldb'
    )
    subparsers = parser.add_subparsers(
        help="Debugging operations"
    )

    # TODO: Specify config file location
    # TODO: Verbose output

    start_parser = subparsers.add_parser('start', help="start debugger")
    start_parser.add_argument(
        'executable', metavar='EXECUTABLE', help="executable to be debugged"
    )
    start_parser.set_defaults(command="start")

    break_parser = subparsers.add_parser(
        'break', aliases=["b"], help="toggle breakpoint"
    )
    break_parser.add_argument(
        'executable', metavar='EXECUTABLE', help="executable to be debugged"
    )
    break_parser.add_argument(
        'source', metavar='SOURCE', help="source file for breakpoint"
    )
    break_parser.add_argument(
        'line', metavar='LINE', help="line number for breakpoint"
    )
    # TODO: Other ways of specifying breakpoints
    break_parser.set_defaults(command="break")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args(sys.argv[1:])

    config = DbgConfig()
    config.load()
    if args.command == "start":
        config.debug(args.executable)
    elif args.command == "break":
        config.toggle_breakpoint(args.executable, args.source, args.line)
        config.save()
    else:
        parser.print_help()
        sys.exit(1)
