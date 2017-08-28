#!/usr/bin/env python3

# Copyright (C) 2017 William Hicks
#
# This file is part of MakeBreak.
#
# MakeBreak is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import os
import sys
import json
import argparse


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

    def clean(self):
        """Remove config file and lldb files from debug directory"""
        self._data = {}
        os.remove(self.config_filename)
        for file_ in os.scandir(self.dbg_directory):
            if file_.name.endswith(".lldb"):
                os.remove(file_.path)

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
        self.set_last_used(filename)
        if filename not in self._data.keys():
            self._data[filename] = {"Breakpoints": {}}

    def get_last_used(self):
        """Return last executable debugged or configured"""
        return self._data.get("LASTUSED", None)

    def set_last_used(self, executable):
        """Return last executable debugged or configured"""
        executable = canon_path(executable)
        self._data["LASTUSED"] = executable

    def toggle_breakpoint(self, executable, source_file, line):
        source_file = os.path.split(source_file)[1]
        if executable is None:
            executable = self.get_last_used()
        else:
            executable = canon_path(executable)
            self.set_last_used(executable)
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

    def clean_breakpoints(self, executable):
        """Remove all breakpoints for given executable"""
        if executable is None:
            executable = self.get_last_used()
        for source_file, lines in self._data[
                executable]["Breakpoints"].items():
            for line_ in reversed(lines):
                self.toggle_breakpoint(executable, source_file, line_)

    def print_breakpoints(self, executable):
        if executable is None:
            executable = self.get_last_used()
        exec_str = "Executable: {}".format(os.path.basename(executable))
        # TODO: Verbose should print full pathname
        print(exec_str)
        print("-" * len(exec_str))
        try:
            for source_file, lines in self._data[
                    executable]["Breakpoints"].items():
                for line_ in lines:
                    print("{}:{}".format(source_file, line_))
        except KeyError:  # Executable touched but not added to config yet
            pass

    def debug(self, executable):
        """Launch debugging session

        .. warn:: Must run export_commands first
        """
        if executable is None:
            executable = self.get_last_used()
        command_filename = os.path.join(
            self.dbg_directory, "{}.lldb".format(raw_name(executable))
        )
        executable = canon_path(executable)
        self.set_last_used(executable)
        if executable in self._data:
            os.execvp("lldb", ["lldb", "-S", command_filename])
        else:
            os.execvp("lldb", ["lldb", executable])

    def export_commands(self):
        """Export commands to files suitable for loading with lldb -S"""
        for filename in self._data.keys():
            if not os.path.isfile(filename):
                continue
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

    parser.add_argument(
        '-x', '--executable', metavar='EXECUTABLE', default=None,
        help="executable to be debugged (last used if omitted)"
    )
    parser.set_defaults(command="start")

    # TODO: Other ways of specifying breakpoints
    break_parser = subparsers.add_parser(
        'break', aliases=["b"], help="toggle breakpoint"
    )
    break_parser.add_argument(
        '-x', '--executable', metavar='EXECUTABLE', default=None,
        help="executable to be debugged (last used if omitted)"
    )
    break_parser.add_argument(
        'source', metavar='SOURCE', help="source file for breakpoint"
    )
    break_parser.add_argument(
        'line', metavar='LINE', help="line number for breakpoint"
    )
    break_parser.set_defaults(command="break")

    clean_parser = subparsers.add_parser(
        'clean', help="remove existing breakpoints for current executable"
    )
    clean_parser.add_argument(
        '-a', '--all', default=False, action="store_true",
        help="completely delete config file (ERASES CURRENT CONFIG)"
    )
    clean_parser.add_argument(
        '-x', '--executable', metavar='EXECUTABLE', default=None,
        help="executable to be debugged (last used if omitted)"
    )
    clean_parser.set_defaults(command="clean")

    touch_parser = subparsers.add_parser(
        'touch', aliases=['t'], help="set last used executable"
    )
    touch_parser.add_argument(
        'executable', metavar='EXECUTABLE', default=None,
        help="executable to be debugged (last used if omitted)"
    )
    touch_parser.set_defaults(command="touch")

    print_parser = subparsers.add_parser(
        'print', aliases=['p'], help="print breakpoints"
    )
    print_parser.add_argument(
        '-x', '--executable', metavar='EXECUTABLE', default=None,
        help="executable to be debugged (last used if omitted)"
    )
    print_parser.set_defaults(command="print")

    build_parser = subparsers.add_parser(
        'build', help="rebuild lldb files from config"
    )
    build_parser.set_defaults(command="build")

    args = parser.parse_args(sys.argv[1:])

    config = DbgConfig()
    config.load()
    if args.executable is None and config.get_last_used() is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "start":
        config.debug(args.executable)
    elif args.command == "break":
        config.toggle_breakpoint(
            args.executable, args.source, args.line
        )
        config.save()
    elif args.command == "clean":
        if args.all:
            config.clean()
        else:
            config.clean_breakpoints(args.executable)
            config.save()
    elif args.command == "touch":
        config.set_last_used(args.executable)
        config.save()
    elif args.command == "print":
        config.print_breakpoints(args.executable)
    elif args.command == "build":
        config.export_commands()
    else:
        parser.print_help()
        sys.exit(1)
