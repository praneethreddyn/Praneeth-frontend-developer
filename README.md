# Praneeth Reddy Portfolio

## Run locally

The GitHub repository list can load directly in the browser. To enable the resume
download, run the included Python server from this folder:

```powershell
python app.py
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). The server uses only
the Python standard library and fetches the public repositories for
`praneethreddyn` from GitHub.

If you prefer VS Code Live Server (configured for port 5501), leave the Python
server running and open the portfolio through Live Server. Its API requests
will be sent to the Python server on port 8000.

The **Download resume** button creates a DOCX copy from
`Praneeth_Reddy_Nalamalapu_Resume.docx`, adds repositories not already listed in
its Projects section, and downloads the generated copy using the same filename.
The original resume template is not modified. If the Python API is unavailable,
the button downloads the saved template instead and tells you how to enable
repository updates. A working internet connection is required to fetch the
latest repositories.
