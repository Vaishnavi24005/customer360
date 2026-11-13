# Customer 360 and Marketing Attribution

A reproducible analytics project joining website, app and CRM activity and comparing four ways to credit marketing touchpoints. The offline demo uses deterministic synthetic events and spend. The warehouse path reads the public GA4 sample and enriches it with simulated app, CRM and cost records.

## Run the demo

Open [demo/index.html](demo/index.html) in a browser after cloning or extracting the project. Choose an attribution model to update the campaign table and channel chart. The demo requires no internet connection, account or build tool.

Rebuild the data and run the validation checks using Python 3.12 or later:

```sh
python pipeline.py demo
```

- [Architecture and model grains](docs/architecture.md)
- [Metrics, findings and validation](docs/findings.md)
- [Tableau reporting guide](docs/tableau.md)
- [Ten-minute presentation](docs/Customer360.pptx) and [speaker guide](docs/presentation.md)
- [Individual reflection prompts](docs/reflection.md)

## Run the BigQuery and dbt pipeline

Use a Google Cloud project with BigQuery enabled in the US multi-region. The authenticated user needs permission to run jobs, create datasets and write tables. Use dedicated project datasets because the input generator replaces its four input tables. The GA4 scans have a 20 GB per-query ceiling.

Run from the repository root in PowerShell with Python and Google Cloud CLI available:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-warehouse.txt
gcloud auth application-default login
$env:C360_PROJECT = 'your-google-cloud-project'
Copy-Item config/profiles.example.yml config/profiles.yml
.\.venv\Scripts\python.exe pipeline.py prepare --project $env:C360_PROJECT
.\.venv\Scripts\dbt.exe build --profiles-dir config
Copy-Item demo warehouse-demo -Recurse
.\.venv\Scripts\python.exe pipeline.py export --project $env:C360_PROJECT --output warehouse-demo
```

Open `warehouse-demo/index.html`, or connect Tableau to the exported CSVs. Defaults are `customer360_inputs` and `customer360`. If you change them, set `C360_INPUTS` and `C360_DATASET` for dbt and pass matching `--inputs` and `--dataset` flags to Python. Keep cloud exports and credentials outside the repository.

The warehouse run requires a project with credentials. The checked-in demo and its reported numbers were validated locally. [Google's GA4 sample documentation](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset)

## Host the demo on GitHub Pages

The included Pages workflow deploys the `demo` directory on manual dispatch. For a repository eligible for Pages, enable **GitHub Actions** under **Settings → Pages → Build and deployment**, then run **Deploy demo** from **Actions**. Anyone with access to the deployed site can view the synthetic aggregate exports.
