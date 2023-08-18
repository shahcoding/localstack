import dataclasses
import json
import os.path
from typing import TYPE_CHECKING, List

import pytest

if TYPE_CHECKING:
    from _pytest.config import Config, PytestPluginManager
    from _pytest.config.argparsing import Parser


@dataclasses.dataclass
class MarkerReportEntry:
    node_id: str
    file_path: str
    markers: list[str]


@dataclasses.dataclass
class MarkerReport:
    prefix_filter: str
    entries: list[MarkerReportEntry] = dataclasses.field(default_factory=list)
    aggregated_report: dict[str, int] = dataclasses.field(default_factory=dict)

    def create_aggregated_report(self):
        for entry in self.entries:
            for marker in entry.markers:
                self.aggregated_report.setdefault(marker, 0)
                self.aggregated_report[marker] += 1


@pytest.hookimpl
def pytest_addoption(parser: "Parser", pluginmanager: "PytestPluginManager"):
    """
    Standard usage. Will create a report for all markers under ./target/marker-report-<date>.json
    $ python -m pytest tests/aws/ --marker-report

    Advanced usage. Will create a report for all markers under ./target2/marker-report-<date>.json
    $ python -m pytest tests/aws/ --marker-report --marker-report-output target2/

    Advanced usage. Only includes markers with `aws_` prefix in the report.
    $ python -m pytest tests/aws/ --marker-report --marker-report-filter-prefix "aws_"
    """
    # TODO: --marker-report-* flags should imply --marker-report
    parser.addoption("--marker-report", action="store_true")
    parser.addoption("--marker-report-prefix", action="store")
    parser.addoption("--marker-report-output", action="store")


@pytest.hookimpl
def pytest_collection_modifyitems(
    session: pytest.Session, config: "Config", items: List[pytest.Item]
) -> None:
    """Generate a report about the pytest markers used"""

    if not config.option.marker_report:
        return

    report = MarkerReport(prefix_filter=config.option.marker_report_prefix or "")

    # target directory for generated report
    marker_report_output = config.option.marker_report_output or "target"
    if os.path.isabs(marker_report_output):
        report_path = os.path.join(marker_report_output, "report.json")
    else:
        # TODO: not sure about config.rootdir yet
        report_path = config.rootdir / marker_report_output / "report.json"

    # go through collected items to collect their markers
    for item in items:
        markers = set()
        for mark in item.iter_markers():
            if mark.name.startswith(report.prefix_filter):
                markers.add(mark.name)

        report_entry = MarkerReportEntry(
            node_id=item.nodeid, file_path=item.fspath.strpath, markers=list(markers)
        )
        report.entries.append(report_entry)

    report.create_aggregated_report()

    with open(report_path, "w") as fd:
        json.dump(dataclasses.asdict(report), fd, indent=2, sort_keys=True)

    print("\n=========================")
    print("MARKER REPORT (SUMMARY)")
    print("=========================")
    for k, v in report.aggregated_report.items():
        print(f"{k}: {v}")
    print("=========================\n")
