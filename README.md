# LJPT_test

JLPT N2 practice quiz — a modular web app: one `index.html` (UI + logic) plus one
`data_*.js` file per exam (each self-registers through `JLPT_REGISTER()`).

## Structure

```
LJPT_test/
├── N2/
│   ├── index.html        # App shell: UI + logic (EXAM_FILES, JLPT_REGISTER)
│   ├── data_2023_07.js   # JLPT N2 — 2023年7月 (07/2023)
│   ├── data_2023_12.js   # JLPT N2 — 2023年12月 (12/2023)
│   ├── data_2022_12.js   # JLPT N2 — 2022年12月 (12/2022)
│   └── data_2022_07.js   # JLPT N2 — 2022年7月 (07/2022)
└── pdf_data/             # Source exam PDFs (not read by the app)
```

## Usage

Open `N2/index.html` in a browser and pick an exam from the **Đề thi** dropdown.

> Some browsers block `<script src="data_*.js">` when the page is opened directly
> from disk (`file://`). If an exam shows *"chưa có dữ liệu"*, either serve the
> folder over HTTP (e.g. `python -m http.server` inside `N2/`) or use the app's
> **Nạp dữ liệu** paste panel.

## Data format

Each exam is `{ metadata, data }`:

```js
JLPT_REGISTER({
  metadata: { id:"n2_YYYY_MM", label:"MM/YYYY", title:"…", file:"data_YYYY_MM.js" },
  data: [
    { tab:"文字・語彙", section:"問題1 漢字読み", instruction:"…",
      questions:[ { id:"…", passage:"", audioUrl:"", question:"…",
                    options:["…","…","…","…"], answer:0,
                    translation:"…", explanation:"…" } ] }
  ]
});
```

Tabs: `文字・語彙` / `用法` / `文法` / `読解` / `聴解`.

## Adding a new exam

1. Create `N2/data_YYYY_MM.js` in the format above.
2. Add one line to `EXAM_FILES` inside `N2/index.html`.

## Requirements

- Any modern browser — no build step, no dependencies.