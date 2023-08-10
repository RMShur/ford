from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    Tuple,
)
import warnings
from markdown_include.include import (
    INC_SYNTAX as MD_INCLUDE_RE,
    MarkdownInclude,
    IncludePreprocessor,
)

from ford.utils import str_to_bool, meta_preprocessor
from ford._typing import PathLike

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


def default_cpus() -> int:
    try:
        import multiprocessing

        return multiprocessing.cpu_count()
    except (ImportError, NotImplementedError):
        return 0


def is_same_type(type_in: Type, tp: Type) -> bool:
    """Returns True if ``type_in`` is the same type as either ``tp``
    or ``Optional[tp]``"""
    return (
        (type_in is tp) or (get_origin(type_in) is tp) or is_optional_type(type_in, tp)
    )


def is_optional_type(tp: Type, sub_tp: Type) -> bool:
    """Returns True if ``tp`` is ``Optional[sub_tp]``"""
    if get_origin(tp) is not Union:
        return False

    return any(tp is sub_tp for tp in get_args(tp))


def convert_to_bool(name: str, option: List[str]) -> bool:
    """Convert value 'option' to a bool, with a nice error message on
    failure. Expects a list from the markdown meta-data extension"""
    if isinstance(option, bool):
        return option

    if len(option) > 1:
        raise ValueError(
            f"Could not convert option '{name}' to bool: expected a single value but got a list ({option})"
        )
    try:
        return str_to_bool(option[0])
    except ValueError:
        raise ValueError(
            f"Could not convert option '{name}' to bool: expected 'true'/'false', got: {option[0]}"
        )


@dataclass
class Settings:
    alias: List[str] = field(default_factory=list)
    author: Optional[str] = None
    author_description: Optional[str] = None
    author_pic: Optional[str] = None
    bitbucket: Optional[str] = None
    coloured_edges: bool = False
    copy_subdir: List[str] = field(default_factory=list)
    creation_date: str = "%Y-%m-%dT%H:%M:%S.%f%z"
    css: Optional[str] = None
    dbg: bool = True
    display: List[str] = field(default_factory=lambda: ["public", "protected"])
    doc_license: str = ""
    docmark: str = "!"
    docmark_alt: str = "*"
    email: Optional[str] = None
    encoding: str = "utf-8"
    exclude: List[str] = field(default_factory=list)
    exclude_dir: List[str] = field(default_factory=list)
    extensions: List[str] = field(
        default_factory=lambda: ["f90", "f95", "f03", "f08", "f15"]
    )
    external: list = field(default_factory=list)
    externalize: bool = False
    extra_filetypes: list = field(default_factory=list)
    extra_mods: list = field(default_factory=list)
    extra_vartypes: list = field(default_factory=list)
    facebook: Optional[str] = None
    favicon: str = "default-icon"
    fixed_extensions: list = field(default_factory=lambda: ["f", "for", "F", "FOR"])
    fixed_length_limit: bool = True
    force: bool = False
    fpp_extensions: list = field(
        default_factory=lambda: ["F90", "F95", "F03", "F08", "F15", "F", "FOR"]
    )
    github: Optional[str] = None
    gitlab: Optional[str] = None
    gitter_sidecar: Optional[str] = None
    google_plus: Optional[str] = None
    graph: bool = False
    graph_dir: Optional[str] = None
    graph_maxdepth: int = 10000
    graph_maxnodes: int = 1000000000
    hide_undoc: bool = False
    incl_src: bool = True
    include: list = field(default_factory=list)
    license: str = ""
    linkedin: Optional[str] = None
    lower: bool = False
    macro: list = field(default_factory=list)
    mathjax_config: Optional[str] = None
    max_frontpage_items: int = 10
    md_extensions: list = field(default_factory=list)
    media_dir: Optional[str] = None
    output_dir: str = "./doc"
    page_dir: Optional[str] = None
    parallel: int = default_cpus()
    predocmark: str = ">"
    predocmark_alt: str = "|"
    preprocess: bool = True
    preprocessor: str = "cpp -traditional-cpp -E -D__GFORTRAN__"
    print_creation_date: bool = False
    privacy_policy_url: Optional[str] = None
    proc_internals: bool = False
    project: str = "Fortran Program"
    project_bitbucket: Optional[str] = None
    project_download: Optional[str] = None
    project_github: Optional[str] = None
    project_gitlab: Optional[str] = None
    project_sourceforge: Optional[str] = None
    project_url: str = ""
    project_website: Optional[str] = None
    quiet: bool = False
    revision: Optional[str] = None
    search: bool = True
    show_proc_parent: bool = False
    sort: str = "src"
    source: bool = False
    src_dir: list = field(default_factory=lambda: ["./src"])
    summary: Optional[str] = None
    terms_of_service_url: Optional[str] = None
    twitter: Optional[str] = None
    version: Optional[str] = None
    warn: bool = False
    website: Optional[str] = None
    year: str = str(date.today().year)

    def __post_init__(self):
        field_types = get_type_hints(self)

        for key, value in asdict(self).items():
            default_type = field_types[key]

            if is_same_type(default_type, type(value)):
                continue

            if is_same_type(default_type, list):
                setattr(self, key, [value])


def load_toml_settings(directory: PathLike) -> Optional[Settings]:
    """Load Ford settings from ``fpm.toml`` file in ``directory``

    Settings should be in ``[extra.ford]`` table
    """

    filename = Path(directory) / "fpm.toml"

    if not filename.is_file():
        return None

    with open(filename, "rb") as f:
        settings = tomllib.load(f)

    if "extra" not in settings:
        return None

    if "ford" not in settings["extra"]:
        return None

    return asdict(Settings(**settings["extra"]["ford"]))


def load_markdown_settings(directory: PathLike, project_file: str) -> Tuple[Dict, str]:
    settings, project_file = meta_preprocessor(project_file)
    settings = asdict(Settings(**settings))
    field_types = get_type_hints(Settings)

    for key, value in settings.items():
        default_type = field_types[key]

        if is_same_type(default_type, type(value)):
            continue
        if is_same_type(default_type, list):
            settings[key] = [value]
        elif is_same_type(default_type, bool):
            settings[key] = convert_to_bool(key, value)
        elif is_same_type(default_type, int):
            settings[key] = int(value[0])
        elif is_same_type(default_type, str) and isinstance(value, list):
            settings[key] = "\n".join(value)

    # Workaround for file inclusion in metadata
    for option, value in settings.items():
        if isinstance(value, str) and MD_INCLUDE_RE.match(value):
            warnings.warn(
                "Including other files in project file metadata is deprecated and "
                "will stop working in a future release.\n"
                f"    {option}: {value}",
                FutureWarning,
            )
            md_base_dir = settings.get("md_base_dir", [str(directory)])[0]
            configs = MarkdownInclude({"base_path": md_base_dir}).getConfigs()
            include_preprocessor = IncludePreprocessor(None, configs)
            settings[option] = "\n".join(include_preprocessor.run(value.splitlines()))

    return settings, project_file
