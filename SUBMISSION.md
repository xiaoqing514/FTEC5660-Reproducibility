# Submission checklist

The course requires three items, and this repository supplies the material for all three. The report
and the recording are yours to finish, and the GitHub link needs your account.

## 1. Report, ready to submit

`report/FTEC5660_Reproducibility_Report.pdf` runs 6 pages, which stays inside the 10 page limit, and
the DOCX source is included so that you can edit the wording. The name and the student ID already
appear on page 1, and a later change requires either an edit in the DOCX or an edit in the
`report_build.py` header followed by a rebuild.

## 2. GitHub link, one push away

The repository is committed locally with nine commits, and it contains everything needed to rebuild
the report from the measured CSVs, because `report_build.py` and `slides_build.py` regenerate both
documents from `results/*/cells.csv`.

```bash
cd repro
# create an empty repository on GitHub first, then:
git remote add origin https://github.com/<your-account>/<repo-name>.git
git push -u origin main
```

You can confirm before pushing that the API key never entered the history:

```bash
git grep -n sk- $(git rev-list --all)   # no output expected
git ls-files | grep -F .env             # no output expected
```

## 3. Presentation, ready to record

`report/FTEC5660_Presentation.pptx` holds 7 slides, and `report/speaking_script.md` holds a timed
script of about 9 minutes 30 seconds, which leaves margin under the 15 minute cap. Record with Zoom,
share the slides full screen, and keep one short segment on the terminal with `logs/baseline_v3.log`
scrolling during a live call if you want the run to be visible on camera.

## What stays out of this repository

- `repro/.env`, which holds the DeepSeek key, and the file is git-ignored.
- The upstream TradingAgents source, which installs from GitHub at the pinned commit
  `9fa1196fffbcfd9de5146d2dd2869df84ab99838`, and the README records the exact install steps.
- `results/_cache/`, which holds the Yahoo price cache and re-downloads in seconds.

## Verification performed

The committed tree alone, exported with `git archive HEAD`, rebuilds the report to the same
paragraph, table and character counts as the checked-in DOCX, and it rebuilds a deck of 7 slides:

```
rebuilt from snapshot (paras,tables,chars): (70, 5, 13336)
current deliverable                      : (70, 5, 13336)
MATCH
```

That result is the reproducibility claim for this repository itself, because a clean clone plus a
DeepSeek key is enough to re-run the experiment and to regenerate every deliverable.
