"""
This module contains the pydantic models used to validate the input
"""

from pathlib import Path
from typing import Any

from astropy import units as u
from astropy.time import Time
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
    validator,
)
from typing_extensions import Self

from snipergw.paths import base_output_dir


class EventConfig(BaseModel):
    event: str | None = None
    rev: int | None = None
    output_dir: Path = base_output_dir


DEFAULT_TELESCOPE = "ZTF"
DEFAULT_STARTTIME = Time.now() + 0.25 * u.hour

all_telescopes = [DEFAULT_TELESCOPE, "WINTER"]


class TelescopeDefault(BaseModel):
    filters: str
    exposuretime: float
    all_filters: list[str]


ztf_default = TelescopeDefault(
    filters="g,r,g", exposuretime=300.0, all_filters=["g", "r", "i"]
)
winter_default = TelescopeDefault(
    filters="J", exposuretime=450.0, all_filters=["y", "J", "Hs"]
)


class PlanConfig(BaseModel):
    output_dir: Path = base_output_dir
    telescope: str = DEFAULT_TELESCOPE
    filters: str | None = None
    exposuretime: float | None = None
    cache: bool = False
    starttime: Time = DEFAULT_STARTTIME
    subprogram: str = "EMGW"
    use_both_grids: bool = False

    @field_validator("telescope")
    @classmethod
    def telescope_must_be_known(cls, v):
        if v not in all_telescopes:
            raise ValueError(f"telescope must be in {all_telescopes}")
        return v

    @model_validator(mode="after")
    def set_default_filter(self) -> Any:
        if self.filters is None:
            if self.telescope == "ZTF":
                self.filters = ztf_default.filters
            elif self.telescope == "WINTER":
                self.filters = winter_default.filters
            else:
                raise ValueError(f"Unknown telescope {self.telescope}")

        for filter_name in self.filters.split(","):
            if self.telescope == "ZTF":
                assert filter_name in ztf_default.all_filters, (
                    f"Unknown filter {filter_name} for telescope {self.telescope}, "
                    f"acceptable filters are {ztf_default.all_filters}"
                )
            elif self.telescope == "WINTER":
                assert filter_name in winter_default.all_filters, (
                    f"Unknown filter {filter_name} for telescope {self.telescope}, "
                    f"acceptable filters are {winter_default.all_filters}"
                )
            else:
                raise ValueError(f"Unknown telescope {self.telescope}")

        return self

    @model_validator(mode="after")
    def set_default_exposure(self) -> Self:
        if self.exposuretime is None:
            if self.telescope == "ZTF":
                self.exposuretime = ztf_default.exposuretime
            elif self.telescope == "WINTER":
                self.exposuretime = winter_default.exposuretime
            else:
                raise ValueError(f"Unknown telescope {self.telescope}")

        return self

    model_config = ConfigDict(arbitrary_types_allowed=True)
