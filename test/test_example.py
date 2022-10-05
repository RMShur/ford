import shutil
import sys
import os
import pathlib
import re

import ford

from bs4 import BeautifulSoup
import pytest


HEADINGS = re.compile(r"h[1-4]")
ANY_TEXT = re.compile(r"h[1-4]|p")


@pytest.fixture(scope="module")
def example_project(tmp_path_factory):
    this_dir = pathlib.Path(__file__).parent
    tmp_path = tmp_path_factory.getbasetemp() / "example"
    shutil.copytree(this_dir / "../example", tmp_path)

    with pytest.MonkeyPatch.context() as m:
        os.chdir(tmp_path)
        m.setattr(sys, "argv", ["ford", "example-project-file.md"])
        ford.run()

    with open(tmp_path / "example-project-file.md", "r") as f:
        project_file = f.read()
    settings, _, _ = ford.parse_arguments({}, project_file, tmp_path)

    doc_path = tmp_path / "doc"

    return doc_path, settings


def read_html(filename):
    with open(filename, "r") as f:
        return BeautifulSoup(f.read(), features="html.parser")


@pytest.fixture(scope="module")
def example_index(example_project):
    path, settings = example_project
    index = read_html(path / "index.html")
    return index, settings


def test_nav_bar(example_index):
    index, settings = example_index

    navbar_links = index.nav("a")
    link_names = {link.text.strip() for link in navbar_links}

    for expected_page in (
        settings["project"],
        "Source Files",
        "Modules",
        "Procedures",
        "Derived Types",
        "Program",
    ):
        assert expected_page in link_names


def test_jumbotron(example_index):
    """This test will probably break if a different theme or HTML/CSS
    framework is used"""

    index, settings = example_index
    jumbotron = index.find("div", "jumbotron")

    jumbotron_text = (p.text for p in jumbotron("p"))
    assert settings["summary"] in jumbotron_text

    links = [link["href"] for link in jumbotron("a")]

    for location_link in [
        "project_bitbucket",
        "project_download",
        "project_github",
        "project_gitlab",
        "project_sourceforge",
        "project_website",
    ]:
        if settings[location_link] is not None:
            assert settings[location_link] in links


def test_developer_info_box(example_index):
    index, settings = example_index

    # Assume that we have something like:
    #     `<div><h2>Developer Info</h2> .. box </div>`
    developer_info = index.find(string="Developer Info").parent.parent

    dev_text = [tag.text for tag in developer_info(ANY_TEXT)]

    for expected_text in ["author", "author_description"]:
        assert settings[expected_text] in dev_text


def test_latex(example_index):
    index, settings = example_index

    tex_tags = index("script", type=re.compile("math/tex.*"))

    assert len(tex_tags) == 4


def test_source_file_links(example_index):
    index, settings = example_index

    source_files_box = index.find(ANY_TEXT, string="Source Files").parent
    source_files_list = sorted([f.text for f in source_files_box("li")])

    assert source_files_list == sorted(
        ["ford_test_module.fpp", "ford_test_program.f90", "ford_example_type.f90"]
    )


def test_module_links(example_index):
    index, settings = example_index

    modules_box = index.find(ANY_TEXT, string="Modules").parent
    modules_list = sorted([f.text for f in modules_box("li")])

    assert modules_list == sorted(["test_module", "ford_example_type_mod"])


def test_procedures_links(example_index):
    index, settings = example_index

    proceduress_box = index.find(ANY_TEXT, string="Procedures").parent
    proceduress_list = sorted([f.text for f in proceduress_box("li")])

    all_procedures = sorted(
        ["decrement", "do_foo_stuff", "do_stuff", "increment", "check"]
    )
    max_frontpage_items = int(settings["max_frontpage_items"])
    front_page_list = all_procedures[:max_frontpage_items]

    assert proceduress_list == front_page_list


def test_types_links(example_index):
    index, settings = example_index

    types_box = index.find(ANY_TEXT, string="Derived Types").parent
    types_list = sorted([f.text for f in types_box("li")])

    assert types_list == sorted(["bar", "foo", "example_type"])


def test_types_type_bound_procedure(example_project):
    path, _ = example_project
    index = read_html(path / "type/example_type.html")

    bound_procedures_section = index.find("h2", string="Type-Bound Procedures").parent

    assert "This will document" in bound_procedures_section.text, "Binding docstring"
    assert (
        "has more documentation" in bound_procedures_section.text
    ), "Full procedure docstring"


def test_graph_submodule(example_project):
    path, _ = example_project
    index = read_html(path / "module/test_submodule.html")

    graph_nodes = index.svg.find_all("g", class_="node")

    assert len(graph_nodes) == 2
    titles = sorted([node.find("text").text for node in graph_nodes])
    assert titles == sorted(["test_module", "test_submodule"])


def test_procedure_return_value(example_project):
    path, _ = example_project
    index = read_html(path / "proc/multidimension_string.html")

    retvar = index.find(string=re.compile("Return Value")).parent
    assert (
        "character(kind=kind('a'), len=4), dimension(:, :), allocatable" in retvar.text
    )


def test_info_bar(example_project):
    path, _ = example_project
    index = read_html(path / "proc/decrement.html")

    info_bar = index.find(id="info-bar")
    assert "creativecommons" in info_bar.find(id="meta-license").a["href"]
    assert "of total for procedures" in info_bar.find(id="statements").a["title"]
    assert "4 statements" in info_bar.find(id="statements").a.text

    breadcrumb = info_bar.find(class_="breadcrumb")
    assert len(breadcrumb("li")) == 3
    breadcrumb_text = [crumb.text for crumb in breadcrumb("li")]
    assert breadcrumb_text == ["ford_test_module.fpp", "test_module", "decrement"]


def test_side_panel(example_project):
    path, _ = example_project
    index = read_html(path / "program/ford_test_program.html")

    side_panel = index.find(id="sidebar")
    assert "None" not in side_panel.text

    side_panels = index.find_all(class_="panel-primary")
    # Twice as many due to the "hidden" panel that appears at the
    # bottom on mobile
    assert len(side_panels) == 2 * 4

    variables_panel = side_panels[0]
    assert len(variables_panel("a")) == 2
    assert variables_panel.a.text == "Variables"
    variables_anchor_link = variables_panel("a")[1]
    assert variables_anchor_link.text == "global_pi"
    assert (
        variables_anchor_link["href"]
        == "../program/ford_test_program.html#variable-global_pi"
    )

    subroutines_panel = side_panels[3]
    assert len(subroutines_panel("a")) == 4
    assert subroutines_panel.a.text == "Subroutines"
    subroutines_anchor_link = subroutines_panel("a")[1]
    assert subroutines_anchor_link.text == "do_foo_stuff"
    assert (
        subroutines_anchor_link["href"]
        == "../program/ford_test_program.html#proc-do_foo_stuff"
    )

    type_index = read_html(path / "type/example_type.html")
    constructor_panel = type_index.find(id="cons-1")
    assert constructor_panel.a.text == "example_type"
    assert (
        constructor_panel.a["href"]
        == "../type/example_type.html#interface-example_type"
    )

    check_index = read_html(path / "interface/check.html")
    check_sidebar = check_index.find(id="sidebar")
    assert "None" in check_sidebar.text
    assert check_sidebar.find_all(class_="panel-primary") == []
