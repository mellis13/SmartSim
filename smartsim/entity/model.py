# BSD 2-Clause License
#
# Copyright (c) 2021-2024, Hewlett Packard Enterprise
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import annotations

import copy
import itertools
import re
import sys
import typing as t
import warnings
from os import getcwd
from os import path as osp

from .._core._install.builder import Device
from .._core.utils.helpers import cat_arg_and_value, expand_exe_path
from ..error import EntityExistsError, SSUnsupportedError
from ..log import get_logger
from .dbobject import FSModel, FSScript
from .entity import SmartSimEntity
from .files import EntityFiles

if t.TYPE_CHECKING:
    from smartsim.types import TODO

    RunSettings = TODO
    BatchSettings = TODO


logger = get_logger(__name__)


# TODO: Remove this supression when we strip fileds/functionality
#       (run-settings/batch_settings/params_as_args/etc)!
# pylint: disable-next=too-many-public-methods

class Application(SmartSimEntity):
    def __init__(
        self,
        name: str,
        exe: str,
        exe_args: t.Optional[t.Union[str,t.Sequence[str]]] = None,
        files: t.Optional[EntityFiles] = None,
        file_parameters: t.Mapping[str, str] | None = None,
    ) -> None:
        """Initialize an ``Application``

        :param name: name of the application
        :param exe: executable to run
        :param exe_args: executable arguments
        :param files: files to be copied, symlinked, and/or configured prior to 
                      execution
        :param file_parameters: parameters and values to be used when configuring
                                files
        """
        super().__init__(name, str(path))
        self._exe = [expand_exe_path(exe)]
        self._exe_args = _build_exe_args(exe_args) or []
        self._files = copy.deepcopy(files) if files else None
        self._file_parameters = params.copy() if params else {}
        self._incoming_entities: t.List[SmartSimEntity] = []
        self._key_prefixing_enabled = False

    #TODO Talk through as a group if _key_prefixing_enabled 
    #     should have proeprty and setter decorators or do we stick with something of similar syntax.
    #     Bring this up to the group after the rest of the class is done so they see what a consistent
    #     API is currently being formed.
    #TODO Discuss if the exe_args parameter should be set with a str in the construct 
    #     and setter or should we stick to t.Sequence[str] only.  This might require group discussion.
    #TODO Discuss with the core team when/if properties shoulda always be returned via reference 
    #     or deep copy 
    #TODO Ticket says to remove prefixing, but I think that needs to stay
    #TODO @property for _exe
    #TODO @exe.setter for _exe
    #TODO @property for _files
    #TODO @pfiles.setter for _files
    #TODO @property for _file_parameters
    #TODO @file_parameters.setter for _file_parameters
    #TODO @property for _incoming_entities
    #TODO @incoming_entities.setter for _incoming_entites
    #TODO Update __str__
    #TODO Should attached_files_table be deleted and replaced with @property?
    #TODO Put create pinning string into a new ticket for finding a home for it
    #TODO check consistency of variable names and constructor with Ensemble, where appropriate
    #TODO Unit tests!!! 
    #TODO Cleanup documentation

    @property
    def exe_args(self) -> t.List[str]:
        # TODO why does this say immutable if it is not a deep copy?
        """Return an immutable list of attached executable arguments.

        :returns: application executable arguments
        """
        return self._exe_args

    @exe_args.setter
    def exe_args(self, value: t.Union[str, t.List[str], None]) -> None:
        # TODO should we just make this a t.Sequence[str] if the 
        # constructor is just t.list[str]
        """Set the executable arguments.

        :param value: executable arguments
        """
        self._exe_args = self._build_exe_args(value)

    def add_exe_args(self, args: t.Union[str, t.List[str]]) -> None:
        """Add executable arguments to executable

        :param args: executable arguments
        """
        args = self._build_exe_args(args)
        self._exe_args.extend(args)

    def register_incoming_entity(self, incoming_entity: SmartSimEntity) -> None:
        """Register future communication between entities.

        Registers the named data sources that this entity
        has access to by storing the key_prefix associated
        with that entity

        :param incoming_entity: The entity that data will be received from
        :raises SmartSimError: if incoming entity has already been registered
        """
        if incoming_entity.name in [
            in_entity.name for in_entity in self.incoming_entities
        ]:
            raise EntityExistsError(
                f"'{incoming_entity.name}' has already "
                + "been registered as an incoming entity"
            )

        self.incoming_entities.append(incoming_entity)

    def enable_key_prefixing(self) -> None:
        """If called, the entity will prefix its keys with its own application name"""
        self._key_prefixing_enabled = True

    def disable_key_prefixing(self) -> None:
        """If called, the entity will not prefix its keys with its own
        application name
        """
        self._key_prefixing_enabled = False

    def query_key_prefixing(self) -> bool:
        """Inquire as to whether this entity will prefix its keys with its name

        :return: Return True if entity will prefix its keys with its name
        """
        return self._key_prefixing_enabled

    def attach_generator_files(
        self,
        to_copy: t.Optional[t.List[str]] = None,
        to_symlink: t.Optional[t.List[str]] = None,
        to_configure: t.Optional[t.List[str]] = None,
    ) -> None:
        """Attach files to an entity for generation

        Attach files needed for the entity that, upon generation,
        will be located in the path of the entity.  Invoking this method
        after files have already been attached will overwrite
        the previous list of entity files.

        During generation, files "to_copy" are copied into
        the path of the entity, and files "to_symlink" are
        symlinked into the path of the entity.

        Files "to_configure" are text based application input files where
        parameters for the application are set. Note that only applications
        support the "to_configure" field. These files must have
        fields tagged that correspond to the values the user
        would like to change. The tag is settable but defaults
        to a semicolon e.g. THERMO = ;10;

        :param to_copy: files to copy
        :param to_symlink: files to symlink
        :param to_configure: input files with tagged parameters
        """
        to_copy = to_copy or []
        to_symlink = to_symlink or []
        to_configure = to_configure or []

        # Check that no file collides with the parameter file written
        # by Generator. We check the basename, even though it is more
        # restrictive than what we need (but it avoids relative path issues)
        for strategy in [to_copy, to_symlink, to_configure]:
            if strategy is not None and any(
                osp.basename(filename) == "smartsim_params.txt" for filename in strategy
            ):
                raise ValueError(
                    "`smartsim_params.txt` is a file automatically "
                    + "generated by SmartSim and cannot be ovewritten."
                )

        self.files = EntityFiles(to_configure, to_copy, to_symlink)

    @property
    def attached_files_table(self) -> str:
        """Return a list of attached files as a plain text table

        :returns: String version of table
        """
        if not self.files:
            return "No file attached to this application."
        return str(self.files)

    def print_attached_files(self) -> None:
        """Print a table of the attached files on std out"""
        print(self.attached_files_table)

    @staticmethod
    def _create_pinning_string(
        pin_ids: t.Optional[t.Iterable[t.Union[int, t.Iterable[int]]]], cpus: int
    ) -> t.Optional[str]:
        """Create a comma-separated string of CPU ids. By default, ``None``
        returns 0,1,...,cpus-1; an empty iterable will disable pinning
        altogether, and an iterable constructs a comma separated string of
        integers (e.g. ``[0, 2, 5]`` -> ``"0,2,5"``)
        """

        def _stringify_id(_id: int) -> str:
            """Return the cPU id as a string if an int, otherwise raise a ValueError"""
            if isinstance(_id, int):
                if _id < 0:
                    raise ValueError("CPU id must be a nonnegative number")
                return str(_id)

            raise TypeError(f"Argument is of type '{type(_id)}' not 'int'")

        try:
            pin_ids = tuple(pin_ids) if pin_ids is not None else None
        except TypeError:
            raise TypeError(
                "Expected a cpu pinning specification of type iterable of ints or "
                f"iterables of ints. Instead got type `{type(pin_ids)}`"
            ) from None

        # Deal with MacOSX limitations first. The "None" (default) disables pinning
        # and is equivalent to []. The only invalid option is a non-empty pinning
        if sys.platform == "darwin":
            if pin_ids:
                warnings.warn(
                    "CPU pinning is not supported on MacOSX. Ignoring pinning "
                    "specification.",
                    RuntimeWarning,
                )
            return None

        # Flatten the iterable into a list and check to make sure that the resulting
        # elements are all ints
        if pin_ids is None:
            return ",".join(_stringify_id(i) for i in range(cpus))
        if not pin_ids:
            return None
        pin_ids = ((x,) if isinstance(x, int) else x for x in pin_ids)
        to_fmt = itertools.chain.from_iterable(pin_ids)
        return ",".join(sorted({_stringify_id(x) for x in to_fmt}))

    def __str__(self) -> str:  # pragma: no cover
        entity_str = "Name: " + self.name + "\n"
        entity_str += "Type: " + self.type + "\n"
        entity_str += str(self.run_settings) + "\n"
        if self._fs_models:
            entity_str += "FS Models: \n" + str(len(self._fs_models)) + "\n"
        if self._fs_scripts:
            entity_str += "FS Scripts: \n" + str(len(self._fs_scripts)) + "\n"
        return entity_str