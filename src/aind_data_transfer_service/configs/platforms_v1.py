"""Platforms"""

from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated


class _PlatformModel(BaseModel):
    """Base model for platform"""

    model_config = ConfigDict(frozen=True)
    name: str
    abbreviation: str


class _Behavior(_PlatformModel):
    """Model behavior"""

    name: Literal["Behavior platform"] = "Behavior platform"
    abbreviation: Literal["behavior"] = "behavior"


class _Confocal(_PlatformModel):
    """Model confocal"""

    name: Literal["Confocal microscopy platform"] = (
        "Confocal microscopy platform"
    )
    abbreviation: Literal["confocal"] = "confocal"


class _Ecephys(_PlatformModel):
    """Model ecephys"""

    name: Literal["Electrophysiology platform"] = "Electrophysiology platform"
    abbreviation: Literal["ecephys"] = "ecephys"


class _Exaspim(_PlatformModel):
    """Model exaSPIM"""

    name: Literal["ExaSPIM platform"] = "ExaSPIM platform"
    abbreviation: Literal["exaSPIM"] = "exaSPIM"


class _Fip(_PlatformModel):
    """Model FIP"""

    name: Literal["Frame-projected independent-fiber photometry platform"] = (
        "Frame-projected independent-fiber photometry platform"
    )
    abbreviation: Literal["FIP"] = "FIP"


class _Hcr(_PlatformModel):
    """Model HCR"""

    name: Literal["Hybridization chain reaction platform"] = (
        "Hybridization chain reaction platform"
    )
    abbreviation: Literal["HCR"] = "HCR"


class _Hsfp(_PlatformModel):
    """Model HSFP"""

    name: Literal["Hyperspectral fiber photometry platform"] = (
        "Hyperspectral fiber photometry platform"
    )
    abbreviation: Literal["HSFP"] = "HSFP"


class _Isi(_PlatformModel):
    """Model ISI"""

    name: Literal["Intrinsic signal imaging platform"] = (
        "Intrinsic signal imaging platform"
    )
    abbreviation: Literal["ISI"] = "ISI"


class _Merfish(_PlatformModel):
    """Model MERFISH"""

    name: Literal["MERFISH platform"] = "MERFISH platform"
    abbreviation: Literal["MERFISH"] = "MERFISH"


class _Mri(_PlatformModel):
    """Model MRI"""

    name: Literal["Magnetic resonance imaging platform"] = (
        "Magnetic resonance imaging platform"
    )
    abbreviation: Literal["MRI"] = "MRI"


class _Mesospim(_PlatformModel):
    """Model mesoSPIM"""

    name: Literal["MesoSPIM platform"] = "MesoSPIM platform"
    abbreviation: Literal["mesoSPIM"] = "mesoSPIM"


class _Motor_Observatory(_PlatformModel):
    """Model motor-observatory"""

    name: Literal["Motor observatory platform"] = "Motor observatory platform"
    abbreviation: Literal["motor-observatory"] = "motor-observatory"


class _Multiplane_Ophys(_PlatformModel):
    """Model multiplane-ophys"""

    name: Literal["Multiplane optical physiology platform"] = (
        "Multiplane optical physiology platform"
    )
    abbreviation: Literal["multiplane-ophys"] = "multiplane-ophys"


class _Slap2(_PlatformModel):
    """Model SLAP2"""

    name: Literal["SLAP2 platform"] = "SLAP2 platform"
    abbreviation: Literal["SLAP2"] = "SLAP2"


class _Single_Plane_Ophys(_PlatformModel):
    """Model single-plane-ophys"""

    name: Literal["Single-plane optical physiology platform"] = (
        "Single-plane optical physiology platform"
    )
    abbreviation: Literal["single-plane-ophys"] = "single-plane-ophys"


class _Smartspim(_PlatformModel):
    """Model SmartSPIM"""

    name: Literal["SmartSPIM platform"] = "SmartSPIM platform"
    abbreviation: Literal["SmartSPIM"] = "SmartSPIM"


class Platform:
    """Platforms"""

    BEHAVIOR = _Behavior()
    CONFOCAL = _Confocal()
    ECEPHYS = _Ecephys()
    EXASPIM = _Exaspim()
    FIP = _Fip()
    HCR = _Hcr()
    HSFP = _Hsfp()
    ISI = _Isi()
    MERFISH = _Merfish()
    MRI = _Mri()
    MESOSPIM = _Mesospim()
    MOTOR_OBSERVATORY = _Motor_Observatory()
    MULTIPLANE_OPHYS = _Multiplane_Ophys()
    SLAP2 = _Slap2()
    SINGLE_PLANE_OPHYS = _Single_Plane_Ophys()
    SMARTSPIM = _Smartspim()

    ALL = tuple(_PlatformModel.__subclasses__())

    ONE_OF = Annotated[
        Union[tuple(_PlatformModel.__subclasses__())],
        Field(discriminator="name"),
    ]

    abbreviation_map = {m().abbreviation: m() for m in ALL}

    @classmethod
    def from_abbreviation(cls, abbreviation: str):
        """Get platform from abbreviation"""
        return cls.abbreviation_map.get(abbreviation, None)
