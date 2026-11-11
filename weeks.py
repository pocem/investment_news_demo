"""Work out which week is "last week" and which is "this week" for an issue.

The newsletter goes out on the weekend or on Monday:
  - last week  = the most recent Mon-Fri that has finished
  - this week  = the Mon-Fri the newsletter is previewing

Rule: "this week" is the Mon-Fri week containing (run date + 2 days), so
Saturday, Sunday and Monday runs all preview the same week. A Tue-Fri run
(e.g. for testing) treats the current week as "this week".
"""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Window:
    start: date  # Monday
    end: date  # Friday

    @property
    def iso_week(self) -> int:
        return self.start.isocalendar().week

    def as_dict(self) -> dict:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "iso_week": self.iso_week}


@dataclass(frozen=True)
class IssueWeeks:
    run_date: date
    last_week: Window
    this_week: Window

    @property
    def label(self) -> str:
        return f"{self.this_week.start.isocalendar().year}-W{self.this_week.iso_week:02d}"


def issue_weeks(run_date: date) -> IssueWeeks:
    anchor = run_date + timedelta(days=2)
    this_monday = anchor - timedelta(days=anchor.weekday())
    last_monday = this_monday - timedelta(days=7)
    return IssueWeeks(
        run_date=run_date,
        last_week=Window(last_monday, last_monday + timedelta(days=4)),
        this_week=Window(this_monday, this_monday + timedelta(days=4)),
    )
