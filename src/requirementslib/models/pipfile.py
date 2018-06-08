# -*- coding: utf-8 -*-
import attr


@attr.s
class Source(object):
    # : URL to PyPI instance
    url = attr.ib(default="")
    # : If False, skip SSL checks
    verify_ssl = attr.ib(
        default=True, validator=attr.validators.optional(attr.validators.instance_of(bool))
    )
    #: human name to refer to this source (can be referenced in packages or dev-packages)
    name = attr.ib(default="")
